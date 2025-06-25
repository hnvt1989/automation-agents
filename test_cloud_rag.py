#!/usr/bin/env python3
"""Test script for cloud RAG functionality."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("local.env")

async def test_cloud_rag():
    """Test the cloud RAG agent."""
    from pydantic_ai.models.openai import OpenAIModel
    from pydantic_ai.providers.openai import OpenAIProvider
    from src.agents.rag_cloud import CloudRAGAgent
    from src.core.config import get_settings
    
    # Initialize model
    settings = get_settings()
    provider = OpenAIProvider(api_key=settings.llm_api_key)
    model = OpenAIModel(settings.model_choice, provider=provider)
    
    # Create cloud RAG agent
    print("Initializing Cloud RAG agent...")
    rag_agent = CloudRAGAgent(model, use_cloud=True)
    
    # Test 1: Get storage info
    print("\n1. Testing storage info...")
    result = await rag_agent.run("What is the current storage configuration?")
    print(f"Storage info: {result.data}")
    
    # Test 2: Add document to knowledge base
    print("\n2. Testing document addition...")
    test_content = """
    This is a test document for the cloud RAG system.
    It contains information about cloud storage integration with Supabase and Neo4j Aura.
    The system supports vector search using pgvector and OpenAI embeddings.
    """
    
    result = await rag_agent.run(
        f"Add this content to the knowledge base: {test_content}",
        metadata={"source": "test_script", "type": "test"}
    )
    print(f"Add result: {result.data}")
    
    # Test 3: Search knowledge base
    print("\n3. Testing vector search...")
    result = await rag_agent.run("Search for information about cloud storage integration")
    print(f"Search result: {result.data}")
    
    # Test 4: List collections
    print("\n4. Testing list collections...")
    result = await rag_agent.run("List all available collections")
    print(f"Collections: {result.data}")
    
    # Test 5: Test graph operations (if configured)
    if os.getenv("NEO4J_URI"):
        print("\n5. Testing graph operations...")
        result = await rag_agent.run("Search the knowledge graph for entities related to 'cloud'")
        print(f"Graph search result: {result.data}")

if __name__ == "__main__":
    asyncio.run(test_cloud_rag())