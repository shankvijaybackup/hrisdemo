import aiohttp
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AtomicworkClient:
    """Client for interacting with Atomicwork API"""
    
    def __init__(self):
        self.base_url = os.getenv("ATOMICWORK_BASE_URL", "https://drreddy.atomicwork.com").strip().rstrip('/')
        self.api_key = os.getenv("ATOMICWORK_API_KEY", "dummy_key").strip()
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Log config (masked)
        masked_key = self.api_key[:4] + "..." + self.api_key[-4:] if len(self.api_key) > 8 else "wont_show"
        logger.info(f"Atomicwork Client Config - URL: {self.base_url}, Key: {masked_key}")

    async def add_note(self, ticket_id: str, content: str, private: bool = False, attachment_path: str = None) -> Dict[str, Any]:
        """Add a note to a ticket using the activity-notes endpoint"""
        
        # In demo mode
        if self.api_key == "dummy_key" or "atomicwork" not in self.base_url:
            logger.info(f"[MOCK] Adding {'private' if private else 'public'} note to {ticket_id}")
            return {"success": True, "message": "Mock note added"}

        # Use the specific endpoint provided by user
        url = f"{self.base_url}/api/v1/requests/{ticket_id}/activity-notes"
        
        # Payload format matches user's cURL
        payload = {
            "is_private": str(private).lower(),  # "false" or "true"
            "description": content,
            "source": "PORTAL"
        }
        
        logger.info(f"Posting note to: {url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    if response.status in (200, 201):
                        return {"success": True}
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to add note: {response.status} - {error_text}")
                        return {"success": False, "error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"Network error adding note to {ticket_id}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def resolve_request(self, ticket_id: str) -> Dict[str, Any]:
        """Resolve the ticket using PATCH"""
        url = f"{self.base_url}/api/v1/requests/{ticket_id}"
        payload = {"status": "Resolved"}
        
        logger.info(f"Resolving ticket: {url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.patch(url, json=payload, headers=self.headers) as response:
                    if response.status in (200, 201):
                        logger.info(f"Ticket {ticket_id} resolved successfully")
                        return {"success": True}
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to resolve ticket: {response.status} - {error_text}")
                        return {"success": False, "error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"Network error resolving ticket {ticket_id}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _upload_file(self, file_path: str) -> str:
        """Upload a file and get its ID"""
        url = f"{self.base_url}/api/v1/attachments"
        try:
            async with aiohttp.ClientSession() as session:
                # Remove Content-Type header to let aiohttp set boundary for multipart
                upload_headers = {k:v for k,v in self.headers.items() if k != 'Content-Type'}
                
                with open(file_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=os.path.basename(file_path))
                    
                    async with session.post(url, data=data, headers=upload_headers) as response:
                        if response.status in (200, 201):
                            resp_json = await response.json()
                            # Assuming response structure { "id": "...", ... }
                            return resp_json.get("id")
                        else:
                            logger.error(f"File upload failed: {await response.text()}")
                            return None
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None


    # Backward compatibility alias
    async def add_private_note(self, ticket_id: str, content: str) -> Dict[str, Any]:
        return await self.add_note(ticket_id, content, private=True)
