#!/usr/bin/env python3
"""Migration script to move files from data/ directories to Supabase."""

import os
import sys
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv(os.path.join(project_root, 'local.env'))

from src.storage.supabase_vector import SupabaseVectorClient
from src.utils.logging import log_info, log_error, log_warning


class FileMigrator:
    """Handles migration of files to Supabase."""
    
    def __init__(self, collection_name: str = "file_migration"):
        """Initialize the migrator."""
        self.collection_name = collection_name
        self.client = SupabaseVectorClient(collection_name=collection_name)
        self.base_path = Path(__file__).parent.parent / "data"
        
    def get_files_to_migrate(self, directory: str) -> List[Path]:
        """Get all markdown files in a directory."""
        target_dir = self.base_path / directory
        if not target_dir.exists():
            log_warning(f"Directory {target_dir} does not exist")
            return []
            
        files = list(target_dir.rglob("*.md"))
        log_info(f"Found {len(files)} files in {directory}")
        return files
    
    def read_file_content(self, file_path: Path) -> str:
        """Read file content with proper encoding."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with latin-1 encoding as fallback
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
    
    def create_metadata(self, file_path: Path, category: str) -> Dict[str, Any]:
        """Create metadata for a file."""
        stat = file_path.stat()
        relative_path = file_path.relative_to(self.base_path)
        
        metadata = {
            "file_path": str(relative_path),
            "absolute_path": str(file_path),
            "category": category,
            "file_size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "migration_date": datetime.now().isoformat(),
            "file_extension": file_path.suffix,
            "parent_directory": file_path.parent.name
        }
        
        # Add subcategory for meeting notes
        if category == "meeting_notes":
            if "1on1" in str(file_path):
                metadata["subcategory"] = "1on1"
            elif "scrum" in str(file_path):
                metadata["subcategory"] = "scrum"
            else:
                metadata["subcategory"] = "general"
        
        return metadata
    
    def migrate_file(self, file_path: Path, category: str) -> bool:
        """Migrate a single file to Supabase."""
        try:
            log_info(f"Migrating {file_path.name}")
            
            # Read file content
            content = self.read_file_content(file_path)
            
            # Skip empty files
            if not content.strip():
                log_warning(f"Skipping empty file: {file_path}")
                return False
            
            # Create metadata
            metadata = self.create_metadata(file_path, category)
            
            # Add to Supabase using contextual chunking
            self.client.add_documents_with_context(
                content=content,
                context_info=metadata,
                use_llm_context=False  # Skip LLM context for this migration
            )
            
            log_info(f"Successfully migrated {file_path.name}")
            return True
            
        except Exception as e:
            log_error(f"Failed to migrate {file_path}: {str(e)}")
            return False
    
    def migrate_directory(self, directory: str, category: str) -> Dict[str, Any]:
        """Migrate all files in a directory."""
        log_info(f"Starting migration of {directory} directory")
        
        files = self.get_files_to_migrate(directory)
        results = {
            "total_files": len(files),
            "successful": 0,
            "failed": 0,
            "failed_files": []
        }
        
        for file_path in files:
            if self.migrate_file(file_path, category):
                results["successful"] += 1
            else:
                results["failed"] += 1
                results["failed_files"].append(str(file_path))
        
        log_info(f"Migration complete for {directory}: {results['successful']}/{results['total_files']} successful")
        return results
    
    def get_migration_stats(self) -> Dict[str, Any]:
        """Get statistics about the migration."""
        return self.client.get_collection_stats()
    
    def clear_migration(self):
        """Clear all migrated data (for testing)."""
        log_warning("Clearing migration data")
        self.client.clear_collection()


def main():
    """Main migration function."""
    print("File Migration to Supabase")
    print("=" * 50)
    
    # Initialize migrator
    migrator = FileMigrator()
    
    # Get initial stats
    initial_stats = migrator.get_migration_stats()
    log_info(f"Initial collection stats: {initial_stats}")
    
    # Ask user for confirmation
    print(f"\nThis will migrate files from:")
    print(f"- data/va_notes (category: va_notes)")
    print(f"- data/meeting_notes (category: meeting_notes)")
    print(f"\nTo Supabase collection: {migrator.collection_name}")
    
    if initial_stats["count"] > 0:
        print(f"\nWarning: Collection already contains {initial_stats['count']} documents")
        response = input("Clear existing data? (y/N): ").lower()
        if response == 'y':
            migrator.clear_migration()
    
    response = input("\nProceed with migration? (y/N): ").lower()
    if response != 'y':
        print("Migration cancelled")
        return
    
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


if __name__ == "__main__":
    main()