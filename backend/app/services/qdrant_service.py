import logging
from typing import Dict, List, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
import uuid

logger = logging.getLogger(__name__)

class QdrantService:
    """
    Service class for interacting with Qdrant Vector Database
    """

    def __init__(self):
        self.api_key = settings.QDRANT_API_KEY
        self.url = settings.QDRANT_URL

        if self.url and self.api_key:
            self.client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
                timeout=10
            )
        elif self.url:
            # For local instance without API key
            self.client = QdrantClient(url=self.url, timeout=10)
        else:
            # For local instance on default port
            self.client = QdrantClient(host="localhost", port=6333, timeout=10)

        self.collection_name = "tasks"
        self.vector_size = 1536  # Standard size for embeddings

        # Initialize the collection if it doesn't exist
        self._initialize_collection()

    def _initialize_collection(self):
        """
        Initialize the Qdrant collection for storing task vectors
        """
        try:
            collections = self.client.get_collections()
            collection_exists = any(col.name == self.collection_name for col in collections.collections)

            if not collection_exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Qdrant collection {self.collection_name} already exists")
        except Exception as e:
            logger.error(f"Error initializing Qdrant collection: {str(e)}")

    async def add_vector(self, task_id: str, embedding: List[float], payload: Dict[str, Any]):
        """
        Add a vector representation of a task to Qdrant
        """
        try:
            points = [
                models.PointStruct(
                    id=task_id,
                    vector=embedding,
                    payload=payload
                )
            ]

            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            return {"status": "success", "message": "Vector added successfully"}
        except Exception as e:
            logger.error(f"Error adding vector to Qdrant: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def search_similar(self, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar tasks based on vector similarity
        """
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit
            )

            return [
                {
                    "id": point.id,
                    "payload": point.payload,
                    "score": point.score
                }
                for point in results
            ]
        except Exception as e:
            logger.error(f"Error searching in Qdrant: {str(e)}")
            return []

    async def delete_vector(self, task_id: str):
        """
        Delete a vector from Qdrant by task ID
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[task_id]
                )
            )
            return {"status": "success", "message": "Vector deleted successfully"}
        except Exception as e:
            logger.error(f"Error deleting vector from Qdrant: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def health_check(self) -> bool:
        """
        Check if Qdrant service is accessible
        """
        try:
            # Try to get collection info to test connectivity
            self.client.get_collection(self.collection_name)
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {str(e)}")
            return False


# Global instance
qdrant_service = QdrantService()