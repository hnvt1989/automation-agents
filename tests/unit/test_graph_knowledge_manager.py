"""Unit tests for GraphKnowledgeManager class."""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from typing import List, Dict, Any
import asyncio

from src.storage.graph_knowledge_manager import (
    GraphKnowledgeManager,
    GraphEntity,
    GraphRelationship,
    GraphSearchResult
)
from src.core.exceptions import GraphDBError


class TestGraphKnowledgeManager:
    """Test GraphKnowledgeManager functionality."""
    
    @pytest.fixture
    def mock_graphiti_client(self):
        """Create a mock Graphiti client."""
        client = AsyncMock()
        client.build_indices_and_constraints = AsyncMock()
        client.add_episode = AsyncMock()
        client.search = AsyncMock()
        client.get_nodes_by_query = AsyncMock()
        client.get_edges_by_query = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_neo4j_driver(self):
        """Create a mock Neo4j driver."""
        driver = MagicMock()
        return driver
    
    @pytest.fixture
    async def graph_manager(self, mock_graphiti_client, mock_neo4j_driver):
        """Create GraphKnowledgeManager with mocked dependencies."""
        with patch('src.storage.graph_knowledge_manager.Graphiti') as mock_graphiti:
            mock_graphiti.return_value = mock_graphiti_client
            
            manager = GraphKnowledgeManager(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password"
            )
            manager.client = mock_graphiti_client
            manager.driver = mock_neo4j_driver
            
            yield manager
            
            # Cleanup
            if hasattr(manager, 'close'):
                await manager.close()
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_graphiti_client):
        """Test GraphKnowledgeManager initialization."""
        with patch('src.storage.graph_knowledge_manager.Graphiti') as mock_graphiti:
            mock_graphiti.return_value = mock_graphiti_client
            
            manager = GraphKnowledgeManager(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password"
            )
            
            assert manager.neo4j_uri == "bolt://localhost:7687"
            assert manager.client == mock_graphiti_client
            mock_graphiti_client.build_indices_and_constraints.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_document_episode(self, graph_manager):
        """Test adding a document as an episode to the graph."""
        # Test data
        content = "Alice is working on Project X with Bob. They meet every Tuesday."
        metadata = {
            'source': '/docs/project.md',
            'type': 'document'
        }
        
        # Add document episode
        episode_id = await graph_manager.add_document_episode(
            content=content,
            metadata=metadata,
            name="Project Documentation"
        )
        
        # Verify
        assert episode_id is not None
        graph_manager.client.add_episode.assert_called_once()
        call_args = graph_manager.client.add_episode.call_args[1]
        assert call_args['name'] == "Project Documentation"
        assert call_args['episode_body'] == content
        assert 'json' in call_args['source']  # Should use JSON source for entity extraction
    
    @pytest.mark.asyncio
    async def test_add_conversation_episode(self, graph_manager):
        """Test adding a conversation as an episode."""
        messages = [
            {"sender": "Alice", "content": "How's Project X going?", "timestamp": "2024-01-01T10:00:00"},
            {"sender": "Bob", "content": "Great! We're ahead of schedule.", "timestamp": "2024-01-01T10:01:00"}
        ]
        
        episode_id = await graph_manager.add_conversation_episode(
            messages=messages,
            conversation_id="conv_123",
            platform="slack"
        )
        
        assert episode_id is not None
        graph_manager.client.add_episode.assert_called_once()
        call_args = graph_manager.client.add_episode.call_args[1]
        assert "Alice: How's Project X going?" in call_args['episode_body']
        assert "Bob: Great! We're ahead of schedule." in call_args['episode_body']
    
    @pytest.mark.asyncio
    async def test_search_entities(self, graph_manager):
        """Test searching for entities in the graph."""
        # Mock search results
        mock_results = [
            MagicMock(
                fact="Alice works on Project X",
                source_node_uuid="node_1",
                target_node_uuid="node_2",
                created_at=datetime.now(timezone.utc)
            )
        ]
        graph_manager.client.search.return_value = mock_results
        
        # Search
        results = await graph_manager.search_entities(
            query="Project X",
            center_node_uuid="user_123",
            num_results=5
        )
        
        # Verify
        assert len(results) == 1
        assert isinstance(results[0], GraphSearchResult)
        assert results[0].fact == "Alice works on Project X"
        graph_manager.client.search.assert_called_once_with(
            "Project X",
            center_node_uuid="user_123",
            num_results=5
        )
    
    @pytest.mark.asyncio
    async def test_get_entity_relationships(self, graph_manager):
        """Test getting relationships for an entity."""
        # Mock node and edges
        mock_node = MagicMock(name="Alice", uuid="alice_uuid")
        mock_edges = [
            MagicMock(
                source_node_uuid="alice_uuid",
                target_node_uuid="project_uuid",
                fact="Alice leads Project X",
                created_at=datetime.now(timezone.utc)
            ),
            MagicMock(
                source_node_uuid="alice_uuid",
                target_node_uuid="bob_uuid",
                fact="Alice collaborates with Bob",
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        graph_manager.client.get_nodes_by_query.return_value = [mock_node]
        graph_manager.client.get_edges_by_query.return_value = mock_edges
        
        # Get relationships
        relationships = await graph_manager.get_entity_relationships("Alice")
        
        # Verify
        assert len(relationships) == 2
        assert all(isinstance(r, GraphRelationship) for r in relationships)
        assert relationships[0].source_id == "alice_uuid"
        assert relationships[0].fact == "Alice leads Project X"
    
    @pytest.mark.asyncio
    async def test_find_related_entities(self, graph_manager):
        """Test finding entities related to a given entity."""
        # Mock data
        mock_edges = [
            MagicMock(
                source_node_uuid="alice_uuid",
                target_node_uuid="project_uuid",
                fact="Alice works on Project X"
            )
        ]
        mock_target_node = MagicMock(name="Project X", uuid="project_uuid")
        
        graph_manager.client.get_edges_by_query.return_value = mock_edges
        graph_manager.client.get_nodes_by_query.return_value = [mock_target_node]
        
        # Find related entities
        related = await graph_manager.find_related_entities(
            entity_name="Alice",
            relationship_type=None,  # Any relationship
            max_depth=1
        )
        
        # Verify
        assert len(related) == 1
        assert isinstance(related[0], GraphEntity)
        assert related[0].name == "Project X"
        assert related[0].entity_id == "project_uuid"
    
    @pytest.mark.asyncio
    async def test_extract_entities_from_text(self, graph_manager):
        """Test entity extraction from text."""
        text = "Alice and Bob are working on Project X. They report to Charlie."
        
        # Mock entity extraction (this would normally use LLM)
        expected_entities = [
            GraphEntity(name="Alice", entity_type="person", entity_id="alice_1"),
            GraphEntity(name="Bob", entity_type="person", entity_id="bob_1"),
            GraphEntity(name="Project X", entity_type="project", entity_id="project_1"),
            GraphEntity(name="Charlie", entity_type="person", entity_id="charlie_1")
        ]
        
        with patch.object(graph_manager, '_extract_entities_with_llm', return_value=expected_entities):
            entities = await graph_manager.extract_entities_from_text(text)
        
        assert len(entities) == 4
        assert all(isinstance(e, GraphEntity) for e in entities)
        assert {e.name for e in entities} == {"Alice", "Bob", "Project X", "Charlie"}
    
    @pytest.mark.asyncio
    async def test_build_graph_from_documents(self, graph_manager):
        """Test building graph from multiple documents."""
        documents = [
            {
                "content": "Alice leads Project X",
                "metadata": {"source": "doc1.md"}
            },
            {
                "content": "Bob joins Project X team",
                "metadata": {"source": "doc2.md"}
            }
        ]
        
        # Build graph
        stats = await graph_manager.build_graph_from_documents(documents)
        
        # Verify
        assert stats['total_documents'] == 2
        assert stats['episodes_created'] == 2
        assert graph_manager.client.add_episode.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_graph_statistics(self, graph_manager):
        """Test getting graph statistics."""
        # Mock Neo4j query results
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = {
            'node_count': 150,
            'edge_count': 320,
            'node_labels': ['Person', 'Project', 'Document'],
            'edge_types': ['WORKS_ON', 'MENTIONS', 'REPORTS_TO']
        }
        
        mock_session.run.return_value = mock_result
        graph_manager.driver.session.return_value.__aenter__.return_value = mock_session
        
        # Get stats
        stats = await graph_manager.get_graph_statistics()
        
        # Verify
        assert stats['total_nodes'] == 150
        assert stats['total_edges'] == 320
        assert 'Person' in stats['node_types']
        assert 'WORKS_ON' in stats['edge_types']
    
    @pytest.mark.asyncio
    async def test_clear_graph(self, graph_manager):
        """Test clearing the graph database."""
        # Mock clear operation
        mock_clear = AsyncMock()
        with patch('src.storage.graph_knowledge_manager.clear_data', mock_clear):
            await graph_manager.clear_graph()
            
            mock_clear.assert_called_once_with(graph_manager.driver)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, graph_manager):
        """Test error handling in graph operations."""
        # Simulate connection error
        graph_manager.client.add_episode.side_effect = Exception("Connection failed")
        
        with pytest.raises(GraphDBError) as exc_info:
            await graph_manager.add_document_episode(
                content="Test content",
                metadata={},
                name="Test"
            )
        
        assert "Failed to add episode" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, graph_manager):
        """Test concurrent graph operations."""
        # Create multiple episodes concurrently
        tasks = []
        for i in range(5):
            task = graph_manager.add_document_episode(
                content=f"Document {i} content",
                metadata={"doc_id": i},
                name=f"Doc {i}"
            )
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify all succeeded
        assert len(results) == 5
        assert all(r is not None for r in results)
        assert graph_manager.client.add_episode.call_count == 5


class TestGraphEntity:
    """Test GraphEntity data class."""
    
    def test_entity_creation(self):
        """Test creating a GraphEntity."""
        entity = GraphEntity(
            name="Alice",
            entity_type="person",
            entity_id="alice_123",
            properties={"role": "developer", "team": "backend"}
        )
        
        assert entity.name == "Alice"
        assert entity.entity_type == "person"
        assert entity.entity_id == "alice_123"
        assert entity.properties["role"] == "developer"
    
    def test_entity_equality(self):
        """Test GraphEntity equality comparison."""
        entity1 = GraphEntity("Alice", "person", "alice_123")
        entity2 = GraphEntity("Alice", "person", "alice_123")
        entity3 = GraphEntity("Bob", "person", "bob_123")
        
        assert entity1 == entity2
        assert entity1 != entity3


class TestGraphRelationship:
    """Test GraphRelationship data class."""
    
    def test_relationship_creation(self):
        """Test creating a GraphRelationship."""
        rel = GraphRelationship(
            source_id="alice_123",
            target_id="project_123",
            relationship_type="WORKS_ON",
            fact="Alice works on Project X",
            properties={"since": "2024-01-01"}
        )
        
        assert rel.source_id == "alice_123"
        assert rel.target_id == "project_123"
        assert rel.relationship_type == "WORKS_ON"
        assert rel.fact == "Alice works on Project X"
        assert rel.properties["since"] == "2024-01-01"


class TestGraphSearchResult:
    """Test GraphSearchResult data class."""
    
    def test_search_result_creation(self):
        """Test creating a GraphSearchResult."""
        result = GraphSearchResult(
            fact="Alice leads Project X",
            source_node_id="alice_123",
            target_node_id="project_123",
            relevance_score=0.95,
            metadata={"confidence": "high"}
        )
        
        assert result.fact == "Alice leads Project X"
        assert result.relevance_score == 0.95
        assert result.metadata["confidence"] == "high"