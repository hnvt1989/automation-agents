#!/usr/bin/env python3
"""Fix password hashing for existing users after security update.

This script updates existing user passwords to work with the new 
client-side + server-side double hashing approach.
"""

import os
import sys
import hashlib
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv("local.env")

def hash_password_client_side(password: str) -> str:
    """Simulate client-side hashing."""
    return hashlib.sha256(password.encode()).hexdigest()

def hash_password_server_side(password: str) -> str:
    """Server-side hashing (second hash)."""
    return hashlib.sha256(password.encode()).hexdigest()

def main():
    """Update existing user password hashing."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set")
        return
    
    client = create_client(supabase_url, supabase_key)
    
    # Get existing users
    try:
        result = client.table("users").select("*").execute()
        users = result.data
        
        print(f"Found {len(users)} users to update")
        
        for user in users:
            email = user["email"]
            current_hash = user["password_hash"]
            
            # For the default user, we know the original password
            if email == "huynguyenvt1989@gmail.com":
                original_password = "Vungtau1989"
                
                # Create the new double-hashed password
                client_hash = hash_password_client_side(original_password)
                server_hash = hash_password_server_side(client_hash)
                
                # Update the user's password hash
                update_result = client.table("users").update({
                    "password_hash": server_hash
                }).eq("id", user["id"]).execute()
                
                if update_result.data:
                    print(f"✅ Updated password hash for {email}")
                else:
                    print(f"❌ Failed to update password hash for {email}")
            else:
                print(f"⚠️  Skipping {email} - password unknown, user will need to reset")
        
        print("✅ Password hash update completed")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()