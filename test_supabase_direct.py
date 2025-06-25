#!/usr/bin/env python3
"""Direct test of Supabase for BGS documents."""

import os
from supabase import create_client
import json

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set")
    exit(1)

# Create Supabase client
client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Checking Supabase for BGS-related documents...")
print("=" * 60)

# Check total documents
try:
    result = client.table("document_embeddings").select("*", count="exact").limit(0).execute()
    print(f"\nTotal documents in database: {result.count}")
except Exception as e:
    print(f"Error getting document count: {str(e)}")

# Search for BGS-related content
print("\nSearching for BGS-related documents...")
try:
    # Search using ILIKE for content containing BGS
    result = client.table("document_embeddings") \
        .select("document_id, collection_name, content, metadata") \
        .ilike("content", "%BGS%") \
        .limit(10) \
        .execute()
    
    if result.data:
        print(f"\nFound {len(result.data)} BGS-related documents:")
        for i, doc in enumerate(result.data):
            print(f"\n{i+1}. Document ID: {doc['document_id']}")
            print(f"   Collection: {doc['collection_name']}")
            print(f"   Content preview: {doc['content'][:200]}...")
            if doc['metadata']:
                metadata = json.loads(doc['metadata']) if isinstance(doc['metadata'], str) else doc['metadata']
                if 'source' in metadata:
                    print(f"   Source: {metadata['source']}")
    else:
        print("No BGS-related documents found")
        
except Exception as e:
    print(f"Error searching for BGS documents: {str(e)}")

# Search for "initial BGS validation" specifically
print("\n\nSearching for 'initial BGS validation'...")
try:
    result = client.table("document_embeddings") \
        .select("document_id, collection_name, content") \
        .ilike("content", "%initial BGS validation%") \
        .execute()
    
    if result.data:
        print(f"Found {len(result.data)} documents containing 'initial BGS validation'")
        for doc in result.data:
            print(f"- Collection: {doc['collection_name']}, ID: {doc['document_id']}")
    else:
        print("No documents found containing 'initial BGS validation'")
        
except Exception as e:
    print(f"Error: {str(e)}")

# Check collection names
print("\n\nChecking available collections...")
try:
    result = client.table("document_embeddings") \
        .select("collection_name") \
        .execute()
    
    if result.data:
        collections = set(doc['collection_name'] for doc in result.data)
        print(f"Found {len(collections)} unique collections:")
        for col in sorted(collections):
            print(f"- {col}")
    else:
        print("No collections found")
        
except Exception as e:
    print(f"Error: {str(e)}")