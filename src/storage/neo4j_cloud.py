"""Neo4j cloud client for hosted Neo4j Aura instances."""

import os
from typing import Dict, List, Any, Optional, Tuple
from neo4j import GraphDatabase, Driver, Result
from neo4j.exceptions import Neo4jError

from src.utils.logging import log_info, log_error, log_warning
from src.core.config import get_settings


class Neo4jCloudClient:
    """Client for interacting with hosted Neo4j Aura instances."""
    
    def __init__(self):
        """Initialize Neo4j cloud client."""
        # Get connection details from environment
        self.uri = os.getenv("NEO4J_URI")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD")
        
        if not self.uri or not self.password:
            raise ValueError("NEO4J_URI and NEO4J_PASSWORD must be set")
        
        # Validate URI format for Neo4j Aura
        if not self.uri.startswith(("neo4j+s://", "neo4j+ssc://")):
            log_warning("URI should use neo4j+s:// or neo4j+ssc:// for secure cloud connections")
        
        self.driver: Optional[Driver] = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to Neo4j Aura."""
        try:
            # For neo4j+s:// or neo4j+ssc:// URIs, encryption is already specified in the scheme
            # Don't pass encrypted parameter
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=3600,  # 1 hour
                max_connection_pool_size=50,
                fetch_size=1000
            )
            
            # Verify connectivity
            self.driver.verify_connectivity()
            log_info(f"Connected to Neo4j Aura at {self.uri}")
            
        except Exception as e:
            log_error(f"Failed to connect to Neo4j Aura: {str(e)}")
            raise
    
    def close(self) -> None:
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            log_info("Neo4j connection closed")
    
    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """Execute a Cypher query and return results.
        
        Args:
            query: Cypher query string
            parameters: Optional query parameters
            
        Returns:
            List of result records as dictionaries
        """
        if not self.driver:
            raise RuntimeError("Neo4j driver not initialized")
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Neo4jError as e:
            log_error(f"Query execution failed: {str(e)}")
            raise
    
    def create_entity(self, label: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create a node with given label and properties.
        
        Args:
            label: Node label
            properties: Node properties
            
        Returns:
            Created node data
        """
        query = f"""
        CREATE (n:{label} $props)
        RETURN n
        """
        
        result = self.execute_query(query, {"props": properties})
        return result[0]["n"] if result else {}
    
    def create_relationship(
        self,
        from_id: str,
        to_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a relationship between two nodes.
        
        Args:
            from_id: Source node ID
            to_id: Target node ID
            relationship_type: Type of relationship
            properties: Optional relationship properties
            
        Returns:
            Created relationship data
        """
        query = f"""
        MATCH (a {{id: $from_id}})
        MATCH (b {{id: $to_id}})
        CREATE (a)-[r:{relationship_type} $props]->(b)
        RETURN r
        """
        
        params = {
            "from_id": from_id,
            "to_id": to_id,
            "props": properties or {}
        }
        
        result = self.execute_query(query, params)
        return result[0]["r"] if result else {}
    
    def find_entities(
        self,
        label: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Find nodes matching criteria.
        
        Args:
            label: Optional node label filter
            properties: Optional property filters
            limit: Maximum results to return
            
        Returns:
            List of matching nodes
        """
        # Build query dynamically
        match_clause = "MATCH (n"
        if label:
            match_clause += f":{label}"
        
        where_conditions = []
        params = {"limit": limit}
        
        if properties:
            for key, value in properties.items():
                where_conditions.append(f"n.{key} = ${key}")
                params[key] = value
        
        match_clause += ")"
        
        query = match_clause
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        query += " RETURN n LIMIT $limit"
        
        result = self.execute_query(query, params)
        return [record["n"] for record in result]
    
    def find_related(
        self,
        entity_id: str,
        relationship_type: Optional[str] = None,
        direction: str = "both",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Find entities related to a given entity.
        
        Args:
            entity_id: ID of the source entity
            relationship_type: Optional relationship type filter
            direction: 'in', 'out', or 'both'
            limit: Maximum results
            
        Returns:
            List of related entities with relationship info
        """
        # Build relationship pattern
        if direction == "out":
            pattern = f"(n {{id: $entity_id}})-[r{':' + relationship_type if relationship_type else ''}]->(m)"
        elif direction == "in":
            pattern = f"(n {{id: $entity_id}})<-[r{':' + relationship_type if relationship_type else ''}]-(m)"
        else:  # both
            pattern = f"(n {{id: $entity_id}})-[r{':' + relationship_type if relationship_type else ''}]-(m)"
        
        query = f"""
        MATCH {pattern}
        RETURN m as entity, type(r) as relationship_type, properties(r) as relationship_props
        LIMIT $limit
        """
        
        params = {"entity_id": entity_id, "limit": limit}
        return self.execute_query(query, params)
    
    def search_entities(self, search_text: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search entities by text across multiple properties.
        
        Args:
            search_text: Text to search for
            limit: Maximum results
            
        Returns:
            List of matching entities
        """
        query = """
        MATCH (n)
        WHERE ANY(prop IN keys(n) WHERE toString(n[prop]) CONTAINS $search_text)
        RETURN n, labels(n) as labels
        LIMIT $limit
        """
        
        params = {"search_text": search_text, "limit": limit}
        result = self.execute_query(query, params)
        
        return [
            {
                "entity": record["n"],
                "labels": record["labels"]
            }
            for record in result
        ]
    
    def get_graph_summary(self) -> Dict[str, Any]:
        """Get summary statistics about the graph.
        
        Returns:
            Dictionary with graph statistics
        """
        queries = {
            "node_count": "MATCH (n) RETURN count(n) as count",
            "relationship_count": "MATCH ()-[r]->() RETURN count(r) as count",
            "labels": "CALL db.labels() YIELD label RETURN collect(label) as labels",
            "relationship_types": "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as types"
        }
        
        summary = {}
        for key, query in queries.items():
            try:
                result = self.execute_query(query)
                if key in ["node_count", "relationship_count"]:
                    summary[key] = result[0]["count"] if result else 0
                elif key == "labels":
                    summary[key] = result[0]["labels"] if result else []
                elif key == "relationship_types":
                    summary[key] = result[0]["types"] if result else []
            except Exception as e:
                log_warning(f"Failed to get {key}: {str(e)}")
                summary[key] = None
        
        return summary
    
    def create_indexes(self) -> None:
        """Create recommended indexes for performance."""
        indexes = [
            "CREATE INDEX entity_id IF NOT EXISTS FOR (n:Entity) ON (n.id)",
            "CREATE INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON (n.name)",
            "CREATE INDEX entity_type IF NOT EXISTS FOR (n:Entity) ON (n.type)",
            "CREATE INDEX document_id IF NOT EXISTS FOR (n:Document) ON (n.id)",
            "CREATE INDEX document_title IF NOT EXISTS FOR (n:Document) ON (n.title)"
        ]
        
        for index_query in indexes:
            try:
                self.execute_query(index_query)
                log_info(f"Created index: {index_query}")
            except Exception as e:
                log_warning(f"Index creation failed (may already exist): {str(e)}")
    
    def clear_graph(self) -> None:
        """Clear all data from the graph (use with caution!)."""
        query = "MATCH (n) DETACH DELETE n"
        self.execute_query(query)
        log_info("Graph cleared")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Singleton instance management
_neo4j_cloud_client: Optional[Neo4jCloudClient] = None


def get_neo4j_cloud_client() -> Neo4jCloudClient:
    """Get or create the Neo4j cloud client singleton."""
    global _neo4j_cloud_client
    if _neo4j_cloud_client is None:
        _neo4j_cloud_client = Neo4jCloudClient()
    return _neo4j_cloud_client