#!/usr/bin/env python3
"""Map all existing documents to the default user (huynguyenvt1989@gmail.com)."""

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


def get_supabase_client() -> Client:
    """Get Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    
    return create_client(url, key)


def get_default_user_id(client: Client) -> str:
    """Get the default user ID for huynguyenvt1989@gmail.com."""
    try:
        # Check if we have an auth table or users table
        # First try the auth.users table (standard Supabase auth)
        result = client.rpc("get_user_by_email", {"email": "huynguyenvt1989@gmail.com"}).execute()
        
        if result.data:
            return result.data[0]["id"]
        
        # If that doesn't work, check if there's a custom users table
        users_result = client.table("users").select("user_id").eq("email", "huynguyenvt1989@gmail.com").execute()
        
        if users_result.data:
            return users_result.data[0]["user_id"]
        
        # If no user found, create a default UUID for this user
        # This is a fallback - ideally the user should exist in auth
        default_user_id = "34ed3b47-3198-43bd-91df-b2a389ad82aa"  # Fixed UUID for consistency
        log_info(f"Using default user ID: {default_user_id}")
        return default_user_id
        
    except Exception as e:
        log_error(f"Error getting user ID: {e}")
        # Return a consistent default UUID
        default_user_id = "34ed3b47-3198-43bd-91df-b2a389ad82aa"
        log_info(f"Using fallback user ID: {default_user_id}")
        return default_user_id


def map_documents_to_user():
    """Map all existing documents to the default user."""
    print("Mapping Existing Documents to Default User")
    print("=" * 50)
    
    try:
        # Initialize Supabase client
        client = get_supabase_client()
        
        # Get default user ID
        user_id = get_default_user_id(client)
        print(f"Default user ID: {user_id}")
        
        # Get all documents with NULL user_id
        null_docs = client.table("document_embeddings").select("id, collection_name, document_id, metadata").is_("user_id", "null").execute()
        
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
        
        # Confirm with user
        response = input(f"\nMap all {len(null_docs.data)} documents to user {user_id}? (y/N): ").lower()
        if response != 'y':
            print("Operation cancelled")
            return
        
        # Update documents in batches
        batch_size = 100
        total_updated = 0
        
        for i in range(0, len(null_docs.data), batch_size):
            batch = null_docs.data[i:i + batch_size]
            doc_ids = [doc["id"] for doc in batch]
            
            # Update batch
            result = client.table("document_embeddings").update({"user_id": user_id}).in_("id", doc_ids).execute()
            
            if result.data:
                total_updated += len(result.data)
                print(f"Updated batch {i//batch_size + 1}: {len(result.data)} documents")
            else:
                log_error(f"Failed to update batch {i//batch_size + 1}")
        
        print(f"\n✅ Successfully updated {total_updated} documents")
        
        # Verify the update
        remaining_null = client.table("document_embeddings").select("id", count="exact").is_("user_id", "null").execute()
        print(f"Remaining documents with NULL user_id: {remaining_null.count}")
        
        # Show updated counts by collection
        print("\nUpdated documents by collection:")
        for collection in collections.keys():
            count = client.table("document_embeddings").select("id", count="exact").eq("collection_name", collection).eq("user_id", user_id).execute()
            print(f"  - {collection}: {count.count} documents for user {user_id}")
        
    except Exception as e:
        log_error(f"Error mapping documents: {str(e)}")
        raise


def verify_user_mapping():
    """Verify that documents are properly mapped to users."""
    print("\n" + "=" * 50)
    print("Verifying User Mapping")
    print("=" * 50)
    
    try:
        client = get_supabase_client()
        user_id = get_default_user_id(client)
        
        # Get counts by user_id
        all_docs = client.table("document_embeddings").select("user_id, collection_name", count="exact").execute()
        user_docs = client.table("document_embeddings").select("id", count="exact").eq("user_id", user_id).execute()
        null_docs = client.table("document_embeddings").select("id", count="exact").is_("user_id", "null").execute()
        
        print(f"Total documents: {all_docs.count}")
        print(f"Documents for user {user_id}: {user_docs.count}")
        print(f"Documents with NULL user_id: {null_docs.count}")
        
        # Show breakdown by collection for the user
        collections = ["documents", "file_migration", "knowledge_base", "default"]
        print(f"\nDocuments for user {user_id} by collection:")
        for collection in collections:
            count = client.table("document_embeddings").select("id", count="exact").eq("collection_name", collection).eq("user_id", user_id).execute()
            if count.count > 0:
                print(f"  - {collection}: {count.count} documents")
        
    except Exception as e:
        log_error(f"Error verifying mapping: {str(e)}")


def main():
    """Main function."""
    try:
        # Map documents to user
        map_documents_to_user()
        
        # Verify the mapping
        verify_user_mapping()
        
        print("\n🎉 Document mapping completed successfully!")
        
    except Exception as e:
        log_error(f"Migration failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())