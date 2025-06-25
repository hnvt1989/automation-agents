#!/usr/bin/env python3
"""Show what's in all collections."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv("local.env")

print("Checking All Collections")
print("=" * 70)

# Check Supabase collections
print("\n1. SUPABASE COLLECTIONS:")
print("-" * 30)

try:
    from src.storage.supabase_client import get_supabase_client
    client = get_supabase_client()
    
    # Get unique collections
    result = client.client.table("document_embeddings") \
        .select("collection_name") \
        .execute()
    
    if result.data:
        collections = set(item['collection_name'] for item in result.data)
        print(f"Found {len(collections)} collections: {sorted(collections)}")
        
        # Count documents in each
        for coll in sorted(collections):
            count_result = client.client.table("document_embeddings") \
                .select("document_id") \
                .eq("collection_name", coll) \
                .execute()
            
            if count_result.data:
                unique_docs = set()
                for item in count_result.data:
                    doc_id = item['document_id']
                    if '_chunk_' in doc_id:
                        doc_id = doc_id.split('_chunk_')[0]
                    unique_docs.add(doc_id)
                
                print(f"\n  Collection '{coll}':")
                print(f"    - {len(count_result.data)} chunks")
                print(f"    - {len(unique_docs)} unique documents")
                
                # Check for BGS content
                bgs_result = client.client.table("document_embeddings") \
                    .select("document_id, content") \
                    .eq("collection_name", coll) \
                    .ilike("content", "%BGS%") \
                    .limit(3) \
                    .execute()
                
                if bgs_result.data:
                    print(f"    - Contains BGS-related content ✓")
                    
                # Check for "initial BGS validation"
                validation_result = client.client.table("document_embeddings") \
                    .select("document_id, content") \
                    .eq("collection_name", coll) \
                    .ilike("content", "%initial BGS validation%") \
                    .limit(1) \
                    .execute()
                
                if validation_result.data:
                    print(f"    - Contains 'initial BGS validation' ✓✓✓")
                    print(f"      Found in: {validation_result.data[0]['document_id']}")
    else:
        print("No collections found in Supabase")
        
except Exception as e:
    print(f"Supabase error: {e}")

# Check ChromaDB collections
print("\n\n2. CHROMADB COLLECTIONS (Local):")
print("-" * 30)

try:
    from src.storage.chromadb_client import get_chromadb_client
    client = get_chromadb_client()
    
    collections = client.client.list_collections()
    if collections:
        print(f"Found {len(collections)} collections:")
        
        for coll in collections:
            print(f"\n  Collection '{coll.name}':")
            count = coll.count()
            print(f"    - {count} documents")
            
            # Try to search for BGS
            try:
                results = coll.query(
                    query_texts=["BGS validation"],
                    n_results=3
                )
                if results['documents'][0]:
                    print(f"    - Contains BGS-related content ✓")
                    
                # Search for specific phrase
                results2 = coll.query(
                    query_texts=["initial BGS validation"],
                    n_results=1
                )
                if results2['documents'][0]:
                    for doc in results2['documents'][0]:
                        if "initial BGS validation" in doc.lower():
                            print(f"    - Contains 'initial BGS validation' ✓✓✓")
                            break
            except Exception as e:
                print(f"    - Search error: {e}")
    else:
        print("No collections found in ChromaDB")
        
except Exception as e:
    print(f"ChromaDB error: {e}")

print("\n" + "=" * 70)
print("SUMMARY:")
print("If 'initial BGS validation' is marked with ✓✓✓, that's where your content is!")
print("Make sure you're searching in the right collection/storage system.")