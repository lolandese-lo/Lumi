import asyncio
import logging
from datetime import datetime
from astral import LocationInfo
from astral.sun import sun

logger = logging.getLogger(__name__)

class BackgroundLoop:
    def __init__(self, device_manager, ai_agent, interval_minutes=5):
        self.device_manager = device_manager
        self.ai_agent = ai_agent
        self.interval_minutes = interval_minutes
        self._task = None
        
        # Offline sun tracking (Defaults to New York, user can modify config later)
        self.city = LocationInfo("New York", "USA", "America/New_York", 40.7128, -74.0060)

    def generate_environment_context(self) -> str:
        """Generate string containing time and sun position facts"""
        now = datetime.now()
        out = f"Current Local Time: {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d')}\n"
        
        try:
            s = sun(self.city.observer, date=now.date(), tzinfo=self.city.timezone)
            # Define basic daylight logic
            is_day = s["sunrise"] < now.astimezone(self.city.timezone) < s["sunset"]
            
            out += f"Sun Status: It is currently {'Daytime' if is_day else 'Nighttime'}.\n"
            out += f"Sunrise was at {s['sunrise'].strftime('%I:%M %p')}, Sunset is at {s['sunset'].strftime('%I:%M %p')}."
        except Exception as e:
            out += "Sun Tracking Unavailable."
            
        return out

    async def _loop(self):
        """The core endless background task"""
        logger.info(f"Jarvis background loop started. Evaluating every {self.interval_minutes} minutes.")
        while True:
            await asyncio.sleep(self.interval_minutes * 60)
            
            try:
                # 1. Update true device states
                await self.device_manager.poll_all_devices()
                
                # 2. Extract texts
                env_context = self.generate_environment_context()
                devices_context = self.device_manager.format_for_prompt()
                
                # 3. Ask AI if we should do anything proactively
                result = self.ai_agent.evaluate_autonomous_actions(env_context, devices_context)
                
                if result:
                    logger.info(f"Autonomous evaluation complete: {result.get('conversation_reply')}")
                    
                    # 4. Execute proactive actions
                    for action in result.get("actions", []):
                        d_id = action.get("device_id")
                        cmd = action.get("command")
                        logger.info(f"JARVIS OVERRIDE: Executing {d_id} -> {cmd}")
                        await self.device_manager.send_command(d_id, cmd)
            
            except Exception as e:
                logger.error(f"Error in background loop: {e}")

    def start(self):
        if not self._task:
            self._task = asyncio.create_task(self._loop())

    def stop(self):
        if self._task:
            self._task.cancel()
            self._task = None
