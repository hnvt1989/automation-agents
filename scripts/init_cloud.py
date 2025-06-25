#!/usr/bin/env python3
"""Initialize cloud services and verify configuration."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv("local.env")

print("Cloud Services Initialization")
print("=" * 70)

# Check environment variables
neo4j_uri = os.getenv("NEO4J_URI", "")
supabase_url = os.getenv("SUPABASE_URL", "")

print("\n1. Configuration Check:")
print(f"   NEO4J_URI: {'✓ Set' if neo4j_uri else '✗ Not set'}")
print(f"   - Cloud mode: {'Yes' if neo4j_uri.startswith('neo4j+s://') else 'No'}")
print(f"   SUPABASE_URL: {'✓ Set' if supabase_url else '✗ Not set'}")

if neo4j_uri.startswith('neo4j+s://'):
    print("\n2. Neo4j Aura Configuration:")
    print("   ✓ Using Neo4j Aura (cloud)")
    print("   ✓ Vector operations disabled")
    print("   ✓ Graphiti integration skipped")
    
    # Test connection
    try:
        from src.storage.neo4j_cloud import get_neo4j_cloud_client
        client = get_neo4j_cloud_client()
        stats = client.get_graph_summary()
        print(f"   ✓ Connected successfully")
        print(f"   - Nodes: {stats.get('node_count', 0)}")
        print(f"   - Relationships: {stats.get('relationship_count', 0)}")
        client.close()
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")

if supabase_url:
    print("\n3. Supabase Configuration:")
    print("   ✓ Using Supabase for vector storage")
    
    # Test connection
    try:
        from src.storage.supabase_vector import SupabaseVectorClient
        client = SupabaseVectorClient()
        stats = client.get_collection_stats()
        print(f"   ✓ Connected successfully")
        print(f"   - Documents: {stats.get('count', 0)}")
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")

print("\n" + "=" * 70)
print("Configuration complete!")
print("\nTo run the application with cloud services:")
print("  python -m src.main")
print("\nTo search across collections:")
print("  Use CloudRAGAgent without specifying a collection")
