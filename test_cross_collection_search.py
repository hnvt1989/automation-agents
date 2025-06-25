#!/usr/bin/env python3
"""Test cross-collection search functionality."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv("local.env")

async def test_cross_collection_search():
    """Test searching across all collections."""
    print("Testing Cross-Collection Search")
    print("=" * 70)
    
    from pydantic_ai.models.openai import OpenAIModel
    from pydantic_ai.providers.openai import OpenAIProvider
    from src.agents.rag_cloud import CloudRAGAgent
    from src.core.config import get_settings
    
    settings = get_settings()
    provider = OpenAIProvider(api_key=settings.llm_api_key)
    model = OpenAIModel(settings.model_choice, provider=provider)
    
    # Test with cloud RAG agent
    print("\n1. Testing with CloudRAGAgent (searching all collections)...")
    rag_agent = CloudRAGAgent(model, use_cloud=True)
    
    # Search without specifying collection (will search all)
    queries = [
        "initial BGS validation",
        "BGS validation process",
        "what is BGS"
    ]
    
    for query in queries:
        print(f"\n\nSearching for: '{query}'")
        print("-" * 50)
        
        try:
            result = await rag_agent.run(f"search for {query}")
            print(result.data)
        except Exception as e:
            print(f"Error: {e}")
    
    # Also test local RAG if available
    print("\n\n2. Testing with local RAG agent...")
    try:
        from src.agents.rag import RAGAgent
        local_rag = RAGAgent(model)
        
        result = await local_rag.run("search for initial BGS validation")
        print(result.data)
    except Exception as e:
        print(f"Local RAG not available or error: {e}")

if __name__ == "__main__":
    asyncio.run(test_cross_collection_search())