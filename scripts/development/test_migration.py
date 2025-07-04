#!/usr/bin/env python3
"""Test script for file migration to Supabase."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv(os.path.join(project_root, 'local.env'))

from src.storage.supabase_vector import SupabaseVectorClient
from src.utils.logging import log_info, log_error
from migrate_files_to_supabase import FileMigrator


def test_migration():
    """Test migration with a single file."""
    print("Testing File Migration")
    print("=" * 30)
    
    # Initialize test migrator
    migrator = FileMigrator(collection_name="test_migration")
    
    # Clear any existing test data
    migrator.clear_migration()
    
    # Find a small test file
    test_files = []
    
    # Look for small files in meeting_notes
    meeting_files = migrator.get_files_to_migrate("meeting_notes")
    for file in meeting_files:
        if file.stat().st_size < 3000:  # Less than 3KB
            test_files.append((file, "meeting_notes"))
            break
    
    # Look for small files in va_notes
    va_files = migrator.get_files_to_migrate("va_notes")
    for file in va_files:
        if file.stat().st_size < 5000:  # Less than 5KB
            test_files.append((file, "va_notes"))
            break
    
    if not test_files:
        print("No suitable test files found")
        return False
    
    # Test migration
    success_count = 0
    for file_path, category in test_files:
        print(f"\nTesting migration of: {file_path.name}")
        print(f"Category: {category}")
        print(f"Size: {file_path.stat().st_size} bytes")
        
        if migrator.migrate_file(file_path, category):
            success_count += 1
            print("✓ Migration successful")
        else:
            print("✗ Migration failed")
    
    # Test search functionality
    print(f"\n{'='*30}")
    print("Testing Search Functionality")
    print("=" * 30)
    
    # Try searching for content
    test_queries = ["meeting", "test", "documentation"]
    
    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        results = migrator.client.query([query], n_results=3)
        
        if results["documents"] and results["documents"][0]:
            print(f"Found {len(results['documents'][0])} results")
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                file_path = metadata.get("file_path", "Unknown")
                print(f"  - {file_path} (similarity: {results['distances'][0][i]:.3f})")
        else:
            print("No results found")
    
    # Get final stats
    stats = migrator.get_migration_stats()
    print(f"\nFinal stats: {stats}")
    
    # Clean up test data
    print("\nCleaning up test data...")
    migrator.clear_migration()
    
    return success_count == len(test_files)


def main():
    """Main test function."""
    try:
        success = test_migration()
        if success:
            print("\n✓ All tests passed! Migration script is ready.")
            return 0
        else:
            print("\n✗ Some tests failed.")
            return 1
    except Exception as e:
        log_error(f"Test failed with error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())