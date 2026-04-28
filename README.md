# Lumi V2

Lumi is an autonomous, local-first home assistant powered by Language Models via Ollama, translating natural language into actionable intent for your smart home devices.

Lumi V2 introduces a completely new architecture targeting speed, reliability, and security:
- **FastAPI Backend**: Replaces the synchronous `HTTPServer` with asynchronous, lightning-fast endpoints.
- **Tapo Native Support**: Integrates TP-Link Tapo smart switches using the native `tapo` protocol.
- **Structured AI Outputs**: Enforces strict JSON schemas using Pydantic and Langchain, preventing brittle string-matching errors entirely.
- **Beautiful Frontend**: A completely reimagined neural-interface themed web UI.

## Getting Started

1. Set up a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/Scripts/activate # Windows
   pip install -r requirements.txt
   ```

2. Configure your devices:
   Edit `config/devices.yaml` to match your ESP relays and Tapo switches. Ensure you provide your TP-Link email and password for Tapo auth.

3. Run the hub:
   ```bash
   python run.py
   ```

## Stack
- Python 3.10+
- FastAPI & Uvicorn
- Langchain + Ollama (`gemma2:latest`)
- `plugp100` for Tapo
