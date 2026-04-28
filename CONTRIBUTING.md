Contributing & Local Setup

This file contains minimal instructions to help contributors get started safely.

1. Create a Python virtual environment and install dependencies:

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Do NOT commit your device credentials. Instead, copy the example config and edit locally:

   ```powershell
   cp config\devices.example.yaml config\devices.yaml
   # Edit config\devices.yaml and replace placeholder values with your local device IPs.
   ```

3. For TP-Link Tapo devices, consider using environment variables instead of storing credentials in `devices.yaml`.
   Example in PowerShell:

   ```powershell
   $env:TAPO_USER = "you@example.com"
   $env:TAPO_PASS = "supersecret"
   ```

   And update `DeviceManager` to read from `env` when present.

4. Running the server (development):

   ```powershell
   python run.py
   ```

5. Opening the web UI:
   - Visit http://localhost:8000/ after the server starts.

If you'd like help wiring environment-based secrets or adding a `.env` loader, open an issue or PR with your suggestion.