#!/usr/bin/env python3
"""Final aggressive cleanup to remove all remaining chunk metadata."""

import os
import sys
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.storage.document_storage import DocumentStorage


def final_clean_content(content: str) -> str:
    """Aggressively remove all chunk metadata and extract only clean content."""
    
    # Step 1: Split on chunk headers and extract content parts
    # This pattern matches the full chunk header including the trailing "Content: "
    chunk_header_pattern = r"This chunk is from [^.]+\..*?Part \d+ of \d+\.\s*Content:\s*"
    
    # Split by chunk headers
    parts = re.split(chunk_header_pattern, content, flags=re.DOTALL | re.IGNORECASE)
    
    content_parts = []
    for i, part in enumerate(parts):
        if i == 0:
            # First part might be clean content (if document doesn't start with chunk header)
            clean_part = part.strip()
            if clean_part and not clean_part.startswith("This chunk is from"):
                content_parts.append(clean_part)
        else:
            # Subsequent parts are content after "Content:" marker
            clean_part = part.strip()
            if clean_part:
                content_parts.append(clean_part)
    
    # Step 2: If we still have no content, try more aggressive extraction
    if not content_parts:
        # Find all content after "Content:" markers
        content_matches = re.findall(r"Content:\s*(.+?)(?=\n\nThis chunk is from|\Z)", content, re.DOTALL | re.IGNORECASE)
        content_parts = [match.strip() for match in content_matches if match.strip()]
    
    # Step 3: Join content parts
    if content_parts:
        combined_content = "\n\n".join(content_parts)
    else:
        combined_content = content
    
    # Step 4: Final cleanup - remove any remaining chunk headers
    # Remove any remaining "This chunk is from..." lines
    combined_content = re.sub(r"This chunk is from[^\n]*\n", "", combined_content, flags=re.IGNORECASE)
    combined_content = re.sub(r"Name:[^\n]*\n", "", combined_content, flags=re.IGNORECASE)
    combined_content = re.sub(r"Description:[^\n]*\n", "", combined_content, flags=re.IGNORECASE)
    combined_content = re.sub(r"Filename:[^\n]*\n", "", combined_content, flags=re.IGNORECASE)
    combined_content = re.sub(r"Doc Type:[^\n]*\n", "", combined_content, flags=re.IGNORECASE)
    combined_content = re.sub(r"Created At:[^\n]*\n", "", combined_content, flags=re.IGNORECASE)
    combined_content = re.sub(r"Last Modified:[^\n]*\n", "", combined_content, flags=re.IGNORECASE)
    combined_content = re.sub(r"Original Path:[^\n]*\n", "", combined_content, flags=re.IGNORECASE)
    combined_content = re.sub(r"File Size:[^\n]*\n", "", combined_content, flags=re.IGNORECASE)
    combined_content = re.sub(r"Original Modified:[^\n]*\n", "", combined_content, flags=re.IGNORECASE)
    combined_content = re.sub(r"Part \d+ of \d+\.\s*\n", "", combined_content, flags=re.IGNORECASE)
    combined_content = re.sub(r"Content:\s*\n", "", combined_content, flags=re.IGNORECASE)
    
    # Remove user_id comments
    combined_content = re.sub(r"<!--\s*user_id:\s*[^>]+\s*-->", "", combined_content)
    
    # Clean up extra whitespace
    combined_content = re.sub(r"\n{3,}", "\n\n", combined_content)
    combined_content = combined_content.strip()
    
    return combined_content


def final_cleanup():
    """Perform final aggressive cleanup of all documents."""
    
    storage = DocumentStorage()
    
    if not storage.tables_available:
        print("❌ Document storage tables not available")
        return False
    
    # Tables to clean up
    tables = ['documents', 'notes', 'memos', 'interviews']
    total_cleaned = 0
    
    for table in tables:
        try:
            print(f"\n📄 Final cleanup of {table}...")
            
            # Get all documents from this table
            result = storage.client.table(table).select('*').execute()
            
            if not result.data:
                print(f"  ✅ {table}: No documents to clean")
                continue
            
            print(f"  📊 Found {len(result.data)} documents")
            
            cleaned_count = 0
            for doc in result.data:
                original_content = doc.get('content', '')
                
                # Check if content has chunk metadata
                if 'This chunk is from' in original_content:
                    
                    cleaned_content = final_clean_content(original_content)
                    
                    # Only update if content actually changed and is substantial
                    if (cleaned_content != original_content and 
                        len(cleaned_content) > 10 and
                        'This chunk is from' not in cleaned_content):
                        
                        try:
                            # Update the document with clean content
                            update_result = storage.client.table(table).update({
                                'content': cleaned_content,
                                'updated_at': 'now()'
                            }).eq('id', doc['id']).execute()
                            
                            if update_result.data:
                                before_chunks = original_content.count('This chunk is from')
                                after_chunks = cleaned_content.count('This chunk is from')
                                print(f"    ✅ Cleaned '{doc.get('name', 'Untitled')}' ({len(original_content)} → {len(cleaned_content)} chars, {before_chunks} → {after_chunks} chunks)")
                                cleaned_count += 1
                                total_cleaned += 1
                                
                                # Show sample for first document
                                if cleaned_count == 1:
                                    print(f"      SAMPLE BEFORE: {repr(original_content[-200:])}")
                                    print(f"      SAMPLE AFTER:  {repr(cleaned_content[-200:])}")
                            else:
                                print(f"    ❌ Failed to update '{doc.get('name', 'Untitled')}'")
                                
                        except Exception as e:
                            print(f"    ❌ Error updating '{doc.get('name', 'Untitled')}': {e}")
                    else:
                        print(f"    ⚠️  '{doc.get('name', 'Untitled')}' - cleanup didn't help")
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
    
    print("🧹 Starting FINAL content cleanup...")
    
    # Test with the problematic content
    test_content = """performance-critical read operations.

This chunk is from va_notes. Name: Backend Description. Description: VA Notes - Backend Description. Filename: backend_description.md. Doc Type: document. Created At: 2025-07-04T14:29:30.121954. Last Modified: 2025-07-04T14:29:30.121970. Original Path: /Users/hnguyen/Desktop/projects/automation-agents/data/va_notes/backend_description.md. File Size: 13811. Original Modified: 1751650175.1649384. Part 17 of 17. 
Content: s for performance-critical read operations."""
    
    clean_result = final_clean_content(test_content)
    print(f"\n📋 Test cleanup:")
    print(f"BEFORE: {repr(test_content)}")
    print(f"AFTER: {repr(clean_result)}")
    print(f"Chunks before: {test_content.count('This chunk is from')}")
    print(f"Chunks after: {clean_result.count('This chunk is from')}")
    
    print("\n" + "="*50)
    
    success = final_cleanup()
    
    if success:
        print("\n✅ FINAL content cleanup completed!")
        print("\n💡 Documents should now be 100% clean")
    else:
        print("\n❌ Final content cleanup failed.")
    
    sys.exit(0 if success else 1)