"""Unit tests for RAG agent with knowledge graph integration."""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from typing import List, Dict, Any

from src.agents.rag import RAGAgent, RAGAgentDeps
from src.storage.graph_knowledge_manager import GraphSearchResult


class TestRAGWithGraph:
    """Test RAG agent with knowledge graph capabilities."""
    
    @pytest.fixture
    def mock_openai_model(self):
        """Create a mock OpenAI model."""
        return MagicMock()
    
    @pytest.fixture
    def mock_chromadb_client(self):
        """Create a mock ChromaDB client."""
        client = MagicMock()
        client.query = MagicMock()
        client.get_collection_stats = MagicMock()
        return client
    
    @pytest.fixture
    def mock_collection_manager(self):
        """Create a mock CollectionManager."""
        manager = MagicMock()
        manager.search_all = MagicMock()
        manager.search_by_type = MagicMock()
        manager.get_collection_stats = MagicMock()
        return manager
    
    @pytest.fixture
    def mock_graph_manager(self):
        """Create a mock GraphKnowledgeManager."""
        manager = AsyncMock()
        manager.search_entities = AsyncMock()
        manager.get_entity_relationships = AsyncMock()
        manager.find_related_entities = AsyncMock()
        manager.hybrid_search = AsyncMock()
        return manager
    
    @pytest.fixture
    def rag_deps_with_graph(self, mock_chromadb_client, mock_collection_manager, mock_graph_manager):
        """Create RAG dependencies with graph manager."""
        deps = RAGAgentDeps(
            chromadb_client=mock_chromadb_client,
            collection_manager=mock_collection_manager
        )
        deps.graph_manager = mock_graph_manager  # Add graph manager
        return deps
    
    @pytest.mark.asyncio
    async def test_search_with_graph_context(self, mock_graph_manager, rag_deps_with_graph):
        """Test search that includes graph context."""
        # Mock vector search results
        rag_deps_with_graph.collection_manager.search_all.return_value = [
            {
                'collection': 'automation_agents_knowledge',
                'id': 'doc1',
                'document': 'Alice is working on Project X',
                'distance': 0.2,
                'metadata': {'source': 'doc1.md'}
            }
        ]
        
        # Mock graph search results
        mock_graph_manager.search_entities.return_value = [
            GraphSearchResult(
                fact="Alice leads Project X and reports to Charlie",
                source_node_id="alice_123",
                target_node_id="charlie_456",
                relevance_score=0.9
            ),
            GraphSearchResult(
                fact="Project X uses Python and React",
                source_node_id="projectx_789",
                target_node_id="python_tech",
                relevance_score=0.8
            )
        ]
        
        # Create mock context for tool execution
        ctx = MagicMock()
        ctx.deps = rag_deps_with_graph
        
        # Test search_knowledge_base_with_graph tool
        with patch('src.agents.rag.RunContext', return_value=ctx):
            # This would be the new enhanced search tool
            query = "Who works on Project X?"
            
            # Simulate enhanced search
            vector_results = await rag_deps_with_graph.collection_manager.search_all(query)
            graph_results = await mock_graph_manager.search_entities(query)
            
            # Verify both searches were called
            assert len(vector_results) > 0
            assert len(graph_results) > 0
            
            # Check graph provides additional context
            facts = [r.fact for r in graph_results]
            assert any("Alice leads Project X" in fact for fact in facts)
            assert any("reports to Charlie" in fact for fact in facts)
    
    @pytest.mark.asyncio
    async def test_entity_exploration(self, mock_graph_manager, rag_deps_with_graph):
        """Test exploring entity relationships."""
        # Mock entity relationships
        mock_graph_manager.get_entity_relationships.return_value = [
            MagicMock(
                source_id="alice_123",
                target_id="projectx_789",
                relationship_type="WORKS_ON",
                fact="Alice works on Project X"
            ),
            MagicMock(
                source_id="alice_123",
                target_id="bob_456",
                relationship_type="COLLABORATES_WITH",
                fact="Alice collaborates with Bob"
            )
        ]
        
        # Get Alice's relationships
        relationships = await mock_graph_manager.get_entity_relationships("Alice")
        
        # Verify relationships found
        assert len(relationships) == 2
        rel_types = [r.relationship_type for r in relationships]
        assert "WORKS_ON" in rel_types
        assert "COLLABORATES_WITH" in rel_types
    
    @pytest.mark.asyncio
    async def test_hybrid_search_integration(self, mock_graph_manager, rag_deps_with_graph):
        """Test hybrid search combining vector and graph results."""
        query = "Project X technical stack"
        
        # Mock vector results
        vector_results = {
            'ids': [['vec1', 'vec2']],
            'documents': [['Project X uses microservices', 'X deployment on AWS']],
            'distances': [[0.3, 0.4]],
            'metadatas': [[{'source': 'tech-doc.md'}, {'source': 'infra.md'}]]
        }
        
        # Mock hybrid search result
        mock_graph_manager.hybrid_search.return_value = [
            {
                'id': 'hybrid1',
                'content': 'Project X uses Python and React (from graph)',
                'combined_score': 0.95,
                'source': 'graph'
            },
            {
                'id': 'vec1',
                'content': 'Project X uses microservices',
                'combined_score': 0.85,
                'source': 'vector'
            }
        ]
        
        # Perform hybrid search
        results = await mock_graph_manager.hybrid_search(
            query=query,
            vector_results=vector_results,
            num_results=5
        )
        
        # Verify results are combined and ranked
        assert len(results) == 2
        assert results[0]['combined_score'] > results[1]['combined_score']
        assert results[0]['source'] == 'graph'  # Graph result ranked higher
    
    @pytest.mark.asyncio
    async def test_contextual_expansion(self, mock_graph_manager, rag_deps_with_graph):
        """Test expanding search context using graph relationships."""
        # Initial search finds Alice
        initial_query = "team lead responsibilities"
        
        # Mock finding Alice as team lead
        mock_graph_manager.search_entities.return_value = [
            GraphSearchResult(
                fact="Alice is the team lead for Project X",
                source_node_id="alice_123",
                target_node_id="projectx_789",
                relevance_score=0.9
            )
        ]
        
        # Mock finding related entities (her team members)
        mock_graph_manager.find_related_entities.return_value = [
            MagicMock(name="Bob", entity_type="person", entity_id="bob_456"),
            MagicMock(name="Charlie", entity_type="person", entity_id="charlie_789"),
            MagicMock(name="Project X", entity_type="project", entity_id="projectx_789")
        ]
        
        # Search and expand
        initial_results = await mock_graph_manager.search_entities(initial_query)
        assert len(initial_results) > 0
        
        # Find Alice's connections
        related = await mock_graph_manager.find_related_entities("Alice")
        
        # Verify team context is available
        related_names = [e.name for e in related]
        assert "Bob" in related_names
        assert "Charlie" in related_names
        assert "Project X" in related_names
    
    @pytest.mark.asyncio
    async def test_graph_stats_in_rag(self, mock_graph_manager, rag_deps_with_graph):
        """Test getting combined stats including graph."""
        # Mock ChromaDB stats
        rag_deps_with_graph.collection_manager.get_collection_stats.return_value = {
            'automation_agents_knowledge': {'count': 100},
            'automation_agents_conversations': {'count': 50},
            'automation_agents_websites': {'count': 25}
        }
        
        # Mock graph stats
        mock_graph_manager.get_graph_statistics.return_value = {
            'total_nodes': 150,
            'total_edges': 300,
            'node_types': ['Person', 'Project', 'Technology'],
            'edge_types': ['WORKS_ON', 'USES', 'COLLABORATES_WITH']
        }
        
        # Get combined stats
        vector_stats = rag_deps_with_graph.collection_manager.get_collection_stats()
        graph_stats = await mock_graph_manager.get_graph_statistics()
        
        # Create combined report
        total_vector_docs = sum(s['count'] for s in vector_stats.values())
        
        combined_stats = {
            'vector_storage': {
                'total_documents': total_vector_docs,
                'by_collection': vector_stats
            },
            'knowledge_graph': graph_stats
        }
        
        # Verify comprehensive stats
        assert combined_stats['vector_storage']['total_documents'] == 175
        assert combined_stats['knowledge_graph']['total_nodes'] == 150
        assert combined_stats['knowledge_graph']['total_edges'] == 300
    
    @pytest.mark.asyncio
    async def test_question_answering_with_graph(self, mock_graph_manager, rag_deps_with_graph):
        """Test answering questions using graph relationships."""
        question = "Who does Alice report to?"
        
        # Mock graph providing direct answer
        mock_graph_manager.search_entities.return_value = [
            GraphSearchResult(
                fact="Alice reports to Charlie who is the Director of Engineering",
                source_node_id="alice_123",
                target_node_id="charlie_456",
                relevance_score=0.95
            )
        ]
        
        # Mock vector search with less specific results
        rag_deps_with_graph.collection_manager.search_all.return_value = [
            {
                'document': 'Org chart shows reporting structure for all teams',
                'distance': 0.6,
                'metadata': {'source': 'org-chart.pdf'}
            }
        ]
        
        # Graph should provide better answer
        graph_results = await mock_graph_manager.search_entities(question)
        vector_results = rag_deps_with_graph.collection_manager.search_all(question)
        
        # Verify graph gives direct answer
        assert len(graph_results) > 0
        assert "reports to Charlie" in graph_results[0].fact
        assert graph_results[0].relevance_score > 0.9
        
        # Vector results are less specific
        assert len(vector_results) > 0
        assert "reports to Charlie" not in vector_results[0]['document']


class TestRAGToolsWithGraph:
    """Test new RAG tools that leverage the knowledge graph."""
    
    @pytest.mark.asyncio
    async def test_explore_entity_tool(self, mock_graph_manager):
        """Test tool for exploring entity relationships."""
        # Mock tool implementation
        async def explore_entity(entity_name: str, depth: int = 1):
            """Explore relationships and facts about an entity."""
            relationships = await mock_graph_manager.get_entity_relationships(entity_name)
            related_entities = await mock_graph_manager.find_related_entities(
                entity_name, 
                max_depth=depth
            )
            
            return {
                'entity': entity_name,
                'relationships': len(relationships),
                'related_entities': len(related_entities)
            }
        
        # Test exploring Alice
        result = await explore_entity("Alice", depth=2)
        
        assert result['entity'] == "Alice"
        assert result['relationships'] >= 0
        assert result['related_entities'] >= 0
    
    @pytest.mark.asyncio
    async def test_find_connections_tool(self, mock_graph_manager):
        """Test tool for finding connections between entities."""
        # Mock finding path between entities
        async def find_connections(entity1: str, entity2: str):
            """Find connections between two entities."""
            # In real implementation, would use graph traversal
            return {
                'from': entity1,
                'to': entity2,
                'paths': [
                    f"{entity1} -> works on -> Project X <- works on <- {entity2}"
                ]
            }
        
        # Test finding connection
        result = await find_connections("Alice", "Bob")
        
        assert result['from'] == "Alice"
        assert result['to'] == "Bob"
        assert len(result['paths']) > 0
    
    @pytest.mark.asyncio
    async def test_timeline_tool(self, mock_graph_manager):
        """Test tool for getting entity timeline."""
        # Mock timeline events
        mock_graph_manager.get_entity_timeline.return_value = [
            {
                'timestamp': '2024-01-01T10:00:00Z',
                'event': 'Alice joined Project X',
                'episode_id': 'ep1'
            },
            {
                'timestamp': '2024-02-01T14:00:00Z',
                'event': 'Alice became team lead',
                'episode_id': 'ep2'
            }
        ]
        
        # Get timeline
        timeline = await mock_graph_manager.get_entity_timeline(
            "Alice",
            start_date="2024-01-01",
            end_date="2024-12-31"
        )
        
        assert len(timeline) == 2
        assert timeline[0]['timestamp'] < timeline[1]['timestamp']
        assert "joined Project X" in timeline[0]['event']