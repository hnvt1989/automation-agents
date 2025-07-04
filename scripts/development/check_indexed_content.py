#!/usr/bin/env python3
"""Check what content is actually indexed in Supabase."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.storage.supabase_client import get_supabase_client

def check_indexed_content():
    """Check what's indexed in Supabase."""
    load_dotenv("local.env")
    
    print("Checking Indexed Content in Supabase...")
    print("=" * 70)
    
    try:
        client = get_supabase_client()
        
        # Get all documents
        print("\n1. Getting all indexed documents...")
        result = client.client.table("document_embeddings") \
            .select("collection_name, document_id, content") \
            .execute()
        
        if result.data:
            print(f"\nTotal chunks indexed: {len(result.data)}")
            
            # Group by collection
            collections = {}
            for doc in result.data:
                coll = doc['collection_name']
                if coll not in collections:
                    collections[coll] = []
                collections[coll].append(doc)
            
            print(f"\nCollections found: {list(collections.keys())}")
            
            for coll, docs in collections.items():
                print(f"\n\nCollection '{coll}': {len(docs)} chunks")
                
                # Get unique document IDs
                unique_docs = set()
                for doc in docs:
                    # Extract base document ID (without chunk suffix)
                    doc_id = doc['document_id']
                    if '_chunk_' in doc_id:
                        doc_id = doc_id.split('_chunk_')[0]
                    unique_docs.add(doc_id)
                
                print(f"Unique documents: {len(unique_docs)}")
                
                # Show sample content
                print("\nSample content:")
                for i, doc in enumerate(docs[:3]):
                    content = doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content']
                    print(f"\n  [{i+1}] Document ID: {doc['document_id']}")
                    print(f"      Content: {content}")
            
            # Search for BGS content
            print("\n\n2. Searching for BGS-related content...")
            bgs_chunks = [doc for doc in result.data if 'BGS' in doc.get('content', '')]
            print(f"Found {len(bgs_chunks)} chunks containing 'BGS'")
            
            if bgs_chunks:
                print("\nSample BGS content:")
                for i, doc in enumerate(bgs_chunks[:3]):
                    content = doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content']
                    print(f"\n  [{i+1}] Document ID: {doc['document_id']}")
                    print(f"      Collection: {doc['collection_name']}")
                    print(f"      Content: {content}")
            
            # Check for specific document
            print("\n\n3. Checking for dmt_release_process.md...")
            dmt_chunks = [doc for doc in result.data if 'dmt_release' in doc.get('document_id', '').lower()]
            if dmt_chunks:
                print(f"Found {len(dmt_chunks)} chunks from dmt_release_process.md")
            else:
                print("dmt_release_process.md is NOT indexed")
            
        else:
            print("\nNo documents found in Supabase!")
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_indexed_content()