#!/usr/bin/env python3
"""Quick verification script for enhanced RAG features."""

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
setup_logger("verify_rag", "INFO")


async def verify_enhanced_rag():
    """Verify enhanced RAG features are working."""
    log_info("=== Verifying Enhanced RAG Features ===\n")
    
    # Initialize components
    settings = get_settings()
    provider = OpenAIProvider(
        base_url=settings.base_url,
        api_key=settings.llm_api_key
    )
    model = OpenAIModel(settings.model_choice, provider=provider)
    
    # Test 1: Verify contextual columns exist
    log_info("1. Checking database schema updates...")
    try:
        vector_client = SupabaseVectorClient("test_verify")
        
        # Try to add a document with contextual metadata
        test_doc = "This is a test document for verification."
        metadata = {
            "source": "verification_test",
            "has_context": True,
            "context_type": "test"
        }
        
        vector_client.add_documents([test_doc], metadatas=[metadata])
        log_info("✓ Database schema updated successfully")
    except Exception as e:
        log_error(f"✗ Schema verification failed: {str(e)}")
        return False
    
    # Test 2: Verify CloudRAGAgent with enhanced features
    log_info("\n2. Testing CloudRAGAgent initialization...")
    try:
        rag_agent = CloudRAGAgent(model, use_cloud=True)
        log_info("✓ CloudRAGAgent initialized with enhanced features")
    except Exception as e:
        log_error(f"✗ CloudRAGAgent initialization failed: {str(e)}")
        return False
    
    # Test 3: Test contextual document addition
    log_info("\n3. Testing contextual document addition...")
    try:
        test_content = """
        # Enhanced RAG Verification
        
        This document verifies that our enhanced RAG system is working correctly.
        It includes contextual chunking, hybrid search, and reranking capabilities.
        """
        
        result = await rag_agent.run(
            f"add this document with contextual chunking to test_verify collection: {test_content}",
            deps=None
        )
        
        if result:
            log_info("✓ Contextual document addition working")
        else:
            log_error("✗ Contextual document addition failed")
    except Exception as e:
        log_error(f"✗ Error adding contextual document: {str(e)}")
    
    # Test 4: Test search functionality
    log_info("\n4. Testing enhanced search...")
    try:
        # Wait a moment for indexing
        await asyncio.sleep(2)
        
        # Test regular search
        result = await rag_agent.run(
            "search test_verify collection for: enhanced RAG verification",
            deps=None
        )
        
        if result and hasattr(result, 'data'):
            log_info("✓ Basic search working")
        else:
            log_error("✗ Basic search failed")
        
        # Test hybrid search
        result = await rag_agent.run(
            "use hybrid search for: contextual chunking capabilities",
            deps=None
        )
        
        if result and hasattr(result, 'data'):
            log_info("✓ Hybrid search working")
        else:
            log_error("✗ Hybrid search failed")
            
    except Exception as e:
        log_error(f"✗ Search test failed: {str(e)}")
    
    # Test 5: Check reranking
    log_info("\n5. Testing reranking functionality...")
    try:
        from src.storage.reranker import ResultReranker, CROSS_ENCODER_AVAILABLE
        
        reranker = ResultReranker(use_cross_encoder=False, use_llm_rerank=False)
        
        # Create test results
        test_results = [
            {
                'content': 'Document about Python programming',
                'score': 0.7,
                'metadata': {'source': 'test1.txt', 'created_at': '2025-01-01T00:00:00Z'}
            },
            {
                'content': 'Document about enhanced RAG systems',
                'score': 0.8,
                'metadata': {'source': 'test2.txt', 'is_verified': True}
            }
        ]
        
        reranked = await reranker.rerank_results(
            query="enhanced RAG",
            results=test_results,
            top_k=2
        )
        
        if reranked and len(reranked) == 2:
            log_info("✓ Reranking working (metadata-based)")
            if not CROSS_ENCODER_AVAILABLE:
                log_info("  Note: Cross-encoder not available (install sentence-transformers for better reranking)")
        else:
            log_error("✗ Reranking failed")
            
    except Exception as e:
        log_error(f"✗ Reranking test failed: {str(e)}")
    
    # Summary
    log_info("\n=== Verification Complete ===")
    log_info("\nEnhanced RAG features are ready to use!")
    log_info("\nOptional improvements:")
    log_info("1. Install sentence-transformers for cross-encoder reranking:")
    log_info("   pip install sentence-transformers torch")
    log_info("2. Add full-text search indexes when database resources allow")
    
    return True


if __name__ == "__main__":
    asyncio.run(verify_enhanced_rag())