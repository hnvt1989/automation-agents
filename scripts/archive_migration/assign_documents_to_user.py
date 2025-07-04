#!/usr/bin/env python3
"""Assign all documents to the default user."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.storage.document_storage import DocumentStorage
from src.storage.auth_storage import AuthStorage


def assign_documents_to_user():
    """Assign all documents to the default user."""
    
    # Get the default user
    auth = AuthStorage()
    users_result = auth.client.table('users').select('id, email').execute()
    
    if not users_result.data:
        print("❌ No users found in the database")
        return False
    
    default_user = users_result.data[0]
    user_id = default_user['id']
    user_email = default_user['email']
    
    print(f"📋 Assigning all documents to user: {user_email} (ID: {user_id})")
    
    storage = DocumentStorage()
    
    if not storage.tables_available:
        print("❌ Document storage tables not available")
        return False
    
    # Tables to update
    tables = ['documents', 'notes', 'memos', 'interviews']
    total_updated = 0
    
    for table in tables:
        try:
            print(f"\n📄 Updating {table}...")
            
            # Get count of NULL user_id records
            count_result = storage.client.table(table).select('id').is_('user_id', 'null').execute()
            null_count = len(count_result.data)
            
            if null_count == 0:
                print(f"  ✅ {table}: All records already have user_id assigned")
                continue
            
            print(f"  📊 Found {null_count} records with NULL user_id")
            
            # Update all NULL user_id records to the default user
            update_result = storage.client.table(table).update({
                'user_id': user_id
            }).is_('user_id', 'null').execute()
            
            updated_count = len(update_result.data) if update_result.data else 0
            print(f"  ✅ Updated {updated_count} records in {table}")
            total_updated += updated_count
            
        except Exception as e:
            print(f"  ❌ Error updating {table}: {e}")
    
    print(f"\n🎉 Summary:")
    print(f"   ✅ Total records updated: {total_updated}")
    print(f"   👤 All documents now belong to: {user_email}")
    
    return True


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv(project_root / "local.env")
    
    print("🚀 Starting user assignment...")
    success = assign_documents_to_user()
    
    if success:
        print("\n✅ User assignment completed!")
        print("\n💡 You can now test the API endpoints - documents should be visible")
    else:
        print("\n❌ User assignment failed.")
    
    sys.exit(0 if success else 1)