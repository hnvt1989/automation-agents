#!/usr/bin/env python3
"""Index a single file to cloud services."""

import os
import sys
import asyncio
from pathlib import Path
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from scripts.index_to_cloud import CloudIndexer
from src.utils.logging import setup_logger, log_info

async def index_single_file(file_path: str, collection: str = "documents"):
    """Index a single file."""
    # Load environment
    load_dotenv("local.env")
    setup_logger("single_file_indexer")
    
    # Convert to Path
    file_path = Path(file_path)
    if not file_path.is_absolute():
        file_path = project_root / file_path
    
    if not file_path.exists():
        log_info(f"File not found: {file_path}")
        return False
    
    log_info(f"Indexing single file: {file_path}")
    
    # Initialize indexer
    indexer = CloudIndexer(collection_name=collection)
    
    # Index the file
    success = await indexer.index_file(file_path, force_reindex=True)
    
    if success:
        log_info(f"Successfully indexed: {file_path}")
        
        # Show stats
        stats = indexer.get_stats()
        log_info(f"Collection stats: {stats.get('vector_storage', {})}")
    else:
        log_info(f"Failed to index: {file_path}")
    
    return success

async def main():
    parser = argparse.ArgumentParser(description="Index a single file to cloud services")
    parser.add_argument("file", help="Path to the file to index")
    parser.add_argument("--collection", default="documents", help="Collection name")
    
    args = parser.parse_args()
    
    await index_single_file(args.file, args.collection)

if __name__ == "__main__":
    asyncio.run(main())