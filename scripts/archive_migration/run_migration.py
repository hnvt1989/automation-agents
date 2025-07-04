#!/usr/bin/env python3
"""Run the full migration without interactive prompts."""

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


def run_migration():
    """Run the full migration automatically."""
    print("File Migration to Supabase")
    print("=" * 50)
    
    # Initialize migrator
    migrator = FileMigrator()
    
    # Get initial stats
    initial_stats = migrator.get_migration_stats()
    log_info(f"Initial collection stats: {initial_stats}")
    
    print(f"\nMigrating files from:")
    print(f"- data/va_notes (category: va_notes)")
    print(f"- data/meeting_notes (category: meeting_notes)")
    print(f"\nTo Supabase collection: {migrator.collection_name}")
    
    if initial_stats["count"] > 0:
        print(f"\nClearing existing {initial_stats['count']} documents...")
        migrator.clear_migration()
    
    # Migrate VA notes
    print("\n" + "=" * 50)
    print("Migrating VA Notes...")
    va_results = migrator.migrate_directory("va_notes", "va_notes")
    
    # Migrate meeting notes
    print("\n" + "=" * 50)
    print("Migrating Meeting Notes...")
    meeting_results = migrator.migrate_directory("meeting_notes", "meeting_notes")
    
    # Final stats
    print("\n" + "=" * 50)
    print("Migration Summary")
    print("=" * 50)
    print(f"VA Notes: {va_results['successful']}/{va_results['total_files']} successful")
    print(f"Meeting Notes: {meeting_results['successful']}/{meeting_results['total_files']} successful")
    
    total_successful = va_results['successful'] + meeting_results['successful']
    total_files = va_results['total_files'] + meeting_results['total_files']
    print(f"Total: {total_successful}/{total_files} successful")
    
    if va_results['failed_files'] or meeting_results['failed_files']:
        print("\nFailed files:")
        for file in va_results['failed_files'] + meeting_results['failed_files']:
            print(f"  - {file}")
    
    # Final collection stats
    final_stats = migrator.get_migration_stats()
    print(f"\nFinal collection stats: {final_stats}")
    
    return total_successful == total_files


if __name__ == "__main__":
    success = run_migration()
    if success:
        print("\n✓ Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Migration completed with errors.")
        sys.exit(1)