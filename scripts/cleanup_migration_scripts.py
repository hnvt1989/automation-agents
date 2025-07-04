#!/usr/bin/env python3
"""Clean up temporary migration scripts that are no longer needed."""

import os
from pathlib import Path

# Migration scripts that can be safely removed
MIGRATION_SCRIPTS = [
    "advanced_cleanup.py",
    "cleanup_document_content.py", 
    "final_cleanup.py",
    "assign_documents_to_user.py",
    "create_tables_simple.py",
    "init_document_storage.py",
    "migrate_to_full_documents.py",
    "fix_table_schemas.sql",
    "add_missing_columns.py"
]

def cleanup_scripts():
    """Move migration scripts to an archive folder."""
    scripts_dir = Path(__file__).parent
    archive_dir = scripts_dir / "archive_migration"
    archive_dir.mkdir(exist_ok=True)
    
    print("🧹 Cleaning up migration scripts...")
    
    moved_count = 0
    for script in MIGRATION_SCRIPTS:
        script_path = scripts_dir / script
        if script_path.exists():
            archive_path = archive_dir / script
            script_path.rename(archive_path)
            print(f"  ✅ Moved {script} to archive/")
            moved_count += 1
        else:
            print(f"  ⚠️  {script} not found")
    
    print(f"\n📦 Archived {moved_count} migration scripts")
    print(f"📂 Scripts moved to: {archive_dir}")
    
    return moved_count > 0

if __name__ == "__main__":
    cleanup_scripts()