#!/usr/bin/env python3
"""Initialize document storage tables in Supabase."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from supabase import create_client
from src.storage.document_storage import DOCUMENT_STORAGE_SCHEMA
from src.storage.auth_storage import USER_AUTH_SCHEMA


def init_document_storage():
    """Initialize document storage tables."""
    try:
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set")
            return False
        
        # Create client
        client = create_client(supabase_url, supabase_key)
        
        print("Initializing document storage tables...")
        
        # Execute user auth schema first (for the users table)
        print("Creating user authentication tables...")
        try:
            # Split and execute individual statements
            auth_statements = [stmt.strip() for stmt in USER_AUTH_SCHEMA.split(';') if stmt.strip()]
            for statement in auth_statements:
                if statement:
                    client.rpc('exec_sql', {'sql': statement}).execute()
        except Exception as e:
            print(f"Warning: User auth tables might already exist: {e}")
        
        # Execute document storage schema
        print("Creating document storage tables...")
        doc_statements = [stmt.strip() for stmt in DOCUMENT_STORAGE_SCHEMA.split(';') if stmt.strip()]
        for statement in doc_statements:
            if statement:
                try:
                    client.rpc('exec_sql', {'sql': statement}).execute()
                    print(f"✓ Executed: {statement[:50]}...")
                except Exception as e:
                    print(f"Warning: {e}")
        
        print("✅ Document storage initialization completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing document storage: {e}")
        return False


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv(project_root / "local.env")
    
    success = init_document_storage()
    sys.exit(0 if success else 1)