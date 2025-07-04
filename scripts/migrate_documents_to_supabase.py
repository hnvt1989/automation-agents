#!/usr/bin/env python3
"""Migration script to move existing documents to Supabase vector storage.

This script migrates:
- Documents from data/va_notes/ 
- Notes from data/meeting_notes/
- Memos from data/memos/
- Interviews from data/interviews/
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from storage.document_manager import DocumentManager
from storage.auth_storage import AuthStorage
from utils.logging import log_info, log_error, log_warning


def load_markdown_file(file_path: Path) -> str:
    """Load content from a markdown file."""
    try:
        return file_path.read_text(encoding='utf-8')
    except Exception as e:
        log_error(f"Failed to read {file_path}: {str(e)}")
        return ""


def load_yaml_file(file_path: Path) -> Dict[str, Any]:
    """Load content from a YAML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        log_error(f"Failed to read {file_path}: {str(e)}")
        return {}


def migrate_documents(doc_manager: DocumentManager, base_dir: Path):
    """Migrate documents from data/va_notes/."""
    va_notes_dir = base_dir / "data" / "va_notes"
    
    if not va_notes_dir.exists():
        log_warning(f"Documents directory not found: {va_notes_dir}")
        return
    
    log_info(f"Migrating documents from {va_notes_dir}")
    
    for file_path in va_notes_dir.glob("*.md"):
        try:
            content = load_markdown_file(file_path)
            if not content:
                continue
            
            name = file_path.stem.replace("_", " ").replace("-", " ").title()
            filename = file_path.name
            
            doc_id = doc_manager.add_document(
                content=content,
                name=name,
                doc_type="document",
                description=f"VA Notes - {name}",
                filename=filename,
                metadata={
                    "original_path": str(file_path),
                    "source": "va_notes",
                    "file_size": file_path.stat().st_size,
                    "original_modified": file_path.stat().st_mtime
                }
            )
            
            log_info(f"Migrated document: {name} -> {doc_id}")
            
        except Exception as e:
            log_error(f"Failed to migrate document {file_path}: {str(e)}")


def migrate_notes(doc_manager: DocumentManager, base_dir: Path):
    """Migrate notes from data/meeting_notes/."""
    meeting_notes_dir = base_dir / "data" / "meeting_notes"
    
    if not meeting_notes_dir.exists():
        log_warning(f"Notes directory not found: {meeting_notes_dir}")
        return
    
    log_info(f"Migrating notes from {meeting_notes_dir}")
    
    # Recursively find all markdown files
    for file_path in meeting_notes_dir.rglob("*.md"):
        try:
            content = load_markdown_file(file_path)
            if not content:
                continue
            
            # Create name from relative path
            relative_path = file_path.relative_to(meeting_notes_dir)
            name_parts = []
            
            # Add subdirectory to name if exists
            if relative_path.parent != Path("."):
                name_parts.append(str(relative_path.parent).replace("/", " - "))
            
            # Add filename
            name_parts.append(file_path.stem.replace("_", " ").replace("-", " ").title())
            
            name = " | ".join(name_parts)
            filename = file_path.name
            
            doc_id = doc_manager.add_document(
                content=content,
                name=name,
                doc_type="note",
                description=f"Meeting Notes - {name}",
                filename=filename,
                metadata={
                    "original_path": str(file_path),
                    "relative_path": str(relative_path),
                    "source": "meeting_notes",
                    "subdirectory": str(relative_path.parent) if relative_path.parent != Path(".") else None,
                    "file_size": file_path.stat().st_size,
                    "original_modified": file_path.stat().st_mtime
                }
            )
            
            log_info(f"Migrated note: {name} -> {doc_id}")
            
        except Exception as e:
            log_error(f"Failed to migrate note {file_path}: {str(e)}")


def migrate_memos(doc_manager: DocumentManager, base_dir: Path):
    """Migrate memos from data/memos/."""
    memos_dir = base_dir / "data" / "memos"
    
    if not memos_dir.exists():
        log_warning(f"Memos directory not found: {memos_dir}")
        return
    
    log_info(f"Migrating memos from {memos_dir}")
    
    for file_path in memos_dir.glob("*.md"):
        try:
            content = load_markdown_file(file_path)
            if not content:
                continue
            
            name = file_path.stem.replace("_", " ").replace("-", " ").title()
            filename = file_path.name
            
            doc_id = doc_manager.add_document(
                content=content,
                name=name,
                doc_type="memo",
                description=f"Memo - {name}",
                filename=filename,
                metadata={
                    "original_path": str(file_path),
                    "source": "memos",
                    "file_size": file_path.stat().st_size,
                    "original_modified": file_path.stat().st_mtime
                }
            )
            
            log_info(f"Migrated memo: {name} -> {doc_id}")
            
        except Exception as e:
            log_error(f"Failed to migrate memo {file_path}: {str(e)}")


def migrate_interviews(doc_manager: DocumentManager, base_dir: Path):
    """Migrate interviews from data/interviews/."""
    interviews_dir = base_dir / "data" / "interviews"
    
    if not interviews_dir.exists():
        log_warning(f"Interviews directory not found: {interviews_dir}")
        return
    
    log_info(f"Migrating interviews from {interviews_dir}")
    
    for file_path in interviews_dir.glob("*.yaml"):
        try:
            interview_data = load_yaml_file(file_path)
            if not interview_data:
                continue
            
            # Convert YAML interview data to document content
            name = interview_data.get("name", file_path.stem.replace("_", " ").title())
            description = interview_data.get("description", "")
            notes = interview_data.get("notes", "")
            status = interview_data.get("status", "pending")
            priority = interview_data.get("priority", "medium")
            
            # Create content from interview data
            content = f"# {name}\n\n"
            if description:
                content += f"**Description:** {description}\n\n"
            content += f"**Status:** {status}\n"
            content += f"**Priority:** {priority}\n\n"
            if notes:
                content += f"## Notes\n\n{notes}\n"
            
            doc_id = doc_manager.add_document(
                content=content,
                name=name,
                doc_type="interview",
                description=description or f"Interview - {name}",
                filename=file_path.name,
                metadata={
                    "original_path": str(file_path),
                    "source": "interviews",
                    "status": status,
                    "priority": priority,
                    "original_notes": notes,
                    "file_size": file_path.stat().st_size,
                    "original_modified": file_path.stat().st_mtime
                }
            )
            
            log_info(f"Migrated interview: {name} -> {doc_id}")
            
        except Exception as e:
            log_error(f"Failed to migrate interview {file_path}: {str(e)}")


def main():
    """Main migration function."""
    base_dir = Path(__file__).parent.parent
    
    log_info("Starting document migration to Supabase")
    
    # Initialize auth storage and get default user
    auth_storage = AuthStorage()
    
    # Try to get or create default user
    try:
        # Try to create default user (will succeed if not exists)
        result = auth_storage.create_default_user("huynguyenvt1989@gmail.com", "Vungtau1989")
        if result["success"]:
            user_id = result["user"]["id"]
            log_info(f"Using default user: {user_id}")
        else:
            # Try to login if user already exists
            login_result = auth_storage.login_user("huynguyenvt1989@gmail.com", "Vungtau1989")
            if login_result["success"]:
                user_id = login_result["user"]["id"]
                log_info(f"Logged in as default user: {user_id}")
            else:
                log_error("Failed to get default user")
                return
    except Exception as e:
        log_error(f"Failed to setup default user: {str(e)}")
        return
    
    # Initialize document manager
    doc_manager = DocumentManager(user_id=user_id)
    
    # Get initial stats
    initial_stats = doc_manager.get_collection_stats()
    log_info(f"Initial collection stats: {initial_stats}")
    
    # Perform migrations
    try:
        migrate_documents(doc_manager, base_dir)
        migrate_notes(doc_manager, base_dir)
        migrate_memos(doc_manager, base_dir)
        migrate_interviews(doc_manager, base_dir)
        
        # Get final stats
        final_stats = doc_manager.get_collection_stats()
        log_info(f"Final collection stats: {final_stats}")
        
        log_info("Document migration completed successfully")
        
    except Exception as e:
        log_error(f"Migration failed: {str(e)}")


if __name__ == "__main__":
    main()