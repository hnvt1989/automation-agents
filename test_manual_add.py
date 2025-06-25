#!/usr/bin/env python3
"""Test manually adding the DMT content."""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv("local.env")

# Read the file content
file_path = Path("data/va_notes/dmt_release_process.md")
content = file_path.read_text()

print("File content preview:")
print("=" * 50)
print(content[:500])
print("=" * 50)

# Extract the specific section about initial BGS validation
lines = content.split('\n')
target_section = []
in_section = False

for line in lines:
    if "Phase 1: Initial BGS Validation" in line:
        in_section = True
    if in_section:
        target_section.append(line)
        if line.strip() == "" and len(target_section) > 5:
            break

print("\nTarget section:")
print("=" * 50)
print('\n'.join(target_section))
print("=" * 50)

# Now try to add just this content
from src.storage.supabase_vector import SupabaseVectorClient

client = SupabaseVectorClient("documents")

test_content = """
DMT Release Process Documentation

## Phase 1: Initial BGS Validation
- **Goal:** Ensure the BGS service accepts the payload and returns valid routing responses.
- **Test Environment:** Staging
- **Resources:** 
  - Two different participant accounts (e.g., Participant A with an EDIPI ending in 07, Participant B with an EDIPI ending in 11).
  - These accounts are preloaded in the BGS staging service.
- **Challenge:** The BGS service in staging is often unreliable, sometimes failing due to system downtime. Jobs may retry through Sidekiq queues, causing delays.
"""

print("\nTrying to add test content...")
try:
    client.add_documents(
        documents=[test_content],
        metadatas=[{
            "source": "manual_test",
            "filename": "dmt_release_process.md",
            "type": "test"
        }],
        ids=["manual_test_dmt_001"]
    )
    print("✓ Successfully added test content")
    
    # Now search for it
    print("\nSearching for 'initial BGS validation'...")
    results = client.query(["initial BGS validation"], n_results=5)
    
    if results and results.get('documents') and results['documents'][0]:
        print(f"✓ Found {len(results['documents'][0])} results")
        for i, doc in enumerate(results['documents'][0]):
            if "initial BGS" in doc:
                print(f"\n✓ Result {i+1} contains our content!")
                print(f"Content: {doc[:300]}...")
    else:
        print("✗ No results found")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()