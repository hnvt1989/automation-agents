#!/usr/bin/env python3
"""Migrate existing chunked documents to full document storage."""

import os
import sys
import uuid
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.storage.supabase_vector import SupabaseVectorClient
from src.storage.document_storage import DocumentStorage
from src.utils.logging import log_info, log_error, log_warning


def migrate_documents():
    """Migrate existing documents from embeddings to full document storage."""
    
    document_types = {
        'document': 'documents',
        'note': 'notes', 
        'memo': 'memos',
        'interview': 'interviews'
    }
    
    storage = DocumentStorage()
    
    if not storage.tables_available:
        print("❌ Document storage tables not available. Please create them first.")
        return False
    
    total_migrated = 0
    total_errors = 0
    
    for doc_type, collection_name in document_types.items():
        print(f"\n📄 Migrating {doc_type}s from collection '{collection_name}'...")
        
        try:
            # Initialize vector client for this collection
            client = SupabaseVectorClient(collection_name=collection_name, enable_contextual=True)
            
            # Get all documents from this collection
            results = client.query(
                query_texts=['document content'],
                n_results=1000,  # Get more results
                where=None
            )
            
            if not results['ids'] or not results['ids'][0]:
                print(f"  No documents found in {collection_name}")
                continue
            
            # Group by document name to reconstruct full documents
            documents_by_name = {}
            
            for i, doc_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i] if results['metadatas'][0] else {}
                content = results['documents'][0][i] if results['documents'][0] else ""
                
                doc_name = metadata.get('name', 'Untitled')
                
                # Skip empty or invalid documents
                if not doc_name or doc_name == 'Untitled' or not content.strip():
                    continue
                
                if doc_name not in documents_by_name:
                    documents_by_name[doc_name] = {
                        'id': str(uuid.uuid4()),
                        'name': doc_name,
                        'description': metadata.get('description', ''),
                        'filename': metadata.get('filename', ''),
                        'doc_type': doc_type,
                        'created_at': metadata.get('created_at'),
                        'last_modified': metadata.get('last_modified'),
                        'chunks': [],
                        'metadata': metadata
                    }
                
                # Add this chunk
                chunk_info = {
                    'content': content,
                    'chunk_index': metadata.get('chunk_index', 0),
                    'doc_id': doc_id
                }
                documents_by_name[doc_name]['chunks'].append(chunk_info)
            
            print(f"  Found {len(documents_by_name)} unique documents")
            
            # Migrate each document
            migrated_count = 0
            for doc_name, doc_info in documents_by_name.items():
                try:
                    # Sort chunks by index and combine content
                    chunks = sorted(doc_info['chunks'], key=lambda x: x.get('chunk_index', 0))
                    
                    # Combine chunk content
                    if len(chunks) == 1:
                        # Single chunk - use as-is
                        full_content = chunks[0]['content']
                    else:
                        # Multiple chunks - combine them
                        full_content = '\n\n'.join(chunk['content'] for chunk in chunks)
                    
                    # Skip if content is too short
                    if len(full_content.strip()) < 10:
                        print(f"    ⚠️  Skipping '{doc_name}' - content too short")
                        continue
                    
                    # Create document in new storage
                    result = storage.create_document(
                        document_id=doc_info['id'],
                        name=doc_info['name'],
                        content=full_content,
                        doc_type=doc_type,
                        description=doc_info['description'],
                        metadata={
                            'filename': doc_info['filename'],
                            'created_at': doc_info['created_at'],
                            'last_modified': doc_info['last_modified'],
                            'migrated_from_chunks': True,
                            'original_chunk_count': len(chunks),
                            **{k: v for k, v in doc_info['metadata'].items() 
                               if k not in ['name', 'description', 'filename', 'created_at', 'last_modified']}
                        }
                    )
                    
                    if result['success']:
                        print(f"    ✅ Migrated '{doc_name}' ({len(chunks)} chunks → full document)")
                        migrated_count += 1
                        total_migrated += 1
                    else:
                        print(f"    ❌ Failed to migrate '{doc_name}': {result['error']}")
                        total_errors += 1
                        
                except Exception as e:
                    print(f"    ❌ Error migrating '{doc_name}': {e}")
                    total_errors += 1
            
            print(f"  📊 {doc_type}s: {migrated_count} migrated successfully")
            
        except Exception as e:
            print(f"  ❌ Error processing {collection_name}: {e}")
            total_errors += 1
    
    print(f"\n🎉 Migration Summary:")
    print(f"   ✅ Total documents migrated: {total_migrated}")
    print(f"   ❌ Total errors: {total_errors}")
    
    if total_migrated > 0:
        print(f"\n💡 Next steps:")
        print(f"   1. Test the new document system with the API")
        print(f"   2. Verify documents are viewable/editable")
        print(f"   3. Consider backing up old embeddings before cleanup")
    
    return total_errors == 0


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv(project_root / "local.env")
    
    print("🚀 Starting document migration...")
    success = migrate_documents()
    
    if success:
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration completed with errors.")
    
    sys.exit(0 if success else 1)