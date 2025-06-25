#!/usr/bin/env python3
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv("local.env")

from src.storage.supabase_client import get_supabase_client

# Check for specific document ID
doc_id = "e34751bac55301fda0c9182c069b6a92"
client = get_supabase_client()

print(f"Checking for document ID: {doc_id}")

# Search by partial match
result = client.client.table("document_embeddings") \
    .select("document_id, content") \
    .like("document_id", f"{doc_id}%") \
    .execute()

if result.data:
    print(f"Found {len(result.data)} chunks with this doc ID")
    for chunk in result.data:
        if "initial BGS" in chunk['content']:
            print(f"✓ Contains 'initial BGS': {chunk['document_id']}")
else:
    print("Not found with this ID")

# Also check by content
print("\nChecking by content...")
result2 = client.client.table("document_embeddings") \
    .select("document_id, content") \
    .ilike("content", "%initial BGS validation%") \
    .execute()

if result2.data:
    print(f"Found {len(result2.data)} chunks containing 'initial BGS validation'")
    for chunk in result2.data[:3]:
        print(f"  - {chunk['document_id']}")
else:
    print("No chunks contain 'initial BGS validation'")

# Check what dmt files ARE indexed
print("\nChecking what DMT files are indexed...")
result3 = client.client.table("document_embeddings") \
    .select("document_id") \
    .ilike("document_id", "%dmt%") \
    .execute()

if result3.data:
    unique_docs = set()
    for chunk in result3.data:
        doc_id_base = chunk['document_id'].split('_chunk_')[0]
        unique_docs.add(doc_id_base)
    print(f"Found {len(unique_docs)} DMT-related documents:")
    for doc in unique_docs:
        print(f"  - {doc}")