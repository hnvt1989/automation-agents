"""Integration tests for GraphKnowledgeManager with ChromaDB."""
import pytest
import asyncio
from pathlib import Path
from typing import Dict, List, Any
import tempfile
import shutil
from datetime import datetime, timezone

from src.storage.chromadb_client import ChromaDBClient
from src.storage.collection_manager import CollectionManager
from src.storage.graph_knowledge_manager import GraphKnowledgeManager
from src.core.constants import COLLECTION_KNOWLEDGE


@pytest.mark.integration
class TestGraphChromaDBIntegration:
    """Test integration between GraphKnowledgeManager and ChromaDB."""
    
    @pytest.fixture
    def temp_persist_dir(self):
        """Create temporary directory for ChromaDB."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def neo4j_config(self):
        """Neo4j configuration for tests."""
        return {
            "uri": "bolt://localhost:7687",
            "user": "neo4j",
            "password": "test_password"
        }
    
    @pytest.fixture
    async def chromadb_client(self, temp_persist_dir):
        """Create ChromaDB client."""
        client = ChromaDBClient(
            persist_directory=temp_persist_dir,
            collection_name=COLLECTION_KNOWLEDGE
        )
        yield client
    
    @pytest.fixture
    async def collection_manager(self, chromadb_client):
        """Create CollectionManager."""
        return CollectionManager(chromadb_client)
    
    @pytest.fixture
    async def graph_manager(self, neo4j_config):
        """Create GraphKnowledgeManager."""
        # Skip if Neo4j is not available
        pytest.importorskip("graphiti_core")
        
        try:
            manager = GraphKnowledgeManager(
                neo4j_uri=neo4j_config["uri"],
                neo4j_user=neo4j_config["user"],
                neo4j_password=neo4j_config["password"]
            )
            await manager.initialize()
            yield manager
            await manager.close()
        except Exception as e:
            pytest.skip(f"Neo4j not available: {e}")
    
    @pytest.mark.asyncio
    async def test_index_and_graph_document(self, chromadb_client, collection_manager, graph_manager):
        """Test indexing a document in both ChromaDB and graph."""
        # Document content
        content = """
        Alice is the project manager for Project Apollo. She works closely with Bob,
        who is the lead developer. The project started in January 2024 and aims to
        build a next-generation AI assistant. Charlie from the data science team
        provides ML expertise.
        """
        
        file_path = Path("/docs/project-apollo.md")
        
        # Index in ChromaDB
        doc_ids = collection_manager.index_knowledge(
            file_path=file_path,
            content=content,
            category="project_documentation"
        )
        
        # Add to knowledge graph
        episode_id = await graph_manager.add_document_episode(
            content=content,
            metadata={
                "source": str(file_path),
                "category": "project_documentation",
                "chromadb_ids": doc_ids
            },
            name="Project Apollo Documentation"
        )
        
        # Verify ChromaDB indexing
        assert len(doc_ids) > 0
        
        # Search in ChromaDB
        chroma_results = chromadb_client.query(
            query_texts=["Project Apollo"],
            n_results=5
        )
        assert len(chroma_results['ids'][0]) > 0
        
        # Search in graph
        graph_results = await graph_manager.search_entities(
            query="Project Apollo",
            num_results=5
        )
        
        # Should find relationships
        assert any("Alice" in r.fact for r in graph_results)
        assert any("Project Apollo" in r.fact for r in graph_results)
    
    @pytest.mark.asyncio
    async def test_conversation_to_graph(self, collection_manager, graph_manager):
        """Test converting conversation to knowledge graph."""
        # Conversation data
        messages = [
            {
                "sender": "Alice",
                "content": "I've scheduled a meeting about Project Apollo for next Tuesday.",
                "timestamp": "2024-01-15T10:00:00Z"
            },
            {
                "sender": "Bob",
                "content": "Great! I'll prepare the technical roadmap. Should we invite Charlie?",
                "timestamp": "2024-01-15T10:02:00Z"
            },
            {
                "sender": "Alice",
                "content": "Yes, Charlie's ML expertise will be valuable for the AI components.",
                "timestamp": "2024-01-15T10:03:00Z"
            }
        ]
        
        # Index conversation in ChromaDB
        conv_ids = collection_manager.index_conversation(
            messages=messages,
            conversation_id="conv_apollo_planning",
            platform="slack"
        )
        
        # Add to graph
        episode_id = await graph_manager.add_conversation_episode(
            messages=messages,
            conversation_id="conv_apollo_planning",
            platform="slack",
            metadata={"chromadb_ids": conv_ids}
        )
        
        # Verify entities were extracted
        await asyncio.sleep(1)  # Allow async processing
        
        # Search for relationships
        alice_relationships = await graph_manager.get_entity_relationships("Alice")
        
        # Should find relationships with Project Apollo and scheduling
        assert len(alice_relationships) > 0
        assert any("meeting" in r.fact.lower() for r in alice_relationships)
    
    @pytest.mark.asyncio
    async def test_hybrid_search(self, chromadb_client, graph_manager):
        """Test hybrid search combining vector and graph results."""
        # Add test data
        documents = [
            {
                "content": "Alice leads the frontend team on Project Apollo.",
                "metadata": {"source": "team-structure.md"}
            },
            {
                "content": "Bob manages the backend infrastructure for Apollo.",
                "metadata": {"source": "tech-stack.md"}
            },
            {
                "content": "Project Zeus is led by David with Emma as tech lead.",
                "metadata": {"source": "project-zeus.md"}
            }
        ]
        
        # Index documents
        for doc in documents:
            # Add to ChromaDB
            chromadb_client.add_documents(
                documents=[doc["content"]],
                metadatas=[doc["metadata"]]
            )
            
            # Add to graph
            await graph_manager.add_document_episode(
                content=doc["content"],
                metadata=doc["metadata"],
                name=f"Doc: {doc['metadata']['source']}"
            )
        
        # Perform hybrid search
        query = "Who works on Apollo?"
        
        # Vector search (ChromaDB)
        vector_results = chromadb_client.query(
            query_texts=[query],
            n_results=5
        )
        
        # Graph search
        graph_results = await graph_manager.search_entities(
            query=query,
            num_results=5
        )
        
        # Combine and rank results
        hybrid_results = await graph_manager.hybrid_search(
            query=query,
            vector_results=vector_results,
            num_results=5
        )
        
        # Should prioritize Apollo-related results
        assert len(hybrid_results) > 0
        apollo_results = [r for r in hybrid_results if "Apollo" in r.get('content', '')]
        assert len(apollo_results) >= 2  # Alice and Bob documents
    
    @pytest.mark.asyncio
    async def test_entity_tracking_across_documents(self, collection_manager, graph_manager):
        """Test tracking entities across multiple documents."""
        # Multiple documents mentioning same entities
        documents = [
            {
                "path": "/docs/meeting-notes-01.md",
                "content": "Alice presented the Q1 roadmap for Project Apollo. Budget approved."
            },
            {
                "path": "/docs/standup-02.md", 
                "content": "Bob reported Apollo API development is on track. Alice reviewing."
            },
            {
                "path": "/docs/retrospective.md",
                "content": "Team retrospective: Apollo Phase 1 complete. Alice and Bob celebrating!"
            }
        ]
        
        # Index all documents
        for doc in documents:
            # ChromaDB indexing
            collection_manager.index_knowledge(
                file_path=Path(doc["path"]),
                content=doc["content"],
                category="meeting_notes"
            )
            
            # Graph indexing
            await graph_manager.add_document_episode(
                content=doc["content"],
                metadata={"source": doc["path"], "type": "meeting_notes"},
                name=f"Meeting: {Path(doc['path']).stem}"
            )
        
        # Find all Apollo-related entities
        apollo_entities = await graph_manager.find_related_entities(
            entity_name="Project Apollo",
            max_depth=2
        )
        
        # Should find Alice and Bob connected to Apollo
        entity_names = {e.name for e in apollo_entities}
        assert "Alice" in entity_names or any("Alice" in e.name for e in apollo_entities)
        assert "Bob" in entity_names or any("Bob" in e.name for e in apollo_entities)
    
    @pytest.mark.asyncio
    async def test_temporal_analysis(self, graph_manager):
        """Test temporal analysis of entity relationships."""
        # Add time-based episodes
        events = [
            {
                "content": "Project Apollo kickoff meeting with Alice as PM.",
                "timestamp": "2024-01-01T10:00:00Z"
            },
            {
                "content": "Bob joined Apollo team as lead developer.",
                "timestamp": "2024-01-15T09:00:00Z"
            },
            {
                "content": "Charlie added to Apollo for ML components.",
                "timestamp": "2024-02-01T14:00:00Z"
            }
        ]
        
        for event in events:
            await graph_manager.add_document_episode(
                content=event["content"],
                metadata={"timestamp": event["timestamp"]},
                name=f"Event: {event['timestamp'][:10]}",
                reference_time=datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
            )
        
        # Query relationships over time
        timeline = await graph_manager.get_entity_timeline(
            entity_name="Project Apollo",
            start_date="2024-01-01",
            end_date="2024-03-01"
        )
        
        # Should show progressive team building
        assert len(timeline) >= 3
        assert timeline[0].timestamp < timeline[-1].timestamp
    
    @pytest.mark.asyncio
    async def test_graph_statistics_with_data(self, graph_manager):
        """Test graph statistics after adding data."""
        # Add various entities and relationships
        test_episodes = [
            "Alice manages Project Apollo with Bob and Charlie.",
            "David leads Project Zeus with Emma as architect.",
            "Frank coordinates between Apollo and Zeus projects.",
            "Meeting scheduled: Apollo and Zeus integration planning."
        ]
        
        for i, content in enumerate(test_episodes):
            await graph_manager.add_document_episode(
                content=content,
                metadata={"doc_id": f"doc_{i}"},
                name=f"Episode {i}"
            )
        
        # Get statistics
        stats = await graph_manager.get_graph_statistics()
        
        # Verify graph has grown
        assert stats['total_nodes'] > 0
        assert stats['total_edges'] > 0
        assert len(stats['node_types']) > 0
        assert len(stats['edge_types']) > 0
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, chromadb_client, graph_manager):
        """Test error recovery in integrated system."""
        # Test with invalid content
        with pytest.raises(Exception):
            await graph_manager.add_document_episode(
                content=None,  # Invalid
                metadata={},
                name="Invalid"
            )
        
        # System should still be functional
        valid_content = "Recovery test: Alice works on Project Recovery."
        episode_id = await graph_manager.add_document_episode(
            content=valid_content,
            metadata={"test": "recovery"},
            name="Recovery Test"
        )
        
        assert episode_id is not None
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, collection_manager, graph_manager):
        """Test performance of batch processing documents."""
        import time
        
        # Generate test documents
        num_docs = 50
        documents = []
        for i in range(num_docs):
            documents.append({
                "content": f"Document {i}: Person{i} works on Project{i % 5} with Person{(i+1) % num_docs}.",
                "metadata": {"doc_id": f"batch_doc_{i}"}
            })
        
        # Measure indexing time
        start_time = time.time()
        
        # Batch process
        stats = await graph_manager.build_graph_from_documents(
            documents,
            batch_size=10
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify completion
        assert stats['total_documents'] == num_docs
        assert stats['episodes_created'] == num_docs
        
        # Performance check (should process at reasonable speed)
        docs_per_second = num_docs / processing_time
        print(f"Processed {docs_per_second:.2f} documents/second")
        
        # Get final graph size
        graph_stats = await graph_manager.get_graph_statistics()
        print(f"Graph size: {graph_stats['total_nodes']} nodes, {graph_stats['total_edges']} edges")