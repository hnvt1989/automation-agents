#!/usr/bin/env python3
"""Test script to debug Supabase vector search for BGS content."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.storage.supabase_vector import SupabaseVectorClient
from src.storage.supabase_client import get_supabase_client
from src.utils.logging import log_info, log_error

def test_search():
    """Test search functionality."""
    print("Testing Supabase vector search...")
    
    # Test 1: Check if documents exist in the database
    print("\n1. Checking document_embeddings table...")
    try:
        client = get_supabase_client()
        
        # Get count of documents
        result = client.client.table("document_embeddings").select("*", count="exact").execute()
        print(f"Total documents in database: {result.count}")
        
        # Check for BGS-related documents
        bgs_docs = client.client.table("document_embeddings").select("*").ilike("content", "%BGS%").limit(5).execute()
        if bgs_docs.data:
            print(f"\nFound {len(bgs_docs.data)} BGS-related documents:")
            for doc in bgs_docs.data:
                print(f"- Collection: {doc['collection_name']}")
                print(f"  ID: {doc['document_id']}")
                print(f"  Content preview: {doc['content'][:100]}...")
                print()
        else:
            print("No BGS-related documents found in database")
            
    except Exception as e:
        print(f"Error checking database: {str(e)}")
    
    # Test 2: Test vector search
    print("\n2. Testing vector search...")
    try:
        # Try different collection names
        collections = ["default", "knowledge_base", "va_notes"]
        
        for collection_name in collections:
            print(f"\nSearching in collection '{collection_name}'...")
            vector_client = SupabaseVectorClient(collection_name)
            
            # Search for BGS validation
            queries = [
                "initial BGS validation",
                "BGS validation",
                "BGS service",
                "Benefits Gateway Services"
            ]
            
            for query in queries:
                print(f"\n  Query: '{query}'")
                results = vector_client.query([query], n_results=3)
                
                if results['documents'] and results['documents'][0]:
                    print(f"  Found {len(results['documents'][0])} results:")
                    for i, doc in enumerate(results['documents'][0]):
                        print(f"    Result {i+1}: {doc[:150]}...")
                else:
                    print("  No results found")
                    
    except Exception as e:
        print(f"Error in vector search: {str(e)}")
    
    # Test 3: Check collection statistics
    print("\n3. Checking collection statistics...")
    try:
        result = client.client.rpc("get_collection_stats").execute()
        if result.data:
            print("Collection statistics:")
            for stat in result.data:
                print(f"- {stat['collection_name']}: {stat['document_count']} documents")
        else:
            print("No collection statistics available")
    except Exception as e:
        print(f"Error getting stats: {str(e)}")

if __name__ == "__main__":
    test_search()