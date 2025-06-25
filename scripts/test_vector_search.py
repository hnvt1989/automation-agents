#!/usr/bin/env python3
"""Test script to verify vector search is working properly."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.storage.supabase_vector import SupabaseVectorClient

def test_vector_search():
    """Test vector search functionality."""
    # Load environment
    load_dotenv("local.env")
    
    print("Testing Supabase Vector Search...")
    print("=" * 50)
    
    try:
        # Initialize client
        client = SupabaseVectorClient("test")
        
        # Test 1: Add a test document
        print("\n1. Adding a test document...")
        test_content = "This is a test document about cloud storage integration with Supabase and Neo4j."
        client.add_documents(
            documents=[test_content],
            metadatas=[{"source": "test", "type": "test"}],
            ids=["test_doc_1"]
        )
        print("✓ Document added successfully")
        
        # Test 2: Search for the document
        print("\n2. Searching for the document...")
        results = client.query(
            query_texts=["cloud storage"],
            n_results=5
        )
        
        if results and results.get('documents') and results['documents'][0]:
            print(f"✓ Found {len(results['documents'][0])} results")
            for i, doc in enumerate(results['documents'][0]):
                print(f"   Result {i+1}: {doc[:100]}...")
        else:
            print("❌ No results found")
        
        # Test 3: Get collection stats
        print("\n3. Getting collection statistics...")
        stats = client.get_collection_stats()
        print(f"✓ Collection stats: {stats}")
        
        # Test 4: Clean up
        print("\n4. Cleaning up test document...")
        client.delete_documents(["test_doc_1"])
        print("✓ Test document deleted")
        
        print("\n" + "=" * 50)
        print("✅ All tests passed! Vector search is working properly.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease make sure you've run the fix_match_documents_function.sql in Supabase")
        return False
    
    return True

if __name__ == "__main__":
    test_vector_search()