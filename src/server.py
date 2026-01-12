from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import asyncio
import logging
import os
from datetime import datetime

# Import local modules
# Note: In production, better to use absolute imports or package structure
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from intent_router import HRIntentRouter
from action_executor import HRActionExecutor
from atomicwork_client import AtomicworkClient

# Setup robust logging (print to stdout with flush)
def log(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} | {level} | {message}", flush=True)

# logger = logging.getLogger(__name__) # Disabled due to buffering/config issues

# ... imports
from fastapi.staticfiles import StaticFiles

# ... app init
# ... imports
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Request

# ... app init
app = FastAPI(
    title="HR Service Request Agent",
    description="NLP-powered HR service request automation for Atomicwork",
    version="1.0.0"
)

# Debug logging for startup
log("Server module loaded, initializing app...")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    log(f"Validation Error: {exc}", "ERROR")
    log(f"Body: {body.decode()}", "ERROR")
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation Failed", "errors": str(exc), "body": body.decode()},
    )

@app.get("/")
async def health_check():
    log("Health check received")
    return {"status": "live", "version": "1.0.0"}

# Ensure output directory exists
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hr_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Mount static files for downloads
app.mount("/downloads", StaticFiles(directory=OUTPUT_DIR), name="downloads")

# Request Models
# Nested models for Atomicwork payload
class Requester(BaseModel):
    id: Optional[int] = None
    email: Optional[str] = None
    label: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class WebhookPayload(BaseModel):
    # New Standard Fields
    id: Optional[int] = None
    display_id: Optional[str] = None
    subject: Optional[str] = None
    requester: Optional[Requester] = None
    
    # Old Fields (Backward Compatibility/Aliases)
    ticket_id: Optional[str] = None
    issue_description: Optional[str] = None
    user_email: Optional[str] = None
    requester_name: Optional[str] = None
    
    model_config = {
        "extra": "ignore"
    }

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

# Routes
@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )

@app.get("/health", response_model=HealthResponse)
async def health():
    """Alternative health endpoint"""
    return await health_check()

@app.post("/webhook")
async def receive_webhook(payload: WebhookPayload, background_tasks: BackgroundTasks):
    """
    Main webhook endpoint - receives HR service requests from Atomicwork
    """
    logger.info(f"=" * 60)
    logger.info(f"WEBHOOK RECEIVED")
    logger.info(f"Full Payload: {payload.model_dump_json()}")
    
    # Normalize ID for logging
    tid = payload.display_id or payload.ticket_id or str(payload.id)
    
    log(f"Ticket ID: {tid}")
    log(f"=" * 60)
    
    # Process in background to return quickly to Atomicwork
    background_tasks.add_task(
        process_hr_request,
        payload
    )
    
    return {
        "status": "accepted",
        "message": f"Processing HR request for ticket {tid}",
        "ticket_id": tid
    }

async def process_hr_request(payload: WebhookPayload):
    """
    Background task to process the HR service request
    """
    # 1. Extract Data (Handle both formats)
    ticket_id = payload.display_id or payload.ticket_id or str(payload.id)
    description = payload.subject or payload.issue_description or ""
    
    user_email = "unknown@company.com"
    requester_name = "Employee"
    
    if payload.requester:
        user_email = payload.requester.email or user_email
        requester_name = payload.requester.label or f"{payload.requester.first_name} {payload.requester.last_name}"
    else:
        user_email = payload.user_email or user_email
        requester_name = payload.requester_name or user_email.split('@')[0]
    
    try:
        # Step 1: Route intent
        log(f"[{ticket_id}] Analyzing intent...")
        intent_result = intent_router.route(description)
        
        log(f"[{ticket_id}] Intent: {intent_result['intent']}")
        log(f"[{ticket_id}] Confidence: {intent_result['confidence']}")
        log(f"[{ticket_id}] Entities: {intent_result['entities']}")
        
        # Step 2: Execute action based on intent
        log(f"[{ticket_id}] Executing action...")
        action_result = await action_executor.execute(
            intent=intent_result['intent'],
            entities=intent_result['entities'],
            user_email=user_email,
            requester_name=requester_name,
            ticket_id=ticket_id
        )
        
        log(f"[{ticket_id}] Action Result: {action_result['status']}")
        
        # Step 3: Update Atomicwork ticket
        log(f"[{ticket_id}] Updating Atomicwork ticket...")
        
        # Build the update note
        note_content = build_ticket_note(intent_result, action_result)
        
        # Get attachment path if available
        attachment_path = action_result.get('attachment_path')
        
        # Update via Public Note (private=False)
        update_result = await atomicwork_client.add_note(
            ticket_id=ticket_id,
            content=note_content,
            private=False,  # Public note as requested
            attachment_path=attachment_path
        )
        
        if update_result['success']:
        log(f"[{ticket_id}] Ticket updated successfully with note!")
            
            # Step 4: Resolve the ticket
            log(f"[{ticket_id}] resolving ticket...")
            resolve_result = await atomicwork_client.resolve_request(ticket_id)
            if resolve_result['success']:
                log(f"[{ticket_id}] Ticket resolved!")
            else:
                 log(f"[{ticket_id}] Failed to resolve ticket", "ERROR")
        else:
            log(f"[{ticket_id}] Failed to update ticket: {update_result.get('error')}", "ERROR")
        
    except Exception as e:
        log(f"[{ticket_id}] Error processing request: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()

def build_ticket_note(intent_result: dict, action_result: dict) -> str:
    """Build a professional HTML note for Atomicwork ticket"""
    
    # Simple, professional message
    message = action_result.get('message', 'Request processed successfully.')
    
    # check for download url
    download_section = ""
    if action_result.get('download_url'):
        download_section = f"""
        <p>
            <a href="{action_result['download_url']}" target="_blank">Download Document</a>
        </p>
        """

    note_html = f"""
    <p>Hi {action_result.get('requester_name', 'there')},</p>
    <p>{message}</p>
    {download_section}
    <p>Regards,<br>HR Service Agent</p>
    """
    
    return note_html

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HR Service Request Agent")
    parser.add_argument("--port", type=int, default=8085, help="Port to run on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()
    
    print("=" * 60)
    print("   HR SERVICE REQUEST AGENT")
    print("=" * 60)
    print(f"Starting server on {args.host}:{args.port}")
    print(f"Webhook endpoint: http://localhost:{args.port}/webhook")
    print("=" * 60)
    
    uvicorn.run(app, host=args.host, port=args.port)
