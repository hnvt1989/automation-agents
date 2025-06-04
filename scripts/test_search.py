#!/usr/bin/env python3
"""Quick test script to search indexed data."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.chromadb_client import ChromaDBClient
from src.storage.collection_manager import CollectionManager
from src.core.config import get_settings

def main():
    # Initialize ChromaDB client
    settings = get_settings()
    chroma_client = ChromaDBClient(
        persist_directory=settings.chroma_persist_directory
    )
    
    # Create collection manager
    collection_manager = CollectionManager(chroma_client)
    
    # Test searches
    test_queries = [
        "BGS SOAP",
        "testing strategy",
        "scrum meeting",
        "cypress tests",
        "veteran benefits"
    ]
    
    print("=== Testing Search Functionality ===\n")
    
    for query in test_queries:
        print(f"Query: '{query}'")
        print("-" * 50)
        
        # Search knowledge collection
        results = collection_manager.search_by_type(
            query=query,
            source_types=["knowledge"],
            n_results=3
        )
        
        if results:
            for i, result in enumerate(results[:3]):
                metadata = result.get('metadata', {})
                print(f"\nResult {i+1}:")
                print(f"  File: {metadata.get('file_name', 'Unknown')}")
                print(f"  Category: {metadata.get('category', 'Unknown')}")
                print(f"  Score: {result.get('score', 0):.3f}")
                print(f"  Content preview: {result.get('content', '')[:100]}...")
        else:
            print("  No results found")
        
        print("\n")

if __name__ == '__main__':
    main()