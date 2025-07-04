#!/usr/bin/env python3
"""Organize development and testing scripts into appropriate folders."""

import os
from pathlib import Path

def organize_scripts():
    """Organize scripts into development and archive folders."""
    scripts_dir = Path(__file__).parent
    
    # Create development folder for scripts that are still useful
    dev_dir = scripts_dir / "development"
    dev_dir.mkdir(exist_ok=True)
    
    # Development scripts to keep organized
    dev_scripts = [
        "debug_indexing.py",
        "debug_search.py", 
        "test_686c_search.py",
        "test_document_manager.py",
        "test_enhanced_rag.py",
        "test_migration.py",
        "verify_enhanced_rag.py",
        "check_indexed_content.py",
        "index_single_file.py",
        "search_686c_improved.py"
    ]
    
    # Archive additional migration scripts that are no longer needed
    archive_dir = scripts_dir / "archive_migration"
    archive_scripts = [
        "migrate_documents_to_supabase.py",
        "migrate_files_to_supabase.py", 
        "migrate_neo4j_to_cloud.py",
        "migrate_to_supabase.py",
        "migrate_user_data.py",
        "run_migration.py",
        "map_documents_to_user.py",
        "run_document_mapping.py",
        "setup_auth.py",
        "setup_default_user.py"
    ]
    
    print("📁 Organizing development scripts...")
    
    # Move development scripts
    moved_dev = 0
    for script in dev_scripts:
        script_path = scripts_dir / script
        if script_path.exists():
            dev_path = dev_dir / script
            script_path.rename(dev_path)
            print(f"  📋 Moved {script} to development/")
            moved_dev += 1
    
    # Move additional migration scripts to archive
    moved_archive = 0
    for script in archive_scripts:
        script_path = scripts_dir / script
        if script_path.exists():
            archive_path = archive_dir / script
            script_path.rename(archive_path)
            print(f"  📦 Moved {script} to archive_migration/")
            moved_archive += 1
    
    print(f"\n✅ Organization complete:")
    print(f"   📋 {moved_dev} scripts moved to development/")
    print(f"   📦 {moved_archive} scripts moved to archive_migration/")
    
    # Show what's left in scripts root
    remaining = [f for f in scripts_dir.iterdir() 
                if f.is_file() and f.suffix in ['.py', '.sql', '.sh', '.txt']]
    
    print(f"\n📂 Scripts remaining in root:")
    for script in sorted(remaining):
        print(f"   • {script.name}")

if __name__ == "__main__":
    organize_scripts()