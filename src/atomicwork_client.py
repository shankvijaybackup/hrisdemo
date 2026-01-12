import aiohttp
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AtomicworkClient:
    """Client for interacting with Atomicwork API"""
    
    def __init__(self):
        self.base_url = os.getenv("ATOMICWORK_BASE_URL", "https://drreddy.atomicwork.com")
        self.api_key = os.getenv("ATOMICWORK_API_KEY", "dummy_key")
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    async def add_note(self, ticket_id: str, content: str, private: bool = True, attachment_path: str = None) -> Dict[str, Any]:
        """Add a note to a ticket, optionally with an attachment"""
        
        # In demo mode
        if self.api_key == "dummy_key" or not self.base_url:
            logger.info(f"[MOCK] Adding {'private' if private else 'public'} note to {ticket_id}")
            return {"success": True, "message": "Mock note added"}

        # 1. Upload attachment if present
        attachment_id = None
        if attachment_path and os.path.exists(attachment_path):
            attachment_id = await self._upload_file(attachment_path)

        # 2. Add Note
        url = f"{self.base_url}/api/v1/tickets/{ticket_id}/notes"
        payload = {
            "content": content,
            "private": private
        }
        
        if attachment_id:
            payload["attachment_ids"] = [attachment_id]
        
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
