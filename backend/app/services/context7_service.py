import httpx
import asyncio
from typing import Dict, Any, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class Context7APIService:
    """
    Service class for interacting with the Context7 API
    """

    def __init__(self):
        self.api_key = settings.CONTEXT7_API_KEY
        self.base_url = "https://api.context7.com"  # Default base URL
        if not self.api_key:
            logger.warning("CONTEXT7_API_KEY not found in settings. Context7 API will not function.")

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[Any, Any]:
        """
        Make HTTP request to Context7 API
        """
        if not self.api_key:
            return {"error": "CONTEXT7_API_KEY not configured"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
                return {"error": f"HTTP error: {e.response.status_code}"}
            except httpx.RequestError as e:
                logger.error(f"Request error occurred: {str(e)}")
                return {"error": f"Request error: {str(e)}"}
            except Exception as e:
                logger.error(f"Unexpected error occurred: {str(e)}")
                return {"error": f"Unexpected error: {str(e)}"}

    async def search_context(self, query: str, filters: Optional[Dict] = None) -> Dict[Any, Any]:
        """
        Search for contextual information using Context7 API
        """
        payload = {
            "query": query,
            "filters": filters or {}
        }

        return await self._make_request("POST", "/v1/search", json=payload)

    async def get_document(self, doc_id: str) -> Dict[Any, Any]:
        """
        Retrieve a specific document from Context7 API
        """
        return await self._make_request("GET", f"/v1/documents/{doc_id}")

    async def add_document(self, content: str, metadata: Optional[Dict] = None) -> Dict[Any, Any]:
        """
        Add a document to Context7 API
        """
        payload = {
            "content": content,
            "metadata": metadata or {}
        }

        return await self._make_request("POST", "/v1/documents", json=payload)

    async def health_check(self) -> bool:
        """
        Check if Context7 API is accessible
        """
        try:
            # Try to make a simple request to test connectivity
            result = await self._make_request("GET", "/v1/health")
            return "error" not in result
        except Exception:
            return False


# Global instance
context7_service = Context7APIService()