"""Integration tests for contextual RAG functionality."""
import pytest
import asyncio
from typing import List, Dict, Any
from pathlib import Path
import tempfile

from src.storage.chromadb_client import ChromaDBClient
from src.storage.collection_manager import CollectionManager
from src.agents.rag import RAGAgent
from src.core.config import get_settings
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider


@pytest.fixture
def temp_chromadb():
    """Create a temporary ChromaDB instance for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        client = ChromaDBClient(
            persist_directory=Path(tmpdir),
            collection_name="test_contextual"
        )
        yield client
        

@pytest.fixture
def collection_manager(temp_chromadb):
    """Create a collection manager with temporary ChromaDB."""
    return CollectionManager(temp_chromadb)


@pytest.fixture
def mock_llm_model():
    """Create a mock LLM model for testing."""
    settings = get_settings()
    provider = OpenAIProvider(
        base_url=settings.base_url,
        api_key=settings.llm_api_key or "test-key"
    )
    return OpenAIModel('gpt-4o-mini', provider=provider)


class TestContextualRAGEndToEnd:
    """End-to-end tests for contextual RAG."""
    
    @pytest.mark.integration
    def test_index_and_retrieve_with_context(self, collection_manager):
        """Test indexing documents with context and retrieving them."""
        # Index documents with context
        documents = [
            {
                "content": "The DataFrame.merge() function performs database-style joins.",
                "metadata": {
                    "source": "pandas_docs",
                    "section": "Merging and Joining",
                    "version": "2.0"
                }
            },
            {
                "content": "Use pd.concat() to concatenate pandas objects along an axis.",
                "metadata": {
                    "source": "pandas_tutorial",
                    "section": "Data Manipulation",
                    "level": "beginner"
                }
            },
            {
                "content": "SQL-style joins are supported: inner, left, right, and outer.",
                "metadata": {
                    "source": "pandas_docs", 
                    "section": "Merging and Joining",
                    "version": "2.0"
                }
            }
        ]
        
        # Index with contextual information
        for doc in documents:
            collection_manager.index_with_context(
                content=doc["content"],
                metadata=doc["metadata"],
                collection_name="test_contextual",
                context_template="This information is from {source}, section '{section}': {content}"
            )
        
        # Search with context-aware query
        results = collection_manager.contextual_search(
            query="How to join dataframes in pandas?",
            collection_name="test_contextual",
            n_results=3
        )
        
        # Verify results include contextual information
        assert len(results) > 0
        assert any("pandas_docs" in str(r.get("content", "")) for r in results)
        assert any("Merging and Joining" in str(r.get("content", "")) for r in results)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_contextual_rag_conversation_flow(self, collection_manager):
        """Test contextual RAG with conversation history."""
        # Index a conversation about API integration
        conversation = [
            {"role": "user", "content": "How do I integrate with the GitHub API?"},
            {"role": "assistant", "content": "To integrate with GitHub API, first create a personal access token in your GitHub settings."},
            {"role": "user", "content": "What permissions do I need?"},
            {"role": "assistant", "content": "For basic repository access, you need 'repo' scope. For organization data, add 'read:org'."},
            {"role": "user", "content": "How do I authenticate requests?"},
            {"role": "assistant", "content": "Include your token in the Authorization header: 'Authorization: token YOUR_TOKEN'"}
        ]
        
        # Index conversation with context
        collection_manager.index_conversation_with_context(
            messages=conversation,
            conversation_id="github-api-help",
            platform="support_chat",
            topic_summary="GitHub API integration and authentication"
        )
        
        # Search for related information
        results = await collection_manager.contextual_search(
            query="GitHub API authentication token",
            collection_name="conversations",
            n_results=2
        )
        
        # Verify conversation context is preserved
        assert len(results) > 0
        assert any("GitHub API" in str(r.get("content", "")) for r in results)
        assert any("Authorization header" in str(r.get("content", "")) for r in results)
    
    @pytest.mark.integration
    def test_contextual_chunking_large_document(self, collection_manager):
        """Test contextual chunking of large documents."""
        # Create a large document
        large_doc = """
        # Complete Guide to Python Web Development
        
        ## Chapter 1: Introduction to Web Frameworks
        Python offers several web frameworks. Django is a full-featured framework
        that follows the model-view-template pattern. Flask is a micro-framework
        that provides more flexibility.
        
        ## Chapter 2: Setting Up Django
        To install Django, use pip: `pip install django`. Create a new project
        with `django-admin startproject myproject`. The project structure includes
        settings.py for configuration and urls.py for routing.
        
        ## Chapter 3: Flask Basics  
        Flask applications start with creating an app instance. Use decorators
        to define routes. Templates are stored in a templates folder by default.
        Flask uses Jinja2 for templating.
        
        ## Chapter 4: Database Integration
        Both Django and Flask support various databases. Django has a built-in ORM.
        Flask typically uses SQLAlchemy. Configure database connections in settings.
        
        ## Chapter 5: Authentication
        Implement user authentication with sessions and cookies. Django provides
        django.contrib.auth. Flask-Login is popular for Flask applications.
        """ * 3  # Make it larger
        
        # Index with contextual chunking
        chunk_ids = collection_manager.index_large_document_with_context(
            content=large_doc,
            metadata={
                "title": "Python Web Development Guide",
                "type": "tutorial",
                "topics": ["django", "flask", "web development"]
            },
            collection_name="test_contextual",
            chunk_size=500,
            chunk_overlap=100
        )
        
        # Verify chunks were created with context
        assert len(chunk_ids) > 5  # Should create multiple chunks
        
        # Search for specific information
        django_results = collection_manager.contextual_search(
            query="How to create a Django project?",
            collection_name="test_contextual",
            n_results=2
        )
        
        flask_results = collection_manager.contextual_search(
            query="Flask templating system",
            collection_name="test_contextual", 
            n_results=2
        )
        
        # Verify relevant chunks are retrieved
        assert any("django-admin startproject" in str(r.get("content", "")).lower() for r in django_results)
        assert any("jinja2" in str(r.get("content", "")).lower() for r in flask_results)
    
    @pytest.mark.integration
    def test_hybrid_contextual_search(self, collection_manager):
        """Test hybrid search combining embeddings and BM25."""
        # Index technical documentation
        docs = [
            {
                "content": "The async/await syntax in Python allows for asynchronous programming.",
                "metadata": {"topic": "python", "subtopic": "concurrency"}
            },
            {
                "content": "asyncio.create_task() schedules coroutines concurrently.",
                "metadata": {"topic": "python", "subtopic": "asyncio"}
            },
            {
                "content": "Use await to pause execution until an async operation completes.",
                "metadata": {"topic": "python", "subtopic": "concurrency"}
            }
        ]
        
        for doc in docs:
            collection_manager.index_with_context(
                content=doc["content"],
                metadata=doc["metadata"],
                collection_name="test_contextual",
                enable_bm25=True
            )
        
        # Perform hybrid search
        results = collection_manager.hybrid_contextual_search(
            query="Python async await programming",
            collection_name="test_contextual",
            n_results=3,
            embedding_weight=0.7,
            bm25_weight=0.3
        )
        
        # Verify results combine both search methods
        assert len(results) > 0
        assert all("async" in r.get("content", "").lower() or 
                  "await" in r.get("content", "").lower() for r in results)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_rag_agent_contextual_integration(self, mock_llm_model, collection_manager):
        """Test RAG agent with contextual retrieval integration."""
        # Create RAG agent with contextual support
        from src.agents.rag import RAGAgent
        
        # Mock the dependencies injection
        rag_agent = RAGAgent(mock_llm_model)
        rag_agent.collection_manager = collection_manager
        
        # Index some test data
        test_docs = [
            {
                "content": "Redis is an in-memory data structure store used as a cache.",
                "metadata": {"source": "redis_docs", "topic": "introduction"}
            },
            {
                "content": "Set Redis keys with EXPIRE to implement cache expiration.",
                "metadata": {"source": "redis_tutorial", "topic": "caching"}
            }
        ]
        
        for doc in test_docs:
            collection_manager.index_with_context(
                content=doc["content"],
                metadata=doc["metadata"],
                collection_name="knowledge_base"
            )
        
        # Use RAG agent with contextual search
        response = await rag_agent.run(
            "search knowledge base for: Redis cache expiration",
            use_contextual=True
        )
        
        # Verify contextual information in response
        assert response.data is not None
        result_text = str(response.data)
        assert "redis" in result_text.lower()
        assert any(keyword in result_text.lower() 
                  for keyword in ["expire", "expiration", "cache"])


class TestContextualPerformance:
    """Test performance aspects of contextual RAG."""
    
    @pytest.mark.integration
    def test_contextual_indexing_performance(self, collection_manager):
        """Test performance of contextual indexing."""
        import time
        
        # Generate test documents
        num_docs = 100
        documents = [
            {
                "content": f"Document {i}: This is test content about topic {i % 10}.",
                "metadata": {"doc_id": i, "topic": f"topic_{i % 10}"}
            }
            for i in range(num_docs)
        ]
        
        # Measure indexing time
        start_time = time.time()
        
        for doc in documents:
            collection_manager.index_with_context(
                content=doc["content"],
                metadata=doc["metadata"],
                collection_name="test_contextual",
                generate_context=False  # Use template instead of LLM
            )
        
        indexing_time = time.time() - start_time
        
        # Verify performance is reasonable
        assert indexing_time < 60  # Should complete within 60 seconds
        avg_time_per_doc = indexing_time / num_docs
        assert avg_time_per_doc < 1.0  # Less than 1 second per document
        
        # Measure search performance
        search_queries = [
            "topic 5 content",
            "document about topic 3",
            "test content topic 7"
        ]
        
        search_start = time.time()
        for query in search_queries:
            results = collection_manager.contextual_search(
                query=query,
                collection_name="test_contextual",
                n_results=5
            )
            assert len(results) > 0
        
        search_time = time.time() - search_start
        avg_search_time = search_time / len(search_queries)
        assert avg_search_time < 2.0  # Less than 2 seconds per search
    
    @pytest.mark.integration
    def test_context_caching(self, collection_manager):
        """Test caching of generated contexts."""
        # Enable context caching
        collection_manager.enable_context_cache(max_size=100)
        
        # Index same content multiple times
        content = "Python decorators are functions that modify other functions."
        metadata = {"source": "python_guide", "topic": "decorators"}
        
        # First indexing (generates context)
        import time
        start1 = time.time()
        collection_manager.index_with_context(
            content=content,
            metadata=metadata,
            collection_name="test_contextual",
            cache_context=True
        )
        time1 = time.time() - start1
        
        # Second indexing (should use cached context)
        start2 = time.time()
        collection_manager.index_with_context(
            content=content,
            metadata=metadata,
            collection_name="test_contextual",
            cache_context=True
        )
        time2 = time.time() - start2
        
        # Cached version should be faster
        assert time2 < time1 * 0.5  # At least 50% faster
        
        # Verify cache stats
        cache_stats = collection_manager.get_context_cache_stats()
        assert cache_stats["hits"] >= 1
        assert cache_stats["size"] >= 1