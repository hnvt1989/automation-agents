#!/usr/bin/env python3
"""Check what's in the knowledge_base collection."""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv("local.env")

print("Checking knowledge_base collection...")
print("=" * 70)

# Check if it's in ChromaDB (local)
try:
    from src.storage.chromadb_client import get_chromadb_client
    
    client = get_chromadb_client()
    
    # Get the knowledge_base collection
    try:
        collection = client.get_collection("knowledge_base")
        print(f"\n✓ Found 'knowledge_base' collection in ChromaDB")
        print(f"  Document count: {collection.count()}")
        
        # Search for BGS content
        results = collection.query(
            query_texts=["initial BGS validation"],
            n_results=5
        )
        
        if results['documents'][0]:
            print(f"\n✓ Found {len(results['documents'][0])} results for 'initial BGS validation'")
            for i, doc in enumerate(results['documents'][0]):
                if "initial BGS" in doc:
                    print(f"\n  Result {i+1} contains target content:")
                    print(f"  {doc[:200]}...")
                    if results['metadatas'][0][i]:
                        print(f"  Metadata: {results['metadatas'][0][i]}")
        
    except Exception as e:
        print(f"✗ Error accessing knowledge_base collection: {e}")
        
except Exception as e:
    print(f"✗ ChromaDB error: {e}")

# Also check Supabase knowledge_base
print("\n\nChecking Supabase knowledge_base collection...")
try:
    from src.storage.supabase_vector import SupabaseVectorClient
    
    kb_client = SupabaseVectorClient("knowledge_base")
    stats = kb_client.get_collection_stats()
    print(f"✓ Supabase knowledge_base stats: {stats}")
    
    # Try searching
    results = kb_client.query(["initial BGS validation"], n_results=5)
    if results and results.get('documents') and results['documents'][0]:
        print(f"\n✓ Found {len(results['documents'][0])} results in Supabase knowledge_base")
    
except Exception as e:
    print(f"✗ Supabase knowledge_base error: {e}")