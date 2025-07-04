#!/usr/bin/env python3
"""Test script for the new Supabase document management system."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv(os.path.join(project_root, 'local.env'))

from src.storage.document_manager import SupabaseDocumentManager
from src.utils.logging import log_info, log_error


def test_document_crud():
    """Test CRUD operations for documents."""
    print("Testing Supabase Document Management System")
    print("=" * 50)
    
    # Initialize document manager
    doc_manager = SupabaseDocumentManager(collection_name="test_documents")
    
    # Clean up any existing test data
    print("\nCleaning up test data...")
    doc_manager.client.clear_collection()
    
    test_filename = "test_document.md"
    test_content = """# Test Document

This is a test document for verifying the Supabase document management system.

## Features to Test

- Create document
- Read document
- Update document
- Delete document
- Search documents
- List documents

## Content

This document contains some test content that should be indexed and searchable.
The system should be able to chunk this content appropriately and store it in Supabase.
"""
    
    # Test 1: Create document
    print("\n1. Testing CREATE operation...")
    try:
        doc_id = doc_manager.create_document(
            filename=test_filename,
            content=test_content,
            category="test"
        )
        print(f"✓ Created document with ID: {doc_id}")
    except Exception as e:
        print(f"✗ Create failed: {e}")
        return False
    
    # Test 2: List documents
    print("\n2. Testing LIST operation...")
    try:
        documents = doc_manager.list_documents()
        print(f"✓ Found {len(documents)} documents")
        for doc in documents:
            print(f"  - {doc['filename']} ({doc['file_size']} bytes, {doc['chunk_count']} chunks)")
    except Exception as e:
        print(f"✗ List failed: {e}")
        return False
    
    # Test 3: Read document
    print("\n3. Testing READ operation...")
    try:
        document = doc_manager.get_document(test_filename)
        if document:
            print(f"✓ Retrieved document: {document['filename']}")
            print(f"  Content length: {len(document['content'])} characters")
            print(f"  Chunks: {document['chunk_count']}")
        else:
            print("✗ Document not found")
            return False
    except Exception as e:
        print(f"✗ Read failed: {e}")
        return False
    
    # Test 4: Search documents
    print("\n4. Testing SEARCH operation...")
    try:
        search_results = doc_manager.search_documents("test content", n_results=3)
        print(f"✓ Search returned {len(search_results)} results")
        for i, result in enumerate(search_results):
            print(f"  {i+1}. {result['filename']} (similarity: {result['similarity']:.3f})")
            print(f"     Snippet: {result['content_snippet']}")
    except Exception as e:
        print(f"✗ Search failed: {e}")
        return False
    
    # Test 5: Update document
    print("\n5. Testing UPDATE operation...")
    updated_content = test_content + "\n\n## Updated Section\n\nThis content was added during the update test."
    try:
        success = doc_manager.update_document(
            filename=test_filename,
            content=updated_content,
            metadata={"updated": True}
        )
        if success:
            print("✓ Document updated successfully")
            
            # Verify update
            updated_doc = doc_manager.get_document(test_filename)
            if updated_doc and "Updated Section" in updated_doc['content']:
                print("✓ Update verification successful")
            else:
                print("✗ Update verification failed")
                return False
        else:
            print("✗ Update failed")
            return False
    except Exception as e:
        print(f"✗ Update failed: {e}")
        return False
    
    # Test 6: Delete document
    print("\n6. Testing DELETE operation...")
    try:
        success = doc_manager.delete_document(test_filename)
        if success:
            print("✓ Document deleted successfully")
            
            # Verify deletion
            deleted_doc = doc_manager.get_document(test_filename)
            if not deleted_doc:
                print("✓ Deletion verification successful")
            else:
                print("✗ Deletion verification failed")
                return False
        else:
            print("✗ Delete failed")
            return False
    except Exception as e:
        print(f"✗ Delete failed: {e}")
        return False
    
    # Test 7: Collection info
    print("\n7. Testing COLLECTION INFO...")
    try:
        info = doc_manager.get_collection_info()
        print(f"✓ Collection info retrieved:")
        print(f"  Name: {info['collection_name']}")
        print(f"  Total chunks: {info['total_chunks']}")
        print(f"  Total documents: {info['total_documents']}")
        print(f"  Embedding model: {info['embedding_model']}")
    except Exception as e:
        print(f"✗ Collection info failed: {e}")
        return False
    
    return True


def test_migrated_documents():
    """Test access to migrated documents."""
    print("\n" + "=" * 50)
    print("Testing Access to Migrated Documents")
    print("=" * 50)
    
    # Test file_migration collection
    doc_manager = SupabaseDocumentManager(collection_name="file_migration")
    
    try:
        # Get collection info
        info = doc_manager.get_collection_info()
        print(f"Migrated collection info:")
        print(f"  Total chunks: {info['total_chunks']}")
        print(f"  Total documents: {info['total_documents']}")
        
        if info['total_documents'] > 0:
            # Test search in migrated documents
            search_results = doc_manager.search_documents("meeting", n_results=3)
            print(f"\nSearch results for 'meeting': {len(search_results)} found")
            for i, result in enumerate(search_results):
                print(f"  {i+1}. {result['filename']} (similarity: {result['similarity']:.3f})")
        else:
            print("No migrated documents found")
            
    except Exception as e:
        print(f"Error accessing migrated documents: {e}")
        return False
    
    return True


def main():
    """Main test function."""
    try:
        # Test CRUD operations
        crud_success = test_document_crud()
        
        # Test migrated documents
        migration_success = test_migrated_documents()
        
        print("\n" + "=" * 50)
        print("Test Summary")
        print("=" * 50)
        print(f"CRUD Operations: {'✓ PASSED' if crud_success else '✗ FAILED'}")
        print(f"Migrated Documents: {'✓ PASSED' if migration_success else '✗ FAILED'}")
        
        if crud_success and migration_success:
            print("\n🎉 All tests passed! Document management system is working correctly.")
            return 0
        else:
            print("\n❌ Some tests failed.")
            return 1
            
    except Exception as e:
        log_error(f"Test failed with error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())