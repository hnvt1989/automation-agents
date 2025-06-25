#!/usr/bin/env python3
"""Debug script to test search functionality."""

import os
import sys
from pathlib import Path
import traceback

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

async def test_search():
    """Test the search functionality."""
    # Load environment
    load_dotenv("local.env")
    
    print("Testing Search Functionality...")
    print("=" * 50)
    
    try:
        # Test 1: Direct Supabase search
        print("\n1. Testing direct Supabase search...")
        from src.storage.supabase_vector import SupabaseVectorClient
        
        client = SupabaseVectorClient("documents")
        
        # Try a simple search
        query = "GFE"
        print(f"Searching for: '{query}'")
        
        results = client.query([query], n_results=5)
        print(f"Results: {results}")
        
        if results and results.get('documents') and results['documents'][0]:
            print(f"\nFound {len(results['documents'][0])} results")
            for i, doc in enumerate(results['documents'][0][:3]):
                print(f"\nResult {i+1}:")
                print(f"  Content: {doc[:200]}...")
                if results.get('metadatas') and results['metadatas'][0] and i < len(results['metadatas'][0]):
                    print(f"  Metadata: {results['metadatas'][0][i]}")
        else:
            print("No results found")
        
    except Exception as e:
        print(f"\nError in direct search: {e}")
        traceback.print_exc()
    
    try:
        # Test 2: RAG Agent search
        print("\n\n2. Testing RAG agent search...")
        from pydantic_ai.models.openai import OpenAIModel
        from pydantic_ai.providers.openai import OpenAIProvider
        from src.agents.rag_cloud import CloudRAGAgent
        from src.core.config import get_settings
        
        settings = get_settings()
        provider = OpenAIProvider(api_key=settings.llm_api_key)
        model = OpenAIModel(settings.model_choice, provider=provider)
        
        rag_agent = CloudRAGAgent(model, use_cloud=True)
        
        # Test search
        result = await rag_agent.run("What is GFE?")
        print(f"\nRAG Agent result: {result.data}")
        
    except Exception as e:
        print(f"\nError in RAG agent search: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_search())