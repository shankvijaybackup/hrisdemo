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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="HR Service Request Agent",
    description="NLP-powered HR service request automation for Atomicwork",
    version="1.0.0"
)

# Initialize components
intent_router = HRIntentRouter()
action_executor = HRActionExecutor()
atomicwork_client = AtomicworkClient()

# Request Models
class WebhookPayload(BaseModel):
    ticket_id: str
    issue_description: str
    user_email: Optional[str] = None
    machine_hostname: Optional[str] = None
    # Additional fields that might come from Atomicwork
    requester_name: Optional[str] = None
    employee_id: Optional[str] = None

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
    logger.info(f"Ticket ID: {payload.ticket_id}")
    logger.info(f"Description: {payload.issue_description}")
    logger.info(f"User: {payload.user_email}")
    logger.info(f"=" * 60)
    
    # Process in background to return quickly to Atomicwork
    background_tasks.add_task(
        process_hr_request,
        payload
    )
    
    return {
        "status": "accepted",
        "message": f"Processing HR request for ticket {payload.ticket_id}",
        "ticket_id": payload.ticket_id
    }

async def process_hr_request(payload: WebhookPayload):
    """
    Background task to process the HR service request
    1. Understand intent via NLP
    2. Execute the appropriate action
    3. Update Atomicwork ticket with results
    """
    ticket_id = payload.ticket_id
    description = payload.issue_description
    user_email = payload.user_email or "unknown@company.com"
    requester_name = payload.requester_name or user_email.split('@')[0]
    
    try:
        # Step 1: Route intent
        logger.info(f"[{ticket_id}] Analyzing intent...")
        intent_result = intent_router.route(description)
        
        logger.info(f"[{ticket_id}] Intent: {intent_result['intent']}")
        logger.info(f"[{ticket_id}] Confidence: {intent_result['confidence']}")
        logger.info(f"[{ticket_id}] Entities: {intent_result['entities']}")
        
        # Step 2: Execute action based on intent
        logger.info(f"[{ticket_id}] Executing action...")
        action_result = await action_executor.execute(
            intent=intent_result['intent'],
            entities=intent_result['entities'],
            user_email=user_email,
            requester_name=requester_name,
            ticket_id=ticket_id
        )
        
        logger.info(f"[{ticket_id}] Action Result: {action_result['status']}")
        
        # Step 3: Update Atomicwork ticket
        logger.info(f"[{ticket_id}] Updating Atomicwork ticket...")
        
        # Build the update note
        note_content = build_ticket_note(intent_result, action_result)
        
        update_result = await atomicwork_client.add_private_note(
            ticket_id=ticket_id,
            content=note_content
        )
        
        if update_result['success']:
            logger.info(f"[{ticket_id}] Ticket updated successfully!")
        else:
            logger.error(f"[{ticket_id}] Failed to update ticket: {update_result.get('error')}")
        
    except Exception as e:
        logger.error(f"[{ticket_id}] Error processing request: {str(e)}")
        import traceback
        traceback.print_exc()

def build_ticket_note(intent_result: dict, action_result: dict) -> str:
    """Build HTML note for Atomicwork ticket"""
    
    intent = intent_result['intent']
    confidence = intent_result['confidence']
    entities = intent_result['entities']
    status = action_result['status']
    message = action_result.get('message', '')
    details = action_result.get('details', {})
    
    # Status color
    status_color = "#28a745" if status == "success" else "#dc3545" if status == "error" else "#ffc107"
    status_icon = "&#10003;" if status == "success" else "&#10007;" if status == "error" else "&#9888;"
    
    note_html = f"""
<div style="font-family: Arial, sans-serif; padding: 20px; background: #f8f9fa; border-radius: 8px;">
    <h3 style="color: #333; margin-top: 0; border-bottom: 2px solid #007bff; padding-bottom: 10px;">
        HR Service Agent - Automated Response
    </h3>
    
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 15px;">
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #dee2e6; width: 150px;"><strong>Intent Detected</strong></td>
            <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{intent.replace('_', ' ').title()}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Confidence</strong></td>
            <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{confidence:.0%}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Status</strong></td>
            <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">
                <span style="color: {status_color}; font-weight: bold;">{status_icon} {str(status).upper()}</span>
            </td>
        </tr>
    </table>
    
    <div style="background: white; padding: 15px; border-radius: 4px; margin-bottom: 15px;">
        <h4 style="margin-top: 0; color: #495057;">Action Taken</h4>
        <p style="margin-bottom: 0;">{message}</p>
    </div>
"""
    
    # Add entity details if present
    if entities:
        note_html += """
    <div style="background: white; padding: 15px; border-radius: 4px; margin-bottom: 15px;">
        <h4 style="margin-top: 0; color: #495057;">Extracted Information</h4>
        <ul style="margin-bottom: 0; padding-left: 20px;">
"""
        for key, value in entities.items():
            note_html += f"            <li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>\n"
        note_html += """        </ul>
    </div>
"""
    
    # Add action-specific details
    if details:
        note_html += """
    <div style="background: white; padding: 15px; border-radius: 4px; margin-bottom: 15px;">
        <h4 style="margin-top: 0; color: #495057;">Details</h4>
        <ul style="margin-bottom: 0; padding-left: 20px;">
"""
        for key, value in details.items():
            if key != 'pdf_content':  # Don't include raw PDF content
                note_html += f"            <li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>\n"
        note_html += """        </ul>
    </div>
"""
    
    # Add download link if there's an attachment
    if action_result.get('download_url'):
        note_html += f"""
    <div style="background: #e7f3ff; padding: 15px; border-radius: 4px; margin-bottom: 15px;">
        <h4 style="margin-top: 0; color: #0056b3;">Download</h4>
        <p style="margin-bottom: 0;">
            <a href="{action_result['download_url']}" style="color: #007bff; text-decoration: none;">
                Click here to download the generated document
            </a>
        </p>
    </div>
"""
    
    note_html += f"""
    <p style="color: #6c757d; font-size: 11px; margin-bottom: 0; text-align: right;">
        Processed by HR Service Agent | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </p>
</div>
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
