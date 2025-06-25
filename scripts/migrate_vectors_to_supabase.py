#!/usr/bin/env python3
"""
Migration script to transfer vector data from ChromaDB to Supabase pgvector.

Usage:
    python scripts/migrate_vectors_to_supabase.py [--collection COLLECTION_NAME] [--batch-size BATCH_SIZE]
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List, Dict, Any
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.storage.chromadb_client import get_chromadb_client
from src.storage.supabase_vector import SupabaseVectorClient
from src.utils.logging import log_info, log_error, log_warning
from src.core.constants import (
    DEFAULT_COLLECTION_NAME,
    COLLECTION_WEBSITES,
    COLLECTION_CONVERSATIONS,
    COLLECTION_KNOWLEDGE
)


def migrate_collection(
    collection_name: str,
    batch_size: int = 100,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Migrate a single collection from ChromaDB to Supabase.
    
    Args:
        collection_name: Name of collection to migrate
        batch_size: Number of documents to process at once
        dry_run: If True, only simulate migration
        
    Returns:
        Migration statistics
    """
    log_info(f"Starting migration for collection: {collection_name}")
    
    # Initialize clients
    chromadb_client = get_chromadb_client()
    
    if dry_run:
        log_info("DRY RUN - No data will be migrated")
    else:
        supabase_client = SupabaseVectorClient(collection_name)
    
    stats = {
        "collection": collection_name,
        "total_documents": 0,
        "migrated": 0,
        "failed": 0,
        "errors": []
    }
    
    try:
        # Get collection from ChromaDB
        collection = chromadb_client.get_collection(collection_name)
        
        # Get total document count
        total_count = collection.count()
        stats["total_documents"] = total_count
        
        log_info(f"Found {total_count} documents in ChromaDB collection '{collection_name}'")
        
        if total_count == 0:
            log_warning(f"No documents to migrate in collection '{collection_name}'")
            return stats
        
        # Migrate in batches
        offset = 0
        while offset < total_count:
            try:
                # Get batch of documents
                result = collection.get(
                    limit=batch_size,
                    offset=offset,
                    include=["documents", "metadatas", "embeddings"]
                )
                
                if not result["ids"]:
                    break
                
                batch_size_actual = len(result["ids"])
                log_info(f"Processing batch: {offset} to {offset + batch_size_actual}")
                
                if not dry_run:
                    # Note: We're not migrating embeddings directly since Supabase
                    # will regenerate them using OpenAI. This ensures consistency.
                    supabase_client.add_documents(
                        documents=result["documents"],
                        metadatas=result["metadatas"],
                        ids=result["ids"]
                    )
                
                stats["migrated"] += batch_size_actual
                offset += batch_size_actual
                
                log_info(f"Progress: {stats['migrated']}/{total_count} documents migrated")
                
            except Exception as e:
                log_error(f"Error migrating batch at offset {offset}: {str(e)}")
                stats["failed"] += batch_size
                stats["errors"].append(f"Batch {offset}: {str(e)}")
                offset += batch_size
                continue
        
    except Exception as e:
        log_error(f"Fatal error during migration: {str(e)}")
        stats["errors"].append(f"Fatal: {str(e)}")
    
    return stats


def verify_migration(collection_name: str, sample_size: int = 5) -> bool:
    """Verify migration by comparing sample queries.
    
    Args:
        collection_name: Collection to verify
        sample_size: Number of test queries
        
    Returns:
        True if verification passed
    """
    log_info(f"Verifying migration for collection: {collection_name}")
    
    try:
        # Get clients
        chromadb_client = get_chromadb_client()
        supabase_client = SupabaseVectorClient(collection_name)
        
        # Get sample documents from ChromaDB
        collection = chromadb_client.get_collection(collection_name)
        sample = collection.get(limit=sample_size)
        
        if not sample["ids"]:
            log_warning("No documents to verify")
            return True
        
        # Test with first document as query
        test_query = sample["documents"][0][:200]  # Use first 200 chars
        
        # Query both systems
        chromadb_results = chromadb_client.query_collection(
            collection_name,
            [test_query],
            n_results=3
        )
        
        supabase_results = supabase_client.query(
            [test_query],
            n_results=3
        )
        
        # Compare results
        chromadb_ids = set(chromadb_results["ids"][0])
        supabase_ids = set(supabase_results["ids"][0])
        
        overlap = chromadb_ids.intersection(supabase_ids)
        
        log_info(f"ChromaDB returned: {chromadb_ids}")
        log_info(f"Supabase returned: {supabase_ids}")
        log_info(f"Overlap: {overlap}")
        
        # Verify stats
        chromadb_count = collection.count()
        supabase_stats = supabase_client.get_collection_stats()
        
        log_info(f"Document counts - ChromaDB: {chromadb_count}, Supabase: {supabase_stats['count']}")
        
        return len(overlap) > 0
        
    except Exception as e:
        log_error(f"Verification failed: {str(e)}")
        return False


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Migrate vectors from ChromaDB to Supabase")
    parser.add_argument(
        "--collection",
        type=str,
        help="Specific collection to migrate (default: all collections)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of documents to process per batch (default: 100)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without actually transferring data"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify migration after completion"
    )
    args = parser.parse_args()
    
    # Load environment
    load_dotenv("local.env")
    
    # Check required environment variables
    required_vars = ["SUPABASE_URL", "SUPABASE_KEY", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars and not args.dry_run:
        log_error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Collections to migrate
    if args.collection:
        collections = [args.collection]
    else:
        collections = [
            DEFAULT_COLLECTION_NAME,
            COLLECTION_WEBSITES,
            COLLECTION_CONVERSATIONS,
            COLLECTION_KNOWLEDGE
        ]
    
    log_info(f"Starting vector migration to Supabase")
    log_info(f"Collections to migrate: {collections}")
    log_info(f"Batch size: {args.batch_size}")
    if args.dry_run:
        log_info("DRY RUN MODE - No data will be migrated")
    
    # Migrate each collection
    all_stats = []
    for collection_name in collections:
        log_info(f"\n{'='*60}")
        log_info(f"Migrating collection: {collection_name}")
        log_info(f"{'='*60}")
        
        stats = migrate_collection(
            collection_name,
            batch_size=args.batch_size,
            dry_run=args.dry_run
        )
        all_stats.append(stats)
        
        # Verify if requested
        if args.verify and not args.dry_run and stats["migrated"] > 0:
            log_info(f"\nVerifying migration for {collection_name}...")
            if verify_migration(collection_name):
                log_info("✓ Verification passed")
            else:
                log_warning("✗ Verification failed - manual review recommended")
    
    # Summary
    log_info(f"\n{'='*60}")
    log_info("MIGRATION SUMMARY")
    log_info(f"{'='*60}")
    
    total_docs = sum(s["total_documents"] for s in all_stats)
    total_migrated = sum(s["migrated"] for s in all_stats)
    total_failed = sum(s["failed"] for s in all_stats)
    
    for stats in all_stats:
        log_info(f"\nCollection: {stats['collection']}")
        log_info(f"  Total documents: {stats['total_documents']}")
        log_info(f"  Migrated: {stats['migrated']}")
        log_info(f"  Failed: {stats['failed']}")
        if stats["errors"]:
            log_info(f"  Errors: {len(stats['errors'])}")
            for error in stats["errors"][:3]:  # Show first 3 errors
                log_info(f"    - {error}")
    
    log_info(f"\nTOTAL: {total_migrated}/{total_docs} documents migrated successfully")
    if total_failed > 0:
        log_warning(f"{total_failed} documents failed to migrate")
    
    if not args.dry_run:
        log_info("\n✓ Migration completed!")
        log_info("\nNext steps:")
        log_info("1. Update RAG agent to use SupabaseVectorClient")
        log_info("2. Test vector search functionality")
        log_info("3. Monitor performance and costs")


if __name__ == "__main__":
    main()