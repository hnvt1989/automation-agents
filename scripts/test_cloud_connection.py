#!/usr/bin/env python3
"""Test script to verify cloud service connections before indexing."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

def test_connections():
    """Test connections to cloud services."""
    # Load environment
    load_dotenv("local.env")
    
    print("Testing Cloud Service Connections...")
    print("=" * 50)
    
    # Test Supabase
    print("\n1. Testing Supabase connection...")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found!")
        print("   Please set SUPABASE_URL and SUPABASE_KEY in local.env")
        return False
    
    print(f"✓ Supabase URL: {supabase_url}")
    print("✓ Supabase key found")
    
    try:
        from src.storage.supabase_vector import SupabaseVectorClient
        client = SupabaseVectorClient("test")
        stats = client.get_collection_stats()
        print(f"✓ Supabase connection successful! Collection stats: {stats}")
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False
    
    # Test Neo4j
    print("\n2. Testing Neo4j Aura connection...")
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not neo4j_uri or not neo4j_password:
        print("❌ Neo4j credentials not found!")
        print("   Please set NEO4J_URI and NEO4J_PASSWORD in local.env")
        return False
    
    print(f"✓ Neo4j URI: {neo4j_uri}")
    print("✓ Neo4j password found")
    
    try:
        from src.storage.neo4j_cloud import get_neo4j_cloud_client
        client = get_neo4j_cloud_client()
        summary = client.get_graph_summary()
        print(f"✓ Neo4j connection successful! Graph summary: {summary}")
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        return False
    
    # Test OpenAI
    print("\n3. Testing OpenAI API (for embeddings)...")
    openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    
    if not openai_key:
        print("❌ OpenAI API key not found!")
        print("   Please set OPENAI_API_KEY or LLM_API_KEY in local.env")
        return False
    
    print("✓ OpenAI API key found")
    
    try:
        import openai
        openai.api_key = openai_key
        # Test with a small embedding
        response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input="test"
        )
        print(f"✓ OpenAI API connection successful! Embedding dimensions: {len(response.data[0].embedding)}")
    except Exception as e:
        print(f"❌ OpenAI API connection failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ All cloud services are properly configured!")
    print("\nYou can now run the indexing script:")
    print("  ./index_docs.sh")
    print("\nOr with options:")
    print("  ./index_docs.sh --clear  # Clear existing data first")
    print("  ./index_docs.sh --directories data/custom_dir  # Index custom directory")
    
    return True

if __name__ == "__main__":
    success = test_connections()
    sys.exit(0 if success else 1)