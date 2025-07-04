#!/usr/bin/env python3
"""Test script to debug and improve 686C search results."""

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
setup_logger("test_686c", "INFO")


async def test_direct_search():
    """Test direct vector search for 686C."""
    log_info("=== Testing Direct Vector Search for '686C' ===\n")
    
    # Test with different collections
    collections = ["documents", "knowledge_base", "va_notes"]
    
    for collection in collections:
        log_info(f"\nSearching in collection: {collection}")
        try:
            vector_client = SupabaseVectorClient(collection)
            
            # Try different query variations
            queries = [
                "686C",
                "686C form",
                "BGS 686C",
                "686C-674",
                "what is 686C"
            ]
            
            for query in queries:
                log_info(f"\n  Query: '{query}'")
                results = vector_client.query([query], n_results=3)
                
                if results and results['documents'] and results['documents'][0]:
                    for i, doc in enumerate(results['documents'][0]):
                        score = 1 - results['distances'][0][i]
                        metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                        log_info(f"    Result {i+1} (score: {score:.3f}):")
                        log_info(f"      Source: {metadata.get('source', 'Unknown')}")
                        log_info(f"      Preview: {doc[:100]}...")
                else:
                    log_info("    No results found")
                    
        except Exception as e:
            log_error(f"Error searching collection {collection}: {str(e)}")


async def test_rag_agent_search():
    """Test RAG agent search with different strategies."""
    log_info("\n\n=== Testing RAG Agent Search ===\n")
    
    # Initialize RAG agent
    settings = get_settings()
    provider = OpenAIProvider(
        base_url=settings.base_url,
        api_key=settings.llm_api_key
    )
    model = OpenAIModel(settings.model_choice, provider=provider)
    rag_agent = CloudRAGAgent(model, use_cloud=True)
    
    # Test different search approaches
    search_queries = [
        "search all collections for: 686C",
        "search documents collection for: BGS 686C",
        "search va_notes collection for: 686C-674",
        "use hybrid search for: what is 686C form",
        "search for exact match: 686C"
    ]
    
    for query in search_queries:
        log_info(f"\nTesting: {query}")
        try:
            result = await rag_agent.run(query, deps=None)
            if result and hasattr(result, 'data'):
                log_info(f"Results preview: {str(result.data)[:300]}...")
            else:
                log_info("No results returned")
        except Exception as e:
            log_error(f"Error: {str(e)}")


async def check_actual_content():
    """Check if 686C content exists in the database."""
    log_info("\n\n=== Checking Database for '686C' Content ===\n")
    
    try:
        from src.storage.supabase_client import get_supabase_client
        client = get_supabase_client()
        
        # Search for documents containing 686C
        result = client.client.table("document_embeddings") \
            .select("document_id, content, metadata, collection_name") \
            .ilike("content", "%686C%") \
            .limit(10) \
            .execute()
        
        if result.data:
            log_info(f"Found {len(result.data)} documents containing '686C':")
            for doc in result.data:
                log_info(f"\n  Document: {doc['document_id']}")
                log_info(f"  Collection: {doc['collection_name']}")
                log_info(f"  Content preview: {doc['content'][:200]}...")
                
                # Check metadata
                import json
                try:
                    metadata = json.loads(doc['metadata']) if isinstance(doc['metadata'], str) else doc['metadata']
                    log_info(f"  Source: {metadata.get('source', 'Unknown')}")
                except:
                    pass
        else:
            log_info("No documents found containing '686C' in the database")
            
    except Exception as e:
        log_error(f"Database check failed: {str(e)}")


async def suggest_improvements():
    """Suggest improvements for better search results."""
    log_info("\n\n=== Suggestions for Better Search Results ===\n")
    
    log_info("1. Consider reindexing with enhanced metadata:")
    log_info("   - Add 'keywords' field to metadata during indexing")
    log_info("   - Extract form numbers (like 686C) as specific entities")
    log_info("   - Add document type classification")
    
    log_info("\n2. Query optimization strategies:")
    log_info("   - Use more specific queries: 'BGS 686C form documentation'")
    log_info("   - Search in specific collections where VA forms are stored")
    log_info("   - Use hybrid search with keyword emphasis")
    
    log_info("\n3. Consider creating a specialized search tool:")
    log_info("   - Form number search that looks for exact matches")
    log_info("   - Regex-based search for form patterns")
    log_info("   - Metadata filtering by document type")


async def main():
    """Run all tests."""
    await test_direct_search()
    await test_rag_agent_search()
    await check_actual_content()
    await suggest_improvements()


if __name__ == "__main__":
    asyncio.run(main())