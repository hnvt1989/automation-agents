#!/usr/bin/env python3
"""Non-interactive script to map all existing documents to the default user."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv(os.path.join(project_root, 'local.env'))

from src.utils.logging import log_info, log_error


def map_documents_to_user():
    """Map all existing documents to the default user automatically."""
    print("Auto-Mapping Documents to Default User")
    print("=" * 50)
    
    try:
        # Initialize Supabase client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        client = create_client(url, key)
        
        # Use consistent default user ID for huynguyenvt1989@gmail.com
        user_id = "34ed3b47-3198-43bd-91df-b2a389ad82aa"
        print(f"Mapping documents to user: {user_id}")
        
        # Get all documents with NULL user_id
        null_docs = client.table("document_embeddings").select("id, collection_name").is_("user_id", "null").execute()
        
        if not null_docs.data:
            print("✅ No documents found with NULL user_id")
            return
        
        print(f"Found {len(null_docs.data)} documents with NULL user_id")
        
        # Group by collection for reporting
        collections = {}
        for doc in null_docs.data:
            collection = doc["collection_name"]
            if collection not in collections:
                collections[collection] = 0
            collections[collection] += 1
        
        print("\nDocuments by collection:")
        for collection, count in collections.items():
            print(f"  - {collection}: {count} documents")
        
        # Update all documents with NULL user_id
        print(f"\nUpdating {len(null_docs.data)} documents...")
        
        result = client.table("document_embeddings").update({"user_id": user_id}).is_("user_id", "null").execute()
        
        if result.data:
            print(f"✅ Successfully updated {len(result.data)} documents")
        else:
            print("❌ No documents were updated")
        
        # Verify the update
        remaining_null = client.table("document_embeddings").select("id", count="exact").is_("user_id", "null").execute()
        user_docs = client.table("document_embeddings").select("id", count="exact").eq("user_id", user_id).execute()
        
        print(f"\nVerification:")
        print(f"  - Documents with NULL user_id: {remaining_null.count}")
        print(f"  - Documents for user {user_id}: {user_docs.count}")
        
        # Show updated counts by collection
        print("\nUpdated documents by collection:")
        for collection in collections.keys():
            count = client.table("document_embeddings").select("id", count="exact").eq("collection_name", collection).eq("user_id", user_id).execute()
            print(f"  - {collection}: {count.count} documents")
        
        return True
        
    except Exception as e:
        log_error(f"Error mapping documents: {str(e)}")
        return False


def main():
    """Main function."""
    success = map_documents_to_user()
    
    if success:
        print("\n🎉 Document mapping completed successfully!")
        print(f"All documents are now mapped to user: huynguyenvt1989@gmail.com")
        return 0
    else:
        print("\n❌ Document mapping failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())