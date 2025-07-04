#!/usr/bin/env python3
"""Add missing doc_type columns to notes, memos, and interviews tables."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from supabase import create_client


def add_missing_columns():
    """Add missing doc_type columns."""
    try:
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set")
            return False
        
        # Create client
        client = create_client(supabase_url, supabase_key)
        
        # Test by creating records with doc_type
        tables_to_fix = [
            ('notes', 'note'),
            ('memos', 'memo'), 
            ('interviews', 'interview')
        ]
        
        for table_name, doc_type_value in tables_to_fix:
            print(f"Testing {table_name} table...")
            
            try:
                # Try to insert with doc_type
                test_data = {
                    'document_id': f'test-{table_name}-doctype',
                    'name': 'Doc Type Test',
                    'content': 'Testing doc_type column',
                    'doc_type': doc_type_value
                }
                
                result = client.table(table_name).insert(test_data).execute()
                
                if result.data:
                    print(f"  ✅ {table_name}: doc_type column exists and working")
                    # Clean up
                    client.table(table_name).delete().eq('document_id', f'test-{table_name}-doctype').execute()
                else:
                    print(f"  ❌ {table_name}: Insert failed")
                    
            except Exception as e:
                if 'doc_type' in str(e) and 'does not exist' in str(e):
                    print(f"  ❌ {table_name}: doc_type column missing")
                    print(f"     Please add it manually in Supabase SQL Editor:")
                    print(f"     ALTER TABLE {table_name} ADD COLUMN doc_type VARCHAR(50) NOT NULL DEFAULT '{doc_type_value}';")
                else:
                    print(f"  ❌ {table_name}: Other error - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv(project_root / "local.env")
    
    print("🔧 Checking table schemas...")
    success = add_missing_columns()
    
    if success:
        print("\n✅ Schema check completed!")
        print("\nIf any columns were missing, please run the SQL commands shown above")
        print("in the Supabase dashboard SQL Editor, then re-run the migration.")
    else:
        print("\n❌ Schema check failed.")
    
    sys.exit(0 if success else 1)