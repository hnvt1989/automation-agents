#!/usr/bin/env python3
"""Advanced cleanup of migrated document content with better chunk handling."""

import os
import sys
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.storage.document_storage import DocumentStorage


def extract_clean_content(content: str) -> str:
    """Extract clean content from chunked documents with metadata."""
    
    # Pattern to match chunk headers - more comprehensive
    chunk_pattern = r"This chunk is from [^.]+\.\s*(?:Name:[^.]*\.\s*)?(?:Description:[^.]*\.\s*)?(?:Filename:[^.]*\.\s*)?(?:Doc Type:[^.]*\.\s*)?(?:Created At:[^.]*\.\s*)?(?:Last Modified:[^.]*\.\s*)?(?:Original Path:[^.]*\.\s*)?(?:File Size:[^.]*\.\s*)?(?:Original Modified:[^.]*\.\s*)?(?:Part \d+ of \d+\.\s*)?\s*Content:\s*"
    
    # Split by chunk headers
    parts = re.split(chunk_pattern, content, flags=re.IGNORECASE | re.DOTALL)
    
    # Extract content parts (skip first if it's metadata)
    content_parts = []
    for i, part in enumerate(parts):
        if i == 0:
            # First part might be clean content or metadata
            if not part.strip().startswith("This chunk is from"):
                content_parts.append(part.strip())
        else:
            # Subsequent parts are content after "Content:" marker
            if part.strip():
                content_parts.append(part.strip())
    
    # If we didn't find any content parts, try a different approach
    if not content_parts:
        # Look for content after the last "Content:" marker
        content_matches = re.findall(r"Content:\s*(.+?)(?=This chunk is from|$)", content, re.DOTALL | re.IGNORECASE)
        content_parts = [match.strip() for match in content_matches if match.strip()]
    
    # Join all content parts
    if content_parts:
        clean_content = "\n\n".join(content_parts)
    else:
        # Last resort: return original content
        clean_content = content
    
    # Remove user_id comments
    clean_content = re.sub(r"<!--\s*user_id:\s*[^>]+\s*-->", "", clean_content).strip()
    
    # Remove any remaining chunk headers that might be at the end
    clean_content = re.sub(chunk_pattern, "", clean_content, flags=re.IGNORECASE | re.DOTALL).strip()
    
    # Clean up multiple newlines
    clean_content = re.sub(r"\n{3,}", "\n\n", clean_content)
    
    return clean_content


def advanced_cleanup():
    """Perform advanced cleanup of all documents."""
    
    storage = DocumentStorage()
    
    if not storage.tables_available:
        print("❌ Document storage tables not available")
        return False
    
    # Tables to clean up
    tables = ['documents', 'notes', 'memos', 'interviews']
    total_cleaned = 0
    
    for table in tables:
        try:
            print(f"\n📄 Advanced cleaning of {table}...")
            
            # Get all documents from this table
            result = storage.client.table(table).select('*').execute()
            
            if not result.data:
                print(f"  ✅ {table}: No documents to clean")
                continue
            
            print(f"  📊 Found {len(result.data)} documents")
            
            cleaned_count = 0
            for doc in result.data:
                original_content = doc.get('content', '')
                
                # Check if content needs cleaning
                if ('This chunk is from' in original_content or 
                    'Content:' in original_content or
                    '<!-- user_id:' in original_content):
                    
                    cleaned_content = extract_clean_content(original_content)
                    
                    # Only update if content actually changed and is substantial
                    if (cleaned_content != original_content and 
                        len(cleaned_content) > 10 and
                        cleaned_content.strip()):
                        
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
                                
                                # Show before/after for first few documents
                                if cleaned_count <= 2:
                                    print(f"      BEFORE: {repr(original_content[:100])}...")
                                    print(f"      AFTER:  {repr(cleaned_content[:100])}...")
                            else:
                                print(f"    ❌ Failed to update '{doc.get('name', 'Untitled')}'")
                                
                        except Exception as e:
                            print(f"    ❌ Error updating '{doc.get('name', 'Untitled')}': {e}")
                    else:
                        print(f"    ⚠️  '{doc.get('name', 'Untitled')}' - no significant improvement")
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
    
    print("🧹 Starting advanced content cleanup...")
    
    # Test the extraction function
    test_content = """This chunk is from va_notes. Name: Backend Description. Description: VA Notes - Backend Description. Filename: backend_description.md. Doc Type: document. Created At: 2025-07-04T14:29:30.121954. Last Modified: 2025-07-04T14:29:30.121970. Original Path: /Users/hnguyen/Desktop/projects/automation-agents/data/va_notes/backend_description.md. File Size: 13811. Original Modified: 1751650175.1649384. Part 1 of 17. 
Content: <!-- user_id: 34ed3b47-3198-43bd-91df-b2a389ad82aa -->
# Backend API Documentation

This is the actual content we want.

This chunk is from va_notes. Name: Backend Description. Description: VA Notes - Backend Description. Filename: backend_description.md. Doc Type: document. Created At: 2025-07-04T14:29:30.121954. Last Modified: 2025-07-04T14:29:30.121970. Original Path: /Users/hnguyen/Desktop/projects/automation-agents/data/va_notes/backend_description.md. File Size: 13811. Original Modified: 1751650175.1649384. Part 17 of 17. 
Content: s for performance-critical read operations."""
    
    clean_test = extract_clean_content(test_content)
    print(f"\n📋 Test extraction:")
    print(f"BEFORE ({len(test_content)} chars): {repr(test_content[:100])}...")
    print(f"AFTER ({len(clean_test)} chars): {repr(clean_test)}")
    
    print("\n" + "="*50)
    
    success = advanced_cleanup()
    
    if success:
        print("\n✅ Advanced content cleanup completed!")
        print("\n💡 Documents should now be completely clean without any metadata")
    else:
        print("\n❌ Advanced content cleanup failed.")
    
    sys.exit(0 if success else 1)