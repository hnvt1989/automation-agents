#!/usr/bin/env python3
"""Test specific search for BGS validation content."""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

async def test_specific_search():
    """Test searching for specific BGS validation content."""
    load_dotenv("local.env")
    
    print("Testing Specific Search for BGS Validation...")
    print("=" * 70)
    
    # First, let's check if dmt_release_process.md was indexed
    print("\n1. Checking if dmt_release_process.md is now indexed...")
    
    from src.storage.supabase_client import get_supabase_client
    client = get_supabase_client()
    
    # Check for the specific document
    result = client.client.table("document_embeddings") \
        .select("document_id, content, metadata") \
        .like("document_id", "%dmt_release%") \
        .execute()
    
    if result.data:
        print(f"✓ Found {len(result.data)} chunks from dmt_release_process.md")
        
        # Look for the specific content
        for chunk in result.data:
            if "initial BGS validation" in chunk['content'].lower():
                print(f"\n✓ FOUND IT! Chunk ID: {chunk['document_id']}")
                print(f"Content preview: {chunk['content'][:300]}...")
                print(f"Metadata: {chunk.get('metadata', {})}")
                break
    else:
        print("✗ dmt_release_process.md is still NOT indexed!")
        return
    
    # Now test vector search
    print("\n\n2. Testing vector search...")
    
    from src.storage.supabase_vector import SupabaseVectorClient
    vector_client = SupabaseVectorClient("documents")
    
    # Test different search queries
    queries = [
        "initial BGS validation",
        "BGS validation",
        "Phase 1 Initial BGS Validation",
        "dmt release process"
    ]
    
    for query in queries:
        print(f"\n\nSearching for: '{query}'")
        try:
            results = vector_client.query([query], n_results=5)
            
            if results and results.get('documents') and results['documents'][0]:
                print(f"✓ Found {len(results['documents'][0])} results")
                
                # Check if any result contains our target text
                found_target = False
                for i, doc in enumerate(results['documents'][0]):
                    if "initial BGS validation" in doc.lower():
                        print(f"\n  ✓ Result {i+1} contains 'initial BGS validation':")
                        print(f"    Content: {doc[:300]}...")
                        found_target = True
                        break
                
                if not found_target:
                    print("  ✗ None of the results contain 'initial BGS validation'")
                    # Show what was returned
                    for i, doc in enumerate(results['documents'][0][:2]):
                        print(f"\n  Result {i+1} preview: {doc[:200]}...")
            else:
                print("✗ No results found")
                
        except Exception as e:
            print(f"✗ Search error: {e}")
    
    # Test with RAG agent
    print("\n\n3. Testing with RAG agent...")
    try:
        from pydantic_ai.models.openai import OpenAIModel
        from pydantic_ai.providers.openai import OpenAIProvider
        from src.agents.rag_cloud import CloudRAGAgent
        from src.core.config import get_settings
        
        settings = get_settings()
        provider = OpenAIProvider(api_key=settings.llm_api_key)
        model = OpenAIModel(settings.model_choice, provider=provider)
        
        rag_agent = CloudRAGAgent(model, use_cloud=True)
        
        # Direct tool call
        from pydantic_ai import RunContext
        from src.agents.rag_cloud import RAGAgentDeps
        
        # Create a mock context
        class MockContext:
            def __init__(self, deps):
                self.deps = deps
        
        deps = RAGAgentDeps(
            vector_client=vector_client,
            graph_client=rag_agent.graph_client
        )
        ctx = MockContext(deps)
        
        # Call the search tool directly
        result = await rag_agent.agent._tools[0].func(
            ctx,
            query="initial BGS validation",
            collection=None,
            n_results=10
        )
        
        print(f"\nRAG tool result:\n{result}")
        
    except Exception as e:
        print(f"✗ RAG agent error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_specific_search())