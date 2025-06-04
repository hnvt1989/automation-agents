#!/usr/bin/env python3
"""Script to migrate from single ChromaDB collection to multiple collections."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Dict, List, Any
import argparse
from tqdm import tqdm

from src.storage.chromadb_client import ChromaDBClient, get_chromadb_client
from src.storage.collection_manager import CollectionManager
from src.core.constants import (
    DEFAULT_COLLECTION_NAME,
    COLLECTION_WEBSITES,
    COLLECTION_CONVERSATIONS,
    COLLECTION_KNOWLEDGE
)
from src.utils.logging import log_info, log_error, log_warning


def categorize_document(metadata: Dict[str, Any]) -> str:
    """Categorize a document based on its metadata.
    
    Args:
        metadata: Document metadata
        
    Returns:
        Target collection name
    """
    source_type = metadata.get('source_type', '').lower()
    
    # Direct mapping based on source_type
    if source_type == 'website':
        return COLLECTION_WEBSITES
    elif source_type == 'conversation':
        return COLLECTION_CONVERSATIONS
    elif source_type == 'knowledge':
        return COLLECTION_KNOWLEDGE
    
    # Infer from other metadata fields
    if 'url' in metadata or 'domain' in metadata:
        return COLLECTION_WEBSITES
    elif 'conversation_id' in metadata or 'participants' in metadata or 'platform' in metadata:
        return COLLECTION_CONVERSATIONS
    elif 'file_path' in metadata or 'file_type' in metadata:
        return COLLECTION_KNOWLEDGE
    
    # Default to knowledge collection
    log_warning(f"Could not categorize document with metadata: {metadata}")
    return COLLECTION_KNOWLEDGE


def migrate_collection(
    source_client: ChromaDBClient,
    target_clients: Dict[str, ChromaDBClient],
    batch_size: int = 100,
    dry_run: bool = False
) -> Dict[str, int]:
    """Migrate documents from single collection to multiple collections.
    
    Args:
        source_client: Source ChromaDB client
        target_clients: Dictionary of target collection clients
        batch_size: Number of documents to process at once
        dry_run: If True, only analyze without migrating
        
    Returns:
        Dictionary with migration statistics
    """
    stats = {
        'total': 0,
        'migrated': 0,
        'errors': 0,
        'by_collection': {
            COLLECTION_WEBSITES: 0,
            COLLECTION_CONVERSATIONS: 0,
            COLLECTION_KNOWLEDGE: 0
        }
    }
    
    try:
        # Get total document count
        total_count = source_client.collection.count()
        stats['total'] = total_count
        log_info(f"Found {total_count} documents to migrate")
        
        if total_count == 0:
            log_warning("No documents to migrate")
            return stats
        
        # Process in batches
        offset = 0
        with tqdm(total=total_count, desc="Migrating documents") as pbar:
            while offset < total_count:
                # Get batch of documents
                batch = source_client.get_documents(
                    limit=min(batch_size, total_count - offset)
                )
                
                if not batch['ids']:
                    break
                
                # Categorize and prepare documents for each collection
                collection_batches = {
                    COLLECTION_WEBSITES: {'ids': [], 'documents': [], 'metadatas': []},
                    COLLECTION_CONVERSATIONS: {'ids': [], 'documents': [], 'metadatas': []},
                    COLLECTION_KNOWLEDGE: {'ids': [], 'documents': [], 'metadatas': []}
                }
                
                for i in range(len(batch['ids'])):
                    doc_id = batch['ids'][i]
                    document = batch['documents'][i]
                    metadata = batch['metadatas'][i] or {}
                    
                    # Determine target collection
                    target_collection = categorize_document(metadata)
                    
                    # Add to appropriate batch
                    collection_batches[target_collection]['ids'].append(doc_id)
                    collection_batches[target_collection]['documents'].append(document)
                    collection_batches[target_collection]['metadatas'].append(metadata)
                    
                    stats['by_collection'][target_collection] += 1
                
                # Migrate to target collections
                if not dry_run:
                    for collection_name, batch_data in collection_batches.items():
                        if batch_data['ids']:
                            try:
                                target_clients[collection_name].add_documents(
                                    documents=batch_data['documents'],
                                    metadatas=batch_data['metadatas'],
                                    ids=batch_data['ids']
                                )
                                stats['migrated'] += len(batch_data['ids'])
                            except Exception as e:
                                log_error(f"Error migrating to {collection_name}: {str(e)}")
                                stats['errors'] += len(batch_data['ids'])
                
                # Update progress
                pbar.update(len(batch['ids']))
                offset += len(batch['ids'])
        
    except Exception as e:
        log_error(f"Migration error: {str(e)}")
        stats['errors'] = stats['total'] - stats['migrated']
    
    return stats


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Migrate ChromaDB to multiple collections")
    parser.add_argument(
        "--persist-dir",
        type=Path,
        help="ChromaDB persist directory (uses default if not specified)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of documents to process at once (default: 100)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze migration without actually moving documents"
    )
    parser.add_argument(
        "--clear-source",
        action="store_true",
        help="Clear source collection after successful migration"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize source client
        log_info("Initializing source collection...")
        source_client = ChromaDBClient(
            persist_directory=args.persist_dir,
            collection_name=DEFAULT_COLLECTION_NAME
        )
        
        # Initialize target clients
        log_info("Initializing target collections...")
        target_clients = {
            COLLECTION_WEBSITES: ChromaDBClient(
                persist_directory=args.persist_dir,
                collection_name=COLLECTION_WEBSITES
            ),
            COLLECTION_CONVERSATIONS: ChromaDBClient(
                persist_directory=args.persist_dir,
                collection_name=COLLECTION_CONVERSATIONS
            ),
            COLLECTION_KNOWLEDGE: ChromaDBClient(
                persist_directory=args.persist_dir,
                collection_name=COLLECTION_KNOWLEDGE
            )
        }
        
        # Perform migration
        log_info(f"Starting migration (dry_run={args.dry_run})...")
        stats = migrate_collection(
            source_client,
            target_clients,
            batch_size=args.batch_size,
            dry_run=args.dry_run
        )
        
        # Print results
        print("\n" + "="*50)
        print("MIGRATION RESULTS")
        print("="*50)
        print(f"Total documents: {stats['total']}")
        if not args.dry_run:
            print(f"Successfully migrated: {stats['migrated']}")
            print(f"Errors: {stats['errors']}")
        print("\nDocuments by collection:")
        for collection, count in stats['by_collection'].items():
            print(f"  {collection}: {count}")
        
        # Clear source collection if requested and migration was successful
        if args.clear_source and not args.dry_run and stats['errors'] == 0:
            response = input("\nClear source collection? This cannot be undone! (yes/no): ")
            if response.lower() == 'yes':
                source_client.clear_collection()
                log_info("Source collection cleared")
            else:
                log_info("Source collection retained")
        
        # Verify target collections
        if not args.dry_run:
            print("\nVerifying target collections:")
            for collection_name, client in target_clients.items():
                count = client.collection.count()
                print(f"  {collection_name}: {count} documents")
        
    except Exception as e:
        log_error(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()