#!/usr/bin/env python3
"""Clean up migrated document content by removing chunk metadata."""

import os
import sys
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.storage.document_storage import DocumentStorage


def clean_content(content: str) -> str:
    """Remove chunk metadata from content and extract clean document text."""
    
    # Pattern to match chunk headers like:
    # "This chunk is from va_notes. Name: ... Part X of Y.\nContent: "
    chunk_header_pattern = r"This chunk is from [^.]+\.\s*(?:Name:[^.]+\.\s*)?(?:Description:[^.]+\.\s*)?(?:Filename:[^.]+\.\s*)?(?:Doc Type:[^.]+\.\s*)?(?:Created At:[^.]+\.\s*)?(?:Last Modified:[^.]+\.\s*)?(?:Original Path:[^.]+\.\s*)?(?:File Size:[^.]+\.\s*)?(?:Original Modified:[^.]+\.\s*)?(?:Part \d+ of \d+\.\s*)?\s*Content:\s*"
    
    # Split content by chunk headers and extract just the content parts
    parts = re.split(chunk_header_pattern, content, flags=re.IGNORECASE | re.DOTALL)
    
    # The first part might be empty or contain initial metadata, subsequent parts are content
    clean_parts = []
    for i, part in enumerate(parts):
        if i == 0 and part.strip().startswith("This chunk is from"):
            # Skip the first metadata part
            continue
        elif part.strip():
            clean_parts.append(part.strip())
    
    # Join all content parts
    if clean_parts:
        clean_content = "\n\n".join(clean_parts)
    else:
        # Fallback: try to extract content after "Content:" marker
        content_match = re.search(r"Content:\s*(.+)", content, re.DOTALL | re.IGNORECASE)
        if content_match:
            clean_content = content_match.group(1).strip()
        else:
            # Last resort: return original content
            clean_content = content
    
    # Remove any remaining user_id comments
    clean_content = re.sub(r"<!--\s*user_id:\s*[^>]+\s*-->", "", clean_content).strip()
    
    return clean_content


def cleanup_documents():
    """Clean up all migrated documents."""
    
    storage = DocumentStorage()
    
    if not storage.tables_available:
        print("❌ Document storage tables not available")
        return False
    
    # Tables to clean up
    tables = ['documents', 'notes', 'memos', 'interviews']
    total_cleaned = 0
    
    for table in tables:
        try:
            print(f"\n📄 Cleaning up {table}...")
            
            # Get all documents from this table
            result = storage.client.table(table).select('*').execute()
            
            if not result.data:
                print(f"  ✅ {table}: No documents to clean")
                continue
            
            print(f"  📊 Found {len(result.data)} documents")
            
            cleaned_count = 0
            for doc in result.data:
                original_content = doc.get('content', '')
                
                # Check if content needs cleaning (has chunk metadata)
                if 'This chunk is from' in original_content or 'Content:' in original_content:
                    cleaned_content = clean_content(original_content)
                    
                    # Only update if content actually changed
                    if cleaned_content != original_content and len(cleaned_content) > 10:
                        try:
                            # Update the document with clean content
                            update_result = storage.client.table(table).update({
                                'content': cleaned_content,
                                'updated_at': 'now()'
                            }).eq('id', doc['id']).execute()
                            
                            if update_result.data:
                                print(f"    ✅ Cleaned '{doc.get('name', 'Untitled')}' ({len(original_content)} → {len(cleaned_content)} chars)")
                                cleaned_count += 1
                                total_cleaned += 1
                            else:
                                print(f"    ❌ Failed to update '{doc.get('name', 'Untitled')}'")
                                
                        except Exception as e:
                            print(f"    ❌ Error updating '{doc.get('name', 'Untitled')}': {e}")
                    else:
                        print(f"    ⚠️  '{doc.get('name', 'Untitled')}' - no significant content after cleaning")
                else:
                    print(f"    ✅ '{doc.get('name', 'Untitled')}' already clean")
            
            print(f"  📊 {table}: {cleaned_count} documents cleaned")
            
        except Exception as e:
            print(f"  ❌ Error processing {table}: {e}")
    
    print(f"\n🎉 Summary:")
    print(f"   ✅ Total documents cleaned: {total_cleaned}")
    
    return True


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv(project_root / "local.env")
    
    print("🧹 Starting content cleanup...")
    
    # Show example of what we're cleaning
    print("\n📋 Example of content that will be cleaned:")
    sample_dirty = """This chunk is from va_notes. Name: Test Doc. Description: Test. Filename: test.md. Doc Type: document. Created At: 2025-07-04T14:29:22.622186. Part 1 of 2. 
Content: <!-- user_id: 123 -->
# Actual Document Title

This is the real content we want to keep."""
    
    sample_clean = clean_content(sample_dirty)
    print("BEFORE:", repr(sample_dirty[:100] + "..."))
    print("AFTER:", repr(sample_clean[:100] + "..."))
    
    print("\n" + "="*50)
    
    success = cleanup_documents()
    
    if success:
        print("\n✅ Content cleanup completed!")
        print("\n💡 Documents should now show clean content without metadata headers")
    else:
        print("\n❌ Content cleanup failed.")
    
    sys.exit(0 if success else 1)