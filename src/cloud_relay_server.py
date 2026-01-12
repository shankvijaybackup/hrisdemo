import argparse
import uvicorn
from fastapi import FastAPI, Request
import httpx
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CloudRelay")

app = FastAPI()

TARGET_URL = "http://localhost:8085/webhook"

@app.post("/webhook")
async def forward_webhook(request: Request):
    """Forward incoming webhooks to the local agent"""
    try:
        payload = await request.json()
        logger.info(f"Relaying webhook to {TARGET_URL}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(TARGET_URL, json=payload, timeout=10.0)
            
        return {
            "status": "relayed", 
            "upstream_status": response.status_code,
            "upstream_response": response.json()
        }
    except Exception as e:
        logger.error(f"Relay failed: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=10000)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)
