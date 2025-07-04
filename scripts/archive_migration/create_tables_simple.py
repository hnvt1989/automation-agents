#!/usr/bin/env python3
"""Create document storage tables in Supabase using direct table operations."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from supabase import create_client


def create_tables():
    """Create document storage tables."""
    try:
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set")
            return False
        
        # Create client
        client = create_client(supabase_url, supabase_key)
        
        print("Testing document storage by creating a simple document...")
        
        # Try to create a test document
        test_data = {
            "document_id": "test-simple-123",
            "name": "Test Document",
            "description": "A test document",
            "content": "This is test content",
            "doc_type": "document",
            "metadata": "{}",
            "user_id": None
        }
        
        # Try inserting into documents table (this will fail if table doesn't exist)
        try:
            result = client.table("documents").insert(test_data).execute()
            print("✅ Documents table exists and working!")
            
            # Clean up test data
            client.table("documents").delete().eq("document_id", "test-simple-123").execute()
            
        except Exception as e:
            print(f"❌ Documents table doesn't exist or has issues: {e}")
            print("Please create the tables manually in Supabase dashboard or via SQL editor.")
            
            # Print the SQL for manual creation
            print("\n--- SQL to create tables manually ---")
            print("""
-- Create documents table for storing full documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    metadata JSONB DEFAULT '{}',
    user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_document_id ON documents(document_id);
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON documents(doc_type);

-- Repeat for other tables: notes, memos, interviews
CREATE TABLE IF NOT EXISTS notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
            """)
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv(project_root / "local.env")
    
    success = create_tables()
    sys.exit(0 if success else 1)