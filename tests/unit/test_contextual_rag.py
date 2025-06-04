"""Unit tests for contextual RAG functionality."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from src.storage.chromadb_client import ChromaDBClient
from src.storage.collection_manager import CollectionManager
from src.utils.logging import log_info


class TestContextualChunking:
    """Test contextual chunking functionality."""
    
    def test_chunk_with_context_website(self):
        """Test adding context to website chunks."""
        client = Mock(spec=ChromaDBClient)
        manager = CollectionManager(client)
        
        # Test data
        url = "https://example.com/docs/api"
        title = "API Documentation"
        content = """
        # Introduction
        This is our API documentation.
        
        ## Authentication
        All API requests require authentication using API keys.
        
        ## Rate Limits
        The API has a rate limit of 100 requests per minute.
        
        ## Endpoints
        ### GET /users
        Returns a list of users.
        
        ### POST /users
        Creates a new user.
        """
        
        # Expected behavior: chunks should have contextual information prepended
        context_info = {
            "source_type": "website",
            "url": url,
            "title": title,
            "document_type": "API documentation"
        }
        
        # Use the contextual chunker directly
        if manager.contextual_chunker:
            chunks = manager.contextual_chunker.create_contextual_chunks(
                content=content,
                chunk_size=200,
                chunk_overlap=50,
                context_info=context_info,
                use_llm_context=False
            )
        else:
            pytest.skip("Contextual chunker not available")
        
        # Verify chunks have context
        assert len(chunks) > 0
        for chunk in chunks:
            assert "This chunk is from" in chunk.contextual_text
            assert url in chunk.contextual_text
            assert title in chunk.contextual_text
            assert chunk.original_text != chunk.contextual_text
    
    def test_chunk_with_context_conversation(self):
        """Test adding context to conversation chunks."""
        client = Mock(spec=ChromaDBClient)
        client.get_collection_chunk_config = Mock(return_value=(1000, 200))
        client.add_to_collection = Mock()
        manager = CollectionManager(client)
        
        # Test conversation data
        messages = [
            {"role": "user", "content": "How do I integrate with GitHub?"},
            {"role": "assistant", "content": "To integrate with GitHub, you need to..."},
            {"role": "user", "content": "What about authentication?"},
            {"role": "assistant", "content": "For authentication, use OAuth2..."}
        ]
        
        # Use index_conversation_with_context method
        ids = manager.index_conversation_with_context(
            messages=messages,
            conversation_id="conv-123",
            platform="slack",
            topic_summary="GitHub integration discussion"
        )
        
        # Verify conversation was indexed
        assert len(ids) > 0
    
    def test_chunk_with_context_knowledge_base(self):
        """Test adding context to knowledge base chunks."""
        client = Mock(spec=ChromaDBClient)
        client.get_collection_chunk_config = Mock(return_value=(1000, 200))
        client.add_to_collection = Mock()
        manager = CollectionManager(client)
        
        # Test knowledge base document
        content = """
        # Python Best Practices
        
        ## Code Style
        Follow PEP 8 for consistent code style.
        
        ## Testing
        Write unit tests for all functions.
        Use pytest as the testing framework.
        """
        
        # Use index_with_context method
        ids = manager.index_with_context(
            content=content,
            metadata={
                "source_type": "knowledge_base",
                "filename": "python_best_practices.md",
                "category": "development",
                "document_summary": "Guidelines for Python development including code style and testing practices"
            },
            collection_name="knowledge_base"
        )
        
        # Verify knowledge base was indexed
        assert len(ids) > 0


class TestContextualRetrieval:
    """Test contextual retrieval functionality."""
    
    @pytest.mark.asyncio
    async def test_contextual_search_ranking(self):
        """Test that contextual chunks improve search ranking."""
        client = Mock(spec=ChromaDBClient)
        manager = CollectionManager(client)
        
        # Mock query results with contextual and non-contextual chunks
        mock_results = {
            'ids': [['ctx-1', 'regular-1', 'ctx-2']],
            'documents': [[
                "This chunk is from API documentation about authentication. Use OAuth2 for secure authentication.",
                "Use OAuth2 for authentication.",
                "This chunk is from a tutorial on GitHub integration. Authentication is handled via OAuth2."
            ]],
            'distances': [[0.2, 0.3, 0.25]],
            'metadatas': [[
                {'has_context': True, 'source': 'api_docs'},
                {'has_context': False, 'source': 'unknown'},
                {'has_context': True, 'source': 'tutorial'}
            ]]
        }
        
        # Mock get_collection method first
        mock_collection = Mock()
        mock_collection.query = Mock(return_value=mock_results)
        client.get_collection = Mock(return_value=mock_collection)
        
        # Search with contextual retrieval (synchronous method)
        results = manager.contextual_search(
            query="How to authenticate with OAuth2?",
            collection_name="knowledge_base",
            n_results=3
        )
        
        # Verify contextual chunks are ranked higher
        assert len(results) == 3
        assert results[0]['metadata']['has_context'] is True
        assert results[0]['id'] == 'ctx-1'
    
    @pytest.mark.asyncio
    async def test_hybrid_contextual_search(self):
        """Test hybrid search with contextual embeddings and BM25."""
        client = Mock(spec=ChromaDBClient)
        manager = CollectionManager(client)
        
        # Mock both embedding and BM25 results
        embedding_results = {
            'ids': [['emb-1', 'emb-2']],
            'documents': [["Contextual chunk 1", "Contextual chunk 2"]],
            'distances': [[0.1, 0.2]]
        }
        
        bm25_results = [
            {'id': 'bm25-1', 'text': 'BM25 result 1', 'score': 5.2},
            {'id': 'emb-1', 'text': 'Contextual chunk 1', 'score': 4.8}
        ]
        
        # Mock methods for hybrid search
        manager.contextual_search = Mock(return_value=[
            {'id': 'emb-1', 'content': 'Contextual chunk 1', 'score': 0.9, 'metadata': {}},
            {'id': 'emb-2', 'content': 'Contextual chunk 2', 'score': 0.8, 'metadata': {}}
        ])
        manager._bm25_search = Mock(return_value=bm25_results)
        
        # Perform hybrid search
        results = await manager.hybrid_contextual_search(
            query="test query",
            collection_name="websites",
            n_results=3
        )
        
        # Verify results are properly merged and ranked
        assert len(results) > 0
        assert results[0]['id'] in ['emb-1', 'bm25-1']  # Should be highest scoring
    
    def test_context_generation_prompt(self):
        """Test context generation for chunks."""
        client = Mock(spec=ChromaDBClient)
        manager = CollectionManager(client)
        
        # Test document
        document = """
        The company reported Q3 earnings of $500M.
        This represents a 15% increase YoY.
        """
        
        # Test contextual chunker prompt creation
        if manager.contextual_chunker:
            context_prompt = manager.contextual_chunker._create_llm_prompt(
                chunk_text=document,
                context_info={
                    "title": "ACME Corp Q3 2023 Earnings Report",
                    "source": "SEC filing",
                    "date": "2023-10-15",
                    "previous_context": "Q2 earnings were $435M"
                },
                chunk_index=0,
                total_chunks=1
            )
            
            # Verify prompt includes necessary context
            assert "ACME Corp" in context_prompt
            assert "Q3 2023" in context_prompt
            assert "SEC filing" in context_prompt
        else:
            pytest.skip("Contextual chunker not available")


class TestContextualIndexing:
    """Test contextual indexing functionality."""
    
    def test_index_with_context_generation(self):
        """Test indexing documents with automatic context generation."""
        client = Mock(spec=ChromaDBClient)
        manager = CollectionManager(client)
        
        # Mock client methods
        client.get_collection_chunk_config = Mock(return_value=(1000, 200))
        client.add_to_collection = Mock()
        
        # Test indexing
        content = "API keys must be included in the Authorization header."
        metadata = {
            "source": "api_docs",
            "section": "Authentication"
        }
        
        manager.index_with_context(
            content=content,
            metadata=metadata,
            collection_name="knowledge_base",
            generate_context=True
        )
        
        # Verify indexing was called
        client.add_to_collection.assert_called()
        
        # Check that documents were indexed
        call_args = client.add_to_collection.call_args
        indexed_docs = call_args[1]['documents']
        assert len(indexed_docs) > 0
    
    def test_batch_contextual_indexing(self):
        """Test batch indexing with context."""
        client = Mock(spec=ChromaDBClient)
        manager = CollectionManager(client)
        
        # Test batch of documents
        documents = [
            {"content": "Python is great for data science.", "metadata": {"topic": "python"}},
            {"content": "JavaScript powers the web.", "metadata": {"topic": "javascript"}},
            {"content": "Rust provides memory safety.", "metadata": {"topic": "rust"}}
        ]
        
        # Mock client methods
        client.get_collection_chunk_config = Mock(return_value=(1000, 200))
        client.add_to_collection = Mock()
        
        # Batch index
        ids = manager.batch_index_with_context(
            documents=documents,
            collection_name="knowledge_base",
            shared_context="Programming languages comparison guide"
        )
        
        # Verify all documents were processed
        assert len(ids) == 3
    
    def test_contextual_reindexing(self):
        """Test reindexing existing documents with context."""
        client = Mock(spec=ChromaDBClient)
        manager = CollectionManager(client)
        
        # Mock existing documents without context
        existing_docs = {
            'ids': ['doc-1', 'doc-2'],
            'documents': ['Raw content 1', 'Raw content 2'],
            'metadatas': [{'source': 'file1'}, {'source': 'file2'}]
        }
        
        mock_collection = Mock()
        mock_collection.get = Mock(return_value=existing_docs)
        client.get_collection = Mock(return_value=mock_collection)
        client.update_documents = Mock()
        
        # Reindex with context
        manager.reindex_with_context(
            collection_name="knowledge_base",
            context_template="This document is from {source}: {content}"
        )
        
        # Verify documents were updated with context
        client.update_documents.assert_called()
        updated_docs = client.update_documents.call_args[1]['documents']
        assert "This document is from file1:" in updated_docs[0]
        assert "This document is from file2:" in updated_docs[1]


class TestContextualRAGIntegration:
    """Test integration of contextual RAG with existing system."""
    
    @pytest.mark.asyncio
    async def test_rag_agent_with_contextual_search(self):
        """Test RAG agent using contextual search."""
        from src.agents.rag import RAGAgent
        from pydantic_ai.models.test import TestModel
        
        # Use TestModel for testing
        test_model = TestModel()
        
        # Mock dependencies
        mock_chromadb = Mock(spec=ChromaDBClient)
        mock_collection_manager = Mock(spec=CollectionManager)
        mock_collection_manager.enable_contextual = True
        
        # Create RAG agent with mocked dependencies
        with patch('src.agents.rag.get_chromadb_client', return_value=mock_chromadb):
            with patch('src.agents.rag.CollectionManager', return_value=mock_collection_manager):
                agent = RAGAgent(test_model)
        
        # Mock contextual search results
        mock_results = [
            {
                "content": "This chunk is from API docs: Use API keys for authentication.",
                "metadata": {"source": "api_docs", "has_context": True},
                "score": 0.95
            }
        ]
        mock_collection_manager.contextual_search = AsyncMock(return_value=mock_results)
        
        # Test search using the public method
        result = await agent.contextual_search(
            query="How to authenticate?",
            use_contextual=True
        )
        
        # Verify contextual search was used
        mock_collection_manager.contextual_search.assert_called_once()
        assert "API docs" in str(result.data)
    
    def test_contextual_config_settings(self):
        """Test configuration settings for contextual RAG."""
        try:
            from src.core.config import get_settings
            
            settings = get_settings()
            
            # Verify contextual RAG settings exist
            assert hasattr(settings, 'enable_contextual_rag')
            assert hasattr(settings, 'contextual_chunk_size')
            assert hasattr(settings, 'context_generation_model')
            
            # Test default values
            assert settings.enable_contextual_rag is True
            assert settings.contextual_chunk_size > 0
            assert settings.context_generation_model in ['gpt-4o-mini', 'gpt-4o']
        except ValueError as e:
            # Skip if API key is not set
            if "LLM_API_KEY must be set" in str(e):
                pytest.skip("LLM_API_KEY not set for testing")