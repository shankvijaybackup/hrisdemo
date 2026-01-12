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
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def add_private_note(self, ticket_id: str, content: str) -> Dict[str, Any]:
        """Add a private note to a ticket"""
        # In demo mode or if no real API key, just log it
        if self.api_key == "dummy_key" or not self.base_url:
            logger.info(f"[MOCK] Adding note to {ticket_id}")
            return {"success": True, "message": "Mock note added"}
            
        url = f"{self.base_url}/api/v1/tickets/{ticket_id}/notes"
        payload = {
            "content": content,
            "private": True
        }
        
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
