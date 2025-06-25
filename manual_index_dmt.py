#!/usr/bin/env python3
"""Manually index the dmt_release_process.md file."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Must set env vars before imports
os.environ['USE_CLOUD_STORAGE'] = 'true'

from dotenv import load_dotenv
load_dotenv("local.env")

async def manual_index():
    """Manually index the file."""
    print("Manual Indexing of dmt_release_process.md")
    print("=" * 50)
    
    # Get absolute path
    file_path = project_root / "data" / "va_notes" / "dmt_release_process.md"
    print(f"File path: {file_path}")
    print(f"File exists: {file_path.exists()}")
    
    if not file_path.exists():
        print("ERROR: File not found!")
        return
    
    # Read content
    content = file_path.read_text()
    print(f"Content length: {len(content)} chars")
    print(f"Contains 'initial BGS validation': {'initial BGS validation' in content}")
    
    # Import after env setup
    from scripts.index_to_cloud import CloudIndexer
    
    # Create indexer
    print("\nInitializing indexer...")
    indexer = CloudIndexer(collection_name="documents")
    
    # Force index the file
    print("\nIndexing file...")
    success = await indexer.index_file(file_path, force_reindex=True)
    
    if success:
        print("✓ Successfully indexed!")
        
        # Verify it's in the database
        from src.storage.supabase_client import get_supabase_client
        client = get_supabase_client()
        
        result = client.client.table("document_embeddings") \
            .select("document_id, content") \
            .like("document_id", "%dmt_release%") \
            .execute()
        
        if result.data:
            print(f"\n✓ Verified: Found {len(result.data)} chunks in database")
            for chunk in result.data[:3]:
                if "initial BGS validation" in chunk['content']:
                    print(f"\n✓ FOUND TARGET CONTENT in chunk: {chunk['document_id']}")
                    break
        else:
            print("\n✗ ERROR: File was not found in database after indexing!")
    else:
        print("✗ Failed to index file")

if __name__ == "__main__":
    asyncio.run(manual_index())