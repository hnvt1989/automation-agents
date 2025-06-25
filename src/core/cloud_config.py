"""Cloud service configuration."""

import os
from typing import Optional


class CloudConfig:
    """Configuration for cloud services."""
    
    @staticmethod
    def is_supabase_configured() -> bool:
        """Check if Supabase is configured."""
        return bool(
            os.getenv("SUPABASE_URL") and 
            os.getenv("SUPABASE_KEY")
        )
    
    @staticmethod
    def is_neo4j_cloud_configured() -> bool:
        """Check if Neo4j cloud is configured."""
        return bool(
            os.getenv("NEO4J_URI") and 
            os.getenv("NEO4J_PASSWORD") and
            os.getenv("NEO4J_URI", "").startswith(("neo4j+s://", "neo4j+ssc://"))
        )
    
    @staticmethod
    def use_cloud_storage() -> bool:
        """Determine if cloud storage should be used."""
        # Check environment variable override
        use_cloud = os.getenv("USE_CLOUD_STORAGE", "auto").lower()
        
        if use_cloud == "true":
            return True
        elif use_cloud == "false":
            return False
        else:  # auto
            # Use cloud if any cloud service is configured
            return CloudConfig.is_supabase_configured() or CloudConfig.is_neo4j_cloud_configured()
    
    @staticmethod
    def get_storage_info() -> dict:
        """Get information about storage configuration."""
        return {
            "use_cloud": CloudConfig.use_cloud_storage(),
            "supabase_configured": CloudConfig.is_supabase_configured(),
            "neo4j_cloud_configured": CloudConfig.is_neo4j_cloud_configured(),
            "vector_storage": "Supabase" if CloudConfig.is_supabase_configured() else "Not configured",
            "graph_storage": "Neo4j Aura" if CloudConfig.is_neo4j_cloud_configured() else "Neo4j Local"
        }