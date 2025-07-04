#!/usr/bin/env python3
"""Improved search for 686C that extracts actual content."""

import asyncio
import sys
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.supabase_client import get_supabase_client
from src.utils.logging import setup_logger, log_info

setup_logger("search_686c", "INFO")


def extract_actual_content(text):
    """Extract the actual content from contextual chunk text."""
    # Pattern to find "Content: " and get everything after it
    pattern = r'Content:\s*(.+?)(?:\n\nThis chunk|$)'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Fallback: if no pattern found, return original text
    return text


async def search_686c_content():
    """Search for 686C content and display actual content."""
    log_info("=== Searching for 686C Documentation ===\n")
    
    client = get_supabase_client()
    
    # Search for documents containing 686C
    result = client.client.table("document_embeddings") \
        .select("document_id, content, metadata, collection_name") \
        .ilike("content", "%686C%") \
        .order("document_id") \
        .execute()
    
    if not result.data:
        log_info("No documents found containing '686C'")
        return
    
    # Group by source document
    documents = {}
    for doc in result.data:
        # Extract metadata
        import json
        metadata = json.loads(doc['metadata']) if isinstance(doc['metadata'], str) else doc['metadata']
        source = metadata.get('source', 'Unknown')
        
        if source not in documents:
            documents[source] = []
        
        # Extract actual content
        actual_content = extract_actual_content(doc['content'])
        
        documents[source].append({
            'chunk_id': doc['document_id'],
            'content': actual_content,
            'metadata': metadata,
            'collection': doc['collection_name']
        })
    
    # Display results organized by document
    log_info(f"Found 686C content in {len(documents)} documents:\n")
    
    for source, chunks in documents.items():
        log_info(f"\n📄 Document: {Path(source).name}")
        log_info(f"   Path: {source}")
        log_info(f"   Chunks: {len(chunks)}")
        log_info(f"   Collection: {chunks[0]['collection']}")
        
        # Show most relevant chunks (those with more 686C mentions)
        relevant_chunks = []
        for chunk in chunks:
            count = chunk['content'].upper().count('686C')
            if count > 0:
                relevant_chunks.append((count, chunk))
        
        # Sort by relevance
        relevant_chunks.sort(key=lambda x: x[0], reverse=True)
        
        # Show top 3 most relevant chunks
        for i, (count, chunk) in enumerate(relevant_chunks[:3]):
            log_info(f"\n   Chunk {i+1} (686C mentioned {count} times):")
            
            # Extract sentences containing 686C
            sentences = chunk['content'].split('.')
            relevant_sentences = []
            for sentence in sentences:
                if '686C' in sentence.upper():
                    relevant_sentences.append(sentence.strip())
            
            # Show relevant sentences
            for j, sentence in enumerate(relevant_sentences[:3]):
                log_info(f"     • {sentence}.")
            
            if len(relevant_sentences) > 3:
                log_info(f"     ... and {len(relevant_sentences) - 3} more sentences")


async def search_specific_info():
    """Search for specific 686C information."""
    log_info("\n\n=== Searching for Specific 686C Information ===\n")
    
    # Common questions about 686C
    searches = [
        ("What is 686C?", r"686C\s+(?:is|form|application|claim).*?\."),
        ("686C purpose", r"(?:purpose|used?\s+for|submit).*?686C.*?\."),
        ("686C process", r"(?:process|submit|file|complete).*?686C.*?\.")
    ]
    
    client = get_supabase_client()
    
    for query, pattern in searches:
        log_info(f"\n🔍 {query}")
        
        # Search for documents
        result = client.client.table("document_embeddings") \
            .select("content") \
            .ilike("content", f"%{query.replace('?', '')}%") \
            .limit(5) \
            .execute()
        
        if result.data:
            for doc in result.data:
                actual_content = extract_actual_content(doc['content'])
                matches = re.findall(pattern, actual_content, re.IGNORECASE)
                for match in matches[:2]:
                    log_info(f"   → {match}")


async def main():
    """Run improved 686C search."""
    await search_686c_content()
    await search_specific_info()
    
    log_info("\n\n💡 Tip: For better search results, try:")
    log_info("   - 'What is form 686C used for?'")
    log_info("   - 'BGS 686C-674 documentation'")
    log_info("   - 'How to submit 686C claim'")


if __name__ == "__main__":
    asyncio.run(main())