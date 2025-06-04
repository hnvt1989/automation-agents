"""Graph Knowledge Manager for integrating Graphiti with our RAG system."""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
import uuid
import json
from pathlib import Path

try:
    from graphiti_core import Graphiti
    from graphiti_core.edges import EntityEdge
    from graphiti_core.nodes import EpisodeType
    from graphiti_core.utils.maintenance.graph_data_operations import clear_data
    from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF
    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False
    # Dummy classes for when Graphiti is not available
    Graphiti = None
    EntityEdge = None
    EpisodeType = None
    clear_data = None
    EDGE_HYBRID_SEARCH_RRF = None

from src.core.exceptions import GraphDBError
from src.utils.logging import log_info, log_error, log_warning


@dataclass
class GraphEntity:
    """Represents an entity in the knowledge graph."""
    name: str
    entity_type: str
    entity_id: str
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class GraphRelationship:
    """Represents a relationship between entities."""
    source_id: str
    target_id: str
    relationship_type: str
    fact: str
    properties: Dict[str, Any] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


@dataclass
class GraphSearchResult:
    """Result from a graph search query."""
    fact: str
    source_node_id: str
    target_node_id: str
    relevance_score: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class GraphKnowledgeManager:
    """Manages knowledge graph operations using Graphiti."""
    
    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        openai_api_key: Optional[str] = None
    ):
        """Initialize GraphKnowledgeManager.
        
        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            openai_api_key: OpenAI API key for entity extraction
        """
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.openai_api_key = openai_api_key
        
        self._initialized = False
        self.client: Optional[Graphiti] = None
        self.driver = None
    
    async def initialize(self):
        """Initialize the Graphiti client and Neo4j connection."""
        if self._initialized:
            return
        
        if not GRAPHITI_AVAILABLE:
            log_error("Graphiti is not installed. Please install with: pip install graphiti-core")
            raise GraphDBError("Graphiti is not installed")
        
        try:
            # Set OpenAI API key environment variable if provided
            if self.openai_api_key:
                import os
                os.environ["OPENAI_API_KEY"] = self.openai_api_key
            
            # Initialize Graphiti client
            self.client = Graphiti(
                self.neo4j_uri,
                self.neo4j_user,
                self.neo4j_password
            )
            
            # Store driver reference for direct Neo4j operations
            self.driver = self.client.driver
            
            # Build indices and constraints
            try:
                await self.client.build_indices_and_constraints()
                log_info("Graph indices and constraints created successfully")
            except Exception as index_error:
                # Check if it's a duplicate index error
                error_str = str(index_error)
                if "EquivalentSchemaRuleAlreadyExists" in error_str or "already exists" in error_str.lower():
                    log_info("Graph indices already exist, continuing with initialization")
                else:
                    # Re-raise if it's a different error
                    raise
            
            self._initialized = True
            log_info("GraphKnowledgeManager initialized successfully")
            
        except Exception as e:
            log_error(f"Failed to initialize GraphKnowledgeManager: {str(e)}")
            raise GraphDBError(f"Failed to initialize graph database: {str(e)}")
    
    async def add_document_episode(
        self,
        content: str,
        metadata: Dict[str, Any],
        name: str,
        reference_time: Optional[datetime] = None
    ) -> str:
        """Add a document as an episode to the graph.
        
        Args:
            content: Document content
            metadata: Document metadata
            name: Episode name
            reference_time: Optional timestamp for the episode
            
        Returns:
            Episode ID
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Format content for better entity extraction
            episode_body = self._format_content_for_extraction(content, metadata)
            
            # Add episode
            episode_id = str(uuid.uuid4())
            await self.client.add_episode(
                name=name,
                episode_body=episode_body,
                source=EpisodeType.json,  # Use JSON for better entity extraction
                source_description=metadata.get('source', 'document'),
                reference_time=reference_time or datetime.now(timezone.utc)
            )
            
            log_info(f"Added document episode: {name} (ID: {episode_id})")
            return episode_id
            
        except Exception as e:
            log_error(f"Failed to add document episode: {str(e)}")
            raise GraphDBError(f"Failed to add episode: {str(e)}")
    
    async def add_conversation_episode(
        self,
        messages: List[Dict[str, Any]],
        conversation_id: str,
        platform: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a conversation as an episode to the graph.
        
        Args:
            messages: List of message dictionaries
            conversation_id: Unique conversation identifier
            platform: Conversation platform
            metadata: Additional metadata
            
        Returns:
            Episode ID
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Format conversation for entity extraction
            conversation_text = self._format_conversation(messages)
            
            # Create structured data for better extraction
            episode_data = {
                "conversation_id": conversation_id,
                "platform": platform,
                "participants": list(set(msg.get("sender", "Unknown") for msg in messages)),
                "messages": conversation_text,
                "metadata": metadata or {}
            }
            
            episode_id = str(uuid.uuid4())
            await self.client.add_episode(
                name=f"Conversation: {conversation_id}",
                episode_body=json.dumps(episode_data),
                source=EpisodeType.json,
                source_description=f"{platform} conversation",
                reference_time=datetime.now(timezone.utc)
            )
            
            log_info(f"Added conversation episode: {conversation_id}")
            return episode_id
            
        except Exception as e:
            log_error(f"Failed to add conversation episode: {str(e)}")
            raise GraphDBError(f"Failed to add episode: {str(e)}")
    
    async def search_entities(
        self,
        query: str,
        center_node_uuid: Optional[str] = None,
        num_results: int = 10
    ) -> List[GraphSearchResult]:
        """Search for entities and relationships in the graph.
        
        Args:
            query: Search query
            center_node_uuid: Optional center node for proximity-based ranking
            num_results: Number of results to return
            
        Returns:
            List of search results
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Use Graphiti's search with RRF (Reciprocal Rank Fusion)
            edge_results = await self.client.search(
                query,
                center_node_uuid=center_node_uuid,
                num_results=num_results,
                search_config=EDGE_HYBRID_SEARCH_RRF
            )
            
            # Convert to our result format
            results = []
            for edge in edge_results:
                # Calculate relevance score (inverse of rank)
                relevance_score = 1.0 / (edge_results.index(edge) + 1)
                
                result = GraphSearchResult(
                    fact=edge.fact,
                    source_node_id=edge.source_node_uuid,
                    target_node_id=edge.target_node_uuid,
                    relevance_score=relevance_score,
                    metadata={
                        "created_at": edge.created_at.isoformat() if edge.created_at else None,
                        "episode_id": edge.episode_uuid
                    }
                )
                results.append(result)
            
            log_info(f"Graph search for '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            log_error(f"Failed to search entities: {str(e)}")
            raise GraphDBError(f"Failed to search graph: {str(e)}")
    
    async def get_entity_relationships(
        self,
        entity_name: str,
        relationship_type: Optional[str] = None
    ) -> List[GraphRelationship]:
        """Get all relationships for a specific entity.
        
        Args:
            entity_name: Name of the entity
            relationship_type: Optional filter for relationship type
            
        Returns:
            List of relationships
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Find the entity node
            nodes = await self.client.get_nodes_by_query(
                {"name": entity_name}
            )
            
            if not nodes:
                log_warning(f"Entity not found: {entity_name}")
                return []
            
            node = nodes[0]
            
            # Get edges for this node
            edges = await self.client.get_edges_by_query(
                {"source_node_uuid": node.uuid}
            )
            
            # Filter by relationship type if specified
            if relationship_type:
                edges = [e for e in edges if relationship_type.lower() in e.fact.lower()]
            
            # Convert to relationships
            relationships = []
            for edge in edges:
                rel = GraphRelationship(
                    source_id=edge.source_node_uuid,
                    target_id=edge.target_node_uuid,
                    relationship_type=self._extract_relationship_type(edge.fact),
                    fact=edge.fact,
                    created_at=edge.created_at
                )
                relationships.append(rel)
            
            return relationships
            
        except Exception as e:
            log_error(f"Failed to get entity relationships: {str(e)}")
            raise GraphDBError(f"Failed to get relationships: {str(e)}")
    
    async def find_related_entities(
        self,
        entity_name: str,
        relationship_type: Optional[str] = None,
        max_depth: int = 2
    ) -> List[GraphEntity]:
        """Find entities related to a given entity.
        
        Args:
            entity_name: Starting entity name
            relationship_type: Optional relationship type filter
            max_depth: Maximum traversal depth
            
        Returns:
            List of related entities
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get direct relationships first
            relationships = await self.get_entity_relationships(
                entity_name,
                relationship_type
            )
            
            # Collect related entity IDs
            related_ids = set()
            for rel in relationships:
                related_ids.add(rel.target_id)
            
            # Get entity details
            entities = []
            for entity_id in related_ids:
                nodes = await self.client.get_nodes_by_query(
                    {"uuid": entity_id}
                )
                
                if nodes:
                    node = nodes[0]
                    entity = GraphEntity(
                        name=node.name,
                        entity_type=self._infer_entity_type(node.name),
                        entity_id=node.uuid
                    )
                    entities.append(entity)
            
            return entities
            
        except Exception as e:
            log_error(f"Failed to find related entities: {str(e)}")
            raise GraphDBError(f"Failed to find related entities: {str(e)}")
    
    async def build_graph_from_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """Build knowledge graph from multiple documents.
        
        Args:
            documents: List of documents with 'content' and 'metadata'
            batch_size: Batch size for processing
            
        Returns:
            Statistics about the graph building process
        """
        if not self._initialized:
            await self.initialize()
        
        stats = {
            "total_documents": len(documents),
            "episodes_created": 0,
            "errors": 0
        }
        
        # Process in batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            # Create tasks for parallel processing
            tasks = []
            for doc in batch:
                task = self.add_document_episode(
                    content=doc.get("content", ""),
                    metadata=doc.get("metadata", {}),
                    name=doc.get("name", f"Document {i}")
                )
                tasks.append(task)
            
            # Execute batch
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successes and errors
            for result in results:
                if isinstance(result, Exception):
                    stats["errors"] += 1
                    log_error(f"Error processing document: {result}")
                else:
                    stats["episodes_created"] += 1
        
        log_info(f"Built graph from {stats['episodes_created']} documents")
        return stats
    
    async def hybrid_search(
        self,
        query: str,
        vector_results: Dict[str, Any],
        num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining vector and graph results.
        
        Args:
            query: Search query
            vector_results: Results from vector search (ChromaDB)
            num_results: Number of final results
            
        Returns:
            Combined and ranked results
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get graph search results
            graph_results = await self.search_entities(query, num_results=num_results)
            
            # Convert vector results to standardized format
            vector_items = []
            if vector_results.get('ids') and vector_results['ids'][0]:
                for i in range(len(vector_results['ids'][0])):
                    item = {
                        'id': vector_results['ids'][0][i],
                        'content': vector_results['documents'][0][i],
                        'score': 1.0 - vector_results['distances'][0][i],  # Convert distance to score
                        'metadata': vector_results['metadatas'][0][i],
                        'source': 'vector'
                    }
                    vector_items.append(item)
            
            # Convert graph results to standardized format
            graph_items = []
            for result in graph_results:
                item = {
                    'id': f"{result.source_node_id}_{result.target_node_id}",
                    'content': result.fact,
                    'score': result.relevance_score,
                    'metadata': result.metadata,
                    'source': 'graph'
                }
                graph_items.append(item)
            
            # Combine and re-rank using RRF
            combined = self._reciprocal_rank_fusion(
                [vector_items, graph_items],
                k=60  # RRF parameter
            )
            
            # Return top results
            return combined[:num_results]
            
        except Exception as e:
            log_error(f"Failed to perform hybrid search: {str(e)}")
            raise GraphDBError(f"Failed to perform hybrid search: {str(e)}")
    
    async def get_entity_timeline(
        self,
        entity_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get timeline of events/episodes for an entity.
        
        Args:
            entity_name: Entity to track
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            
        Returns:
            List of timeline events
        """
        # Implementation would query episodes mentioning the entity
        # within the date range and return them chronologically
        raise NotImplementedError("Timeline analysis not yet implemented")
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph.
        
        Returns:
            Dictionary with graph statistics
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            async with self.driver.session() as session:
                # Get node count and types
                node_query = """
                MATCH (n)
                RETURN count(n) as node_count,
                       collect(DISTINCT labels(n)) as node_labels
                """
                node_result = await session.run(node_query)
                node_data = await node_result.single()
                
                # Get edge count and types
                edge_query = """
                MATCH ()-[r]->()
                RETURN count(r) as edge_count,
                       collect(DISTINCT type(r)) as edge_types
                """
                edge_result = await session.run(edge_query)
                edge_data = await edge_result.single()
                
                return {
                    "total_nodes": node_data.get("node_count", 0),
                    "total_edges": edge_data.get("edge_count", 0),
                    "node_types": node_data.get("node_labels", []),
                    "edge_types": edge_data.get("edge_types", [])
                }
                
        except Exception as e:
            log_error(f"Failed to get graph statistics: {str(e)}")
            raise GraphDBError(f"Failed to get statistics: {str(e)}")
    
    async def clear_graph(self):
        """Clear all data from the graph database."""
        if not self._initialized:
            await self.initialize()
        
        try:
            await clear_data(self.driver)
            log_info("Graph database cleared")
        except Exception as e:
            log_error(f"Failed to clear graph: {str(e)}")
            raise GraphDBError(f"Failed to clear graph: {str(e)}")
    
    async def close(self):
        """Close connections and cleanup resources."""
        if self.driver:
            await self.driver.close()
        self._initialized = False
        log_info("GraphKnowledgeManager closed")
    
    # Helper methods
    
    def _format_content_for_extraction(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Format content for better entity extraction."""
        # Create structured format for Graphiti
        structured_data = {
            "content": content,
            "metadata": metadata,
            "source_type": metadata.get("source_type", "document")
        }
        return json.dumps(structured_data)
    
    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """Format conversation messages for entity extraction."""
        formatted_messages = []
        for msg in messages:
            sender = msg.get("sender", "Unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            
            formatted_msg = f"{sender}: {content}"
            if timestamp:
                formatted_msg = f"[{timestamp}] {formatted_msg}"
            
            formatted_messages.append(formatted_msg)
        
        return "\n".join(formatted_messages)
    
    def _extract_relationship_type(self, fact: str) -> str:
        """Extract relationship type from fact text."""
        # Simple heuristic - could be enhanced with NLP
        if "works on" in fact.lower() or "working on" in fact.lower():
            return "WORKS_ON"
        elif "manages" in fact.lower() or "leads" in fact.lower():
            return "MANAGES"
        elif "reports to" in fact.lower():
            return "REPORTS_TO"
        elif "collaborates" in fact.lower() or "works with" in fact.lower():
            return "COLLABORATES_WITH"
        else:
            return "RELATED_TO"
    
    def _infer_entity_type(self, entity_name: str) -> str:
        """Infer entity type from name."""
        # Simple heuristics - could be enhanced
        name_lower = entity_name.lower()
        
        if any(word in name_lower for word in ["project", "initiative", "program"]):
            return "project"
        elif any(word in name_lower for word in ["team", "department", "group"]):
            return "organization"
        elif name_lower[0].isupper() and " " not in entity_name:
            return "person"  # Single capitalized word likely a person
        else:
            return "entity"
    
    def _reciprocal_rank_fusion(
        self,
        result_lists: List[List[Dict[str, Any]]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """Perform Reciprocal Rank Fusion on multiple result lists."""
        # Calculate RRF scores
        rrf_scores = {}
        
        for result_list in result_lists:
            for rank, item in enumerate(result_list):
                item_id = item['id']
                if item_id not in rrf_scores:
                    rrf_scores[item_id] = {
                        'score': 0,
                        'item': item
                    }
                
                # RRF formula: 1 / (k + rank)
                rrf_scores[item_id]['score'] += 1.0 / (k + rank + 1)
        
        # Sort by RRF score
        sorted_items = sorted(
            rrf_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        # Return items with combined scores
        results = []
        for item_data in sorted_items:
            item = item_data['item'].copy()
            item['combined_score'] = item_data['score']
            results.append(item)
        
        return results
    
    async def extract_entities_from_text(self, text: str) -> List[GraphEntity]:
        """Extract entities from text using LLM."""
        # This would use OpenAI or another LLM to extract entities
        # For now, returning empty list as placeholder
        return []
    
    async def _extract_entities_with_llm(self, text: str) -> List[GraphEntity]:
        """Extract entities using LLM (placeholder for testing)."""
        # In real implementation, this would call OpenAI
        # For testing, we'll parse some basic patterns
        entities = []
        
        # Simple pattern matching for testing
        import re
        
        # Find capitalized words (potential person names)
        person_pattern = r'\b[A-Z][a-z]+\b'
        potential_persons = re.findall(person_pattern, text)
        
        for name in potential_persons:
            if name not in ['The', 'This', 'That', 'These', 'Those']:
                entities.append(GraphEntity(
                    name=name,
                    entity_type="person",
                    entity_id=f"{name.lower()}_{uuid.uuid4().hex[:8]}"
                ))
        
        # Find project references
        project_pattern = r'Project\s+[A-Z]\w*'
        projects = re.findall(project_pattern, text)
        
        for project in projects:
            entities.append(GraphEntity(
                name=project,
                entity_type="project",
                entity_id=f"{project.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
            ))
        
        return entities