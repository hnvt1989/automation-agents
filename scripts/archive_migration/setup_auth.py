#!/usr/bin/env python3
"""Setup authentication database schema and create default user."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from dotenv import load_dotenv
from src.storage.auth_storage import AuthStorage, USER_AUTH_SCHEMA
from supabase import create_client

def setup_database_schema():
    """Set up the database schema for authentication."""
    print("Setting up database schema...")
    
    # Load environment variables
    env_file = project_root / "local.env"
    load_dotenv(env_file)
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in local.env")
        return False
    
    try:
        client = create_client(supabase_url, supabase_key)
        
        # Execute the schema SQL
        # Note: We'll need to run this manually in Supabase SQL editor
        # as the Python client doesn't support executing arbitrary SQL
        print("\nDatabase schema SQL:")
        print("=" * 50)
        print(USER_AUTH_SCHEMA)
        print("=" * 50)
        print("\nIMPORTANT: Please copy and run the above SQL in your Supabase SQL editor.")
        print("After that, run this script again to create the default user.")
        
        return True
    except Exception as e:
        print(f"Error setting up schema: {e}")
        return False

def create_default_user():
    """Create the default user and migrate existing data."""
    print("Creating default user...")
    
    try:
        auth_storage = AuthStorage()
        result = auth_storage.create_default_user("huynguyenvt1989@gmail.com", "Vungtau1989")
        
        if result["success"]:
            print(f"✅ Default user created successfully!")
            print(f"   Email: huynguyenvt1989@gmail.com")
            print(f"   User ID: {result['user']['id']}")
            print(f"   Token: {result['token'][:20]}...")
            
            if result.get("migration"):
                migration = result["migration"]
                print(f"📊 Data migration completed:")
                print(f"   Updated embeddings: {migration.get('updated_embeddings', 0)}")
            
            return True
        else:
            print(f"❌ Failed to create default user: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating default user: {e}")
        return False

def main():
    """Main setup function."""
    print("🔐 Authentication Setup Script")
    print("=" * 40)
    
    # Check if schema setup is needed
    try:
        auth_storage = AuthStorage()
        # Try to check if users table exists by attempting to query it
        result = auth_storage.client.table("users").select("id").limit(1).execute()
        schema_exists = True
    except Exception:
        schema_exists = False
    
    if not schema_exists:
        print("Database schema not found. Setting up...")
        if not setup_database_schema():
            return
        print("\nPlease run the SQL schema in Supabase and then run this script again.")
        return
    
    # Check if default user already exists
    try:
        auth_storage = AuthStorage()
        existing_user = auth_storage.client.table("users").select("*").eq("email", "huynguyenvt1989@gmail.com").execute()
        
        if existing_user.data:
            print("✅ Default user already exists!")
            user = existing_user.data[0]
            print(f"   Email: {user['email']}")
            print(f"   User ID: {user['id']}")
            print(f"   Created: {user['created_at']}")
            return
        
    except Exception as e:
        print(f"Error checking for existing user: {e}")
    
    # Create the default user
    if create_default_user():
        print("\n🎉 Setup completed successfully!")
    else:
        print("\n❌ Setup failed!")

if __name__ == "__main__":
    main()