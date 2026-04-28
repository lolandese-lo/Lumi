import logging
import json
import asyncio
import requests
import yaml
from datetime import datetime
from plugp100.api.tapo_client import TapoClient
from plugp100.common.credentials import AuthCredential

# Set up logging
logger = logging.getLogger(__name__)

class DeviceManager:
    def __init__(self, config_path: str = 'config/devices.yaml'):
        self.config_path = config_path
        self.DEVICES = {}
        self.GROUPS = {}
        self.tapo_clients = {}  # Cache internal TapoClient objects
        self.load_config()

    def load_config(self):
        """Load device configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.DEVICES = config.get('devices', {})
                self.GROUPS = config.get('groups', {})
                logger.info(f"Loaded {len(self.DEVICES)} devices and {len(self.GROUPS)} groups.")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.DEVICES = {}
            self.GROUPS = {}

    async def get_tapo_client(self, device_id: str):
        """Initialize or retrieve a Tapo connection."""
        device = self.DEVICES.get(device_id)
        if not device or device['type'] != 'tapo_switch':
            return None

        if device_id in self.tapo_clients:
            return self.tapo_clients[device_id]

        user = device.get('tapo_user')
        password = device.get('tapo_pass')
        ip = device.get('ip')

        if not user or not password or not ip:
            logger.error(f"Missing Tapo credentials for {device_id}")
            return None

        # Create credential
        cred = AuthCredential(user, password)
        try:
            client = TapoClient(cred, ip)
            await client.login()
            self.tapo_clients[device_id] = client
            return client
        except Exception as e:
            logger.error(f"Failed to login to Tapo switch {device_id}: {e}")
            return None

    def get_group_devices(self, group_name: str):
        """Get all device objects in a group"""
        if group_name not in self.GROUPS:
            return []
        
        group = self.GROUPS[group_name]
        g_type = group.get('type', 'static')

        if g_type == 'static':
            return group.get('devices', [])
        elif g_type == 'dynamic':
            return list(self.DEVICES.keys())
        elif g_type == 'filtered':
            filters = group.get('filter', {})
            matched = []
            for dev_id, dev_data in self.DEVICES.items():
                if all(dev_data.get(k) == v for k, v in filters.items()):
                    matched.append(dev_id)
            return matched
            
        return []

    async def _send_esp_command(self, device_id: str, device: dict, command: str) -> dict:
        """Send command to ESP32 / Arduino devices over HTTP"""
        url = f"http://{device['ip']}/{command}"
        try:
            # We use a synchronous request here, could use aiohttp but requests 
            # is fine for tiny local payloads inside a thread executor.
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.get(url, timeout=3))
            
            if response.status_code == 200:
                data = response.json()
                device['state'] = data.get('relay', None)
                if 'temperature' in data and data['temperature']:
                    device['temperature'] = data['temperature']
                return {"status": "success", "state": data, "device_id": device_id}
            else:
                logger.error(f"HTTP {response.status_code} from {device_id}")
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Error contacting ESP {device_id}: {e}")
            return {"status": "error", "message": str(e)}

    async def _send_tapo_command(self, device_id: str, device: dict, command: str) -> dict:
        """Send command to Tapo devices via plugp100"""
        client = await self.get_tapo_client(device_id)
        if not client:
            return {"status": "error", "message": "Could not connect to Tapo"}

        try:
            if command == "on":
                await client.on()
                device['state'] = True
            elif command == "off":
                await client.off()
                device['state'] = False
            elif command == "toggle":
                # Need to read state and reverse
                info = await client.get_device_info()
                is_on = info.get("device_on", False)
                if is_on:
                    await client.off()
                    device['state'] = False
                else:
                    await client.on()
                    device['state'] = True
            elif command == "status":
                pass # Just updating state
                
            info = await client.get_device_info()
            device['state'] = info.get("device_on", False)
            
            return {"status": "success", "state": {"relay": device['state']}, "device_id": device_id}
        except Exception as e:
            logger.error(f"Error controlling Tapo {device_id}: {e}")
            return {"status": "error", "message": str(e)}

    async def send_command(self, device_id: str, command: str) -> dict:
        """Universal method to send a command to any device"""
        if device_id not in self.DEVICES:
            logger.warning(f"Unknown device: {device_id}")
            return {"status": "error", "message": "Unknown device"}

        device = self.DEVICES[device_id]
        if command not in device.get('commands', []) and command != "status":
            return {"status": "error", "message": f"Command {command} not supported"}

        dev_type = device.get('type')
        logger.info(f"Targeting {device_id} ({dev_type}) with command: {command}")

        if dev_type == 'esp_relay':
            return await self._send_esp_command(device_id, device, command)
        elif dev_type == 'tapo_switch':
            return await self._send_tapo_command(device_id, device, command)
        else:
            return {"status": "error", "message": f"Unknown device type {dev_type}"}

    async def poll_all_devices(self):
        """Poll all devices for their current states"""
        tasks = []
        for device_id, device in self.DEVICES.items():
            tasks.append(self.send_command(device_id, "status"))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    def format_for_prompt(self) -> str:
        """Export device states to be injected into the LLM prompt"""
        out = []
        for d_id, d in self.DEVICES.items():
            state_str = "ON" if d.get('state') is True else "OFF" if d.get('state') is False else "UNKNOWN"
            temp_str = f", Temp: {d['temperature']}F" if d.get('temperature') else ""
            out.append(f"- {d_id} ({d['type']}) : {state_str} {temp_str} | Description: {d['Description']}")
        return "\n".join(out)
