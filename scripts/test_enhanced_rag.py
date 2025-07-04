#!/usr/bin/env python3
"""Test script for enhanced RAG features."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.rag_cloud import CloudRAGAgent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from src.core.config import get_settings
from src.storage.supabase_vector import SupabaseVectorClient
from src.utils.logging import setup_logger, log_info, log_error

# Setup logging
setup_logger("test_enhanced_rag", "DEBUG")


async def test_contextual_indexing():
    """Test contextual document indexing."""
    log_info("=== Testing Contextual Indexing ===")
    
    # Initialize vector client
    vector_client = SupabaseVectorClient("test_contextual", enable_contextual=True)
    
    # Sample document
    test_content = """
    # Introduction to RAG Systems
    
    Retrieval-Augmented Generation (RAG) combines the power of large language models 
    with external knowledge retrieval. This approach allows AI systems to access 
    up-to-date information and provide more accurate responses.
    
    ## Key Components
    
    1. **Document Chunking**: Breaking down large documents into manageable pieces
    2. **Embedding Generation**: Converting text into vector representations
    3. **Vector Search**: Finding relevant chunks based on similarity
    4. **Response Generation**: Using retrieved context to generate answers
    
    ## Advanced Techniques
    
    Modern RAG systems employ several advanced techniques:
    - Hybrid search combining dense and sparse retrieval
    - Contextual chunking for better retrieval accuracy
    - Reranking to improve result relevance
    - Query expansion for comprehensive search
    """
    
    # Context information
    context_info = {
        "source_type": "knowledge_base",
        "filename": "rag_introduction.md",
        "category": "documentation",
        "document_type": "markdown",
        "document_summary": "Introduction to RAG systems and their components"
    }
    
    try:
        # Index with contextual chunking
        doc_ids = vector_client.add_documents_with_context(
            content=test_content,
            context_info=context_info,
            use_llm_context=False  # Use template-based context for testing
        )
        
        log_info(f"✓ Successfully indexed {len(doc_ids)} contextual chunks")
        return True
    except Exception as e:
        log_error(f"✗ Contextual indexing failed: {str(e)}")
        return False


async def test_hybrid_search():
    """Test hybrid search functionality."""
    log_info("=== Testing Hybrid Search ===")
    
    # Initialize RAG agent
    settings = get_settings()
    provider = OpenAIProvider(
        base_url=settings.base_url,
        api_key=settings.llm_api_key
    )
    model = OpenAIModel(settings.model_choice, provider=provider)
    rag_agent = CloudRAGAgent(model, use_cloud=True)
    
    # Test queries
    test_queries = [
        "What are the key components of RAG systems?",
        "How does contextual chunking improve retrieval?",
        "hybrid search dense sparse retrieval"  # Keyword-focused query
    ]
    
    results = []
    for query in test_queries:
        log_info(f"\nTesting query: '{query}'")
        
        try:
            # Run hybrid search
            result = await rag_agent.run(
                f"use hybrid search for: {query}",
                deps=None
            )
            
            if result and hasattr(result, 'data'):
                log_info(f"✓ Hybrid search returned results")
                results.append(True)
            else:
                log_error(f"✗ No results from hybrid search")
                results.append(False)
                
        except Exception as e:
            log_error(f"✗ Hybrid search failed: {str(e)}")
            results.append(False)
    
    return all(results)


async def test_reranking():
    """Test search with reranking."""
    log_info("=== Testing Search with Reranking ===")
    
    # Initialize vector client
    vector_client = SupabaseVectorClient("test_reranking")
    
    # Add some test documents
    test_docs = [
        {
            "content": "Python is a versatile programming language used for web development, data science, and automation.",
            "metadata": {"source": "python_intro.txt", "topic": "programming", "created_at": "2024-01-01T00:00:00Z"}
        },
        {
            "content": "Machine learning with Python involves libraries like scikit-learn, TensorFlow, and PyTorch.",
            "metadata": {"source": "ml_guide.txt", "topic": "machine learning", "is_verified": True, "created_at": "2025-01-01T00:00:00Z"}
        },
        {
            "content": "Web frameworks in Python include Django, Flask, and FastAPI for building applications.",
            "metadata": {"source": "web_dev.txt", "topic": "web development", "created_at": "2023-01-01T00:00:00Z"}
        }
    ]
    
    # Index documents
    for doc in test_docs:
        vector_client.add_documents(
            [doc["content"]],
            metadatas=[doc["metadata"]]
        )
    
    # Test reranking
    from src.storage.reranker import ResultReranker
    reranker = ResultReranker(use_cross_encoder=False, use_llm_rerank=False)
    
    query = "Python for machine learning"
    
    try:
        # Get search results
        results = vector_client.query([query], n_results=3)
        
        # Prepare for reranking
        search_results = []
        for i, doc in enumerate(results['documents'][0]):
            search_results.append({
                'content': doc,
                'metadata': results['metadatas'][0][i],
                'score': 1 - results['distances'][0][i]
            })
        
        # Rerank results
        reranked = await reranker.rerank_results(
            query=query,
            results=search_results,
            top_k=3
        )
        
        log_info(f"✓ Reranking completed. Top result score: {reranked[0].combined_score:.3f}")
        
        # Check if ML document is ranked higher
        ml_doc_rank = None
        for i, result in enumerate(reranked):
            if "machine learning" in result.metadata.get("topic", ""):
                ml_doc_rank = i
                break
        
        if ml_doc_rank == 0:
            log_info("✓ Reranking correctly prioritized ML document")
            return True
        else:
            log_error(f"✗ ML document ranked at position {ml_doc_rank + 1}")
            return False
            
    except Exception as e:
        log_error(f"✗ Reranking test failed: {str(e)}")
        return False


async def test_end_to_end():
    """Test complete enhanced RAG workflow."""
    log_info("=== Testing End-to-End Enhanced RAG ===")
    
    # Initialize RAG agent
    settings = get_settings()
    provider = OpenAIProvider(
        base_url=settings.base_url,
        api_key=settings.llm_api_key
    )
    model = OpenAIModel(settings.model_choice, provider=provider)
    rag_agent = CloudRAGAgent(model, use_cloud=True)
    
    # Add a contextual document
    test_content = """
    ## Best Practices for RAG Implementation
    
    When implementing a RAG system, consider these best practices:
    
    1. **Chunk Size Optimization**: Choose chunk sizes that balance context and precision
    2. **Metadata Enrichment**: Add relevant metadata to improve filtering
    3. **Query Understanding**: Analyze user queries to determine search strategy
    4. **Result Diversity**: Ensure diverse perspectives in retrieved documents
    5. **Performance Monitoring**: Track retrieval quality and latency
    
    Remember that RAG quality depends heavily on the quality of your indexed content.
    """
    
    context_info = {
        "source_type": "knowledge_base",
        "filename": "rag_best_practices.md",
        "category": "guide",
        "is_verified": True
    }
    
    try:
        # Add document with context
        result = await rag_agent.run(
            f"add this document with contextual chunking to knowledge_base collection: {test_content}",
            deps=None
        )
        log_info("✓ Document added with contextual chunking")
        
        # Wait a moment for indexing
        await asyncio.sleep(2)
        
        # First, let's verify the document was added by doing a simple search
        verify_result = await rag_agent.run(
            "search knowledge_base collection for: best practices",
            deps=None
        )
        
        # Check if verification found anything
        if verify_result and hasattr(verify_result, 'data'):
            log_info(f"✓ Document found in knowledge_base collection")
        else:
            log_warning("Document not found in verification search")
        
        # Test simple search first to ensure we can find the document
        query = "best practices RAG implementation"
        result = await rag_agent.run(
            f"search knowledge_base collection for: {query}",
            deps=None
        )
        
        if result and hasattr(result, 'data'):
            result_text = str(result.data)
            log_info(f"Hybrid search result preview: {result_text[:200]}...")
            
            # Check if we found the document we added
            if "best practices" in result_text.lower() and "rag" in result_text.lower():
                log_info("✓ End-to-end test passed - found relevant results")
                return True
            else:
                log_error(f"✗ Results don't contain expected content. Result: {result_text[:500]}")
                return False
        else:
            log_error("✗ No results returned")
            return False
            
    except Exception as e:
        log_error(f"✗ End-to-end test failed: {str(e)}")
        return False


async def main():
    """Run all tests."""
    log_info("Starting Enhanced RAG Tests\n")
    
    tests = [
        ("Contextual Indexing", test_contextual_indexing),
        ("Hybrid Search", test_hybrid_search),
        ("Reranking", test_reranking),
        ("End-to-End", test_end_to_end)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
            await asyncio.sleep(1)  # Brief pause between tests
        except Exception as e:
            log_error(f"Test '{test_name}' crashed: {str(e)}")
            results[test_name] = False
    
    # Summary
    log_info("\n=== Test Summary ===")
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        log_info(f"{test_name}: {status}")
    
    log_info(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    # Run tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)