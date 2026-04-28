import uvicorn
import logging

if __name__ == "__main__":
    logging.info("Starting Lumi V2 Server...")
    # Make sure to run the server pointing to the fastapi app
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)
