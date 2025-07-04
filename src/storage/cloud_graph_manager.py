"""Simplified graph manager for cloud deployments without vector support."""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from src.storage.neo4j_cloud import get_neo4j_cloud_client
from src.utils.logging import log_info, log_warning, log_error


class CloudGraphManager:
    """Simplified graph manager for Neo4j Aura without vector embeddings."""
    
    def __init__(self):
        """Initialize cloud graph manager."""
        self.client = get_neo4j_cloud_client()
        log_info("CloudGraphManager initialized (no vector support)")
    
    async def add_document(self, content: str, metadata: Dict[str, Any]) -> str:
        """Add document to graph without embeddings."""
        # This is a simplified version - just create basic nodes
        doc_id = metadata.get('id', f"doc_{datetime.now().timestamp()}")
        
        self.client.create_entity("Document", {
            "id": doc_id,
            "content": content[:1000],  # Store truncated content
            "metadata": str(metadata),
            "created_at": datetime.now().isoformat()
        })
        
        return doc_id
    
    async def search_entities(self, query: str, num_results: int = 10) -> List[Dict]:
        """Simple text search without vectors."""
        results = self.client.search_entities(query, limit=num_results)
        return results
    
    def close(self):
        """Close connection."""
        self.client.close()


# Factory function to get appropriate manager
def get_graph_manager():
    """Get appropriate graph manager based on environment."""
    if os.getenv("NEO4J_URI", "").startswith("neo4j+s://"):
        return CloudGraphManager()
    else:
        # No local graph manager available without Graphiti
        log_warning("Local graph manager not available (Graphiti removed)")
        return None
