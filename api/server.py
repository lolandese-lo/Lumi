import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
import os

from core.device_manager import DeviceManager
from core.ai_agent import AIAgent
from core.background_loop import BackgroundLoop

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Lumi V2", description="Autonomous Home AI Hub")
device_manager = DeviceManager(config_path="config/devices.yaml")
ai_agent = AIAgent(model_name="gemma2:latest")
background_agent = BackgroundLoop(device_manager, ai_agent, interval_minutes=5)

class CommandRequest(BaseModel):
    command: str

@app.on_event("startup")
async def startup_event():
    # Attempt an initial poll
    logger.info("Polling devices on startup...")
    await device_manager.poll_all_devices()
    logger.info("Starting background autonomous loop...")
    background_agent.start()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Stopping background autonomous loop...")
    background_agent.stop()

@app.post("/api/command")
async def process_user_command(req: CommandRequest):
    """The main endpoint the frontend hits with a conversational command."""
    # 1. Provide context
    context = device_manager.format_for_prompt()
    
    # 2. Ask LLM
    result = ai_agent.process_command(req.command, context)
    if not result:
        return JSONResponse(status_code=500, content={"error": "LLM failed to generate a valid response."})
        
    responses = []
    # 3. Execute actions locally
    for action in result.get("actions", []):
        d_id = action.get("device_id")
        cmd = action.get("command")
        logger.info(f"LLM instructed: {d_id} -> {cmd}")
        # Send actual commands
        res = await device_manager.send_command(d_id, cmd)
        responses.append({
            "device_id": d_id,
            "command": cmd,
            "result": res
        })

    return {
        "reply": result.get("conversation_reply", ""),
        "actions_taken": responses
    }

@app.get("/api/devices")
async def get_devices():
    """Return current state of all devices."""
    return device_manager.DEVICES

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the root index.html."""
    html_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    try:
        with open(html_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Frontend missing</h1><p>Please ensure frontend/index.html is created.</p>"
