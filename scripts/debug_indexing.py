#!/usr/bin/env python3
"""Debug why dmt_release_process.md is not being indexed."""

import os
import sys
import hashlib
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

def debug_indexing():
    """Debug the indexing process."""
    load_dotenv("local.env")
    
    print("Debugging Indexing Process...")
    print("=" * 70)
    
    # Check the file
    file_path = Path("data/va_notes/dmt_release_process.md")
    if not file_path.is_absolute():
        file_path = project_root / file_path
    
    print(f"\n1. File Check:")
    print(f"   Path: {file_path}")
    print(f"   Exists: {file_path.exists()}")
    print(f"   Size: {file_path.stat().st_size if file_path.exists() else 'N/A'} bytes")
    
    if file_path.exists():
        # Read content
        content = file_path.read_text(encoding='utf-8')
        print(f"   Content length: {len(content)} characters")
        print(f"   First 200 chars: {content[:200]}...")
        
        # Generate document ID (same as indexer)
        doc_id = hashlib.md5(str(file_path).encode()).hexdigest()
        print(f"\n   Expected document ID: {doc_id}")
        print(f"   Expected chunk IDs: {doc_id}_chunk_0, {doc_id}_chunk_1, etc.")
    
    # Check what files the indexer would find
    print(f"\n2. Directory Scan Test:")
    va_notes_dir = project_root / "data" / "va_notes"
    
    # List all .md files
    md_files = list(va_notes_dir.glob("*.md"))
    print(f"   Total .md files in {va_notes_dir}: {len(md_files)}")
    
    # Check if our file is in the list
    target_file = va_notes_dir / "dmt_release_process.md"
    if target_file in md_files:
        print(f"   ✓ dmt_release_process.md is in the file list")
    else:
        print(f"   ✗ dmt_release_process.md is NOT in the file list!")
    
    # Show all files
    print("\n   All .md files found:")
    for f in sorted(md_files):
        print(f"     - {f.name}")
    
    # Test the indexing process manually
    print(f"\n3. Manual Indexing Test:")
    
    try:
        from src.storage.contextual_chunker import ContextualChunker
        from src.core.constants import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
        
        chunker = ContextualChunker()
        
        # Read the file
        content = file_path.read_text(encoding='utf-8')
        
        # Create chunks
        chunks = chunker.create_contextual_chunks(
            content,
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP,
            context_info={
                'source_type': 'knowledge_base',
                'filename': file_path.name,
                'category': 'va_note',
                'document_type': '.md',
                'title': 'DMT Release Process'
            },
            use_llm_context=False
        )
        
        print(f"   Successfully created {len(chunks)} chunks")
        
        # Show first chunk that should contain "initial BGS validation"
        for i, chunk in enumerate(chunks):
            if "initial BGS validation" in chunk.contextual_text.lower():
                print(f"\n   ✓ Found 'initial BGS validation' in chunk {i}:")
                print(f"     {chunk.contextual_text[:300]}...")
                break
                
    except Exception as e:
        print(f"   ✗ Chunking failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Check if file is being skipped
    print(f"\n4. Checking for Skip Conditions:")
    
    # Check if it might be seen as already indexed
    from src.storage.supabase_client import get_supabase_client
    client = get_supabase_client()
    
    doc_id = hashlib.md5(str(file_path).encode()).hexdigest()
    chunk_id = f"{doc_id}_chunk_0"
    
    result = client.client.table("document_embeddings") \
        .select("document_id") \
        .eq("collection_name", "documents") \
        .eq("document_id", chunk_id) \
        .execute()
    
    if result.data:
        print(f"   ✗ File is marked as already indexed (found {chunk_id})")
        print(f"     This is why --force isn't working!")
    else:
        print(f"   ✓ File is not marked as indexed")
    
    # Check for any error patterns
    print(f"\n5. Testing File Processing:")
    
    # Check encoding
    try:
        content = file_path.read_text(encoding='utf-8')
        print(f"   ✓ UTF-8 encoding OK")
    except Exception as e:
        print(f"   ✗ Encoding error: {e}")
    
    # Check for special characters
    if '\x00' in content:
        print(f"   ✗ File contains null bytes")
    else:
        print(f"   ✓ No null bytes found")

if __name__ == "__main__":
    debug_indexing()