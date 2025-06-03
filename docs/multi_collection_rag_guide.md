# Multi-Collection RAG Search Guide

## Current Situation
- RAG searches only the default collection: `automation_agents`
- All content types are mixed in one collection
- No built-in support for multi-collection search

## Options for Multi-Collection Search

### Option 1: Search Specific Collection (Modify RAG)
```python
# Enhanced RAG command examples:
You: search in collection "project_docs" for "API integration"
You: search knowledge base collection="meeting_notes" query="budget discussion"
```

Implementation would require:
```python
async def search_knowledge_base(ctx, query: str, collection: str = None):
    if collection:
        client = get_chromadb_client(collection_name=collection)
    else:
        client = ctx.deps.chromadb_client  # default
```

### Option 2: Search All Collections
```python
# Search across all collections
You: search all collections for "TestRail integration"
```

Implementation approach:
```python
async def search_all_collections(query: str):
    results = []
    collections = chromadb_client.list_collections()
    
    for collection in collections:
        client = get_chromadb_client(collection_name=collection.name)
        collection_results = client.query(query)
        results.extend(collection_results)
    
    # Merge and rank results
    return rank_by_relevance(results)
```

### Option 3: Tagged Search with Metadata
Keep single collection but use metadata for filtering:
```python
# Current approach - filter by metadata
You: search for "API docs" where type="file"
You: search for "meeting notes" where source="conversations"
```

This works with current implementation:
```python
results = chromadb_client.query(
    query_texts=[query],
    where={"source_type": "file"}  # or "conversation"
)
```

### Option 4: Collection Routing by Query Type
Automatically route to appropriate collection based on query:
```python
# Automatic routing examples:
You: search files for "backend testing"        # -> searches file collection
You: search conversations about "API design"   # -> searches conversation collection
You: search tasks related to "TestRail"       # -> searches task collection
```

## Recommended Approach

### Short Term (Works Now)
Use metadata filtering with single collection:
```python
# Examples that work with current system:
You: find documents about "TestRail" from files
You: search conversations mentioning "backend testing"
```

The RAG agent can be given hints:
- "from files" → filter where source_type = "file"
- "conversations" → filter where source_type = "conversation"

### Medium Term
Implement collection-aware search:
1. Add collection parameter to RAG search
2. Create collection manager
3. Add multi-collection search capability

### Long Term
Smart routing and federated search:
1. Auto-detect collection from query context
2. Search relevant collections in parallel
3. Merge and re-rank results
4. Return unified results with source attribution

## Practical Examples

### What Works Now:
```
You: search knowledge base for "TestRail API"
# Searches everything in default collection

You: what files mention "contract testing"  
# RAG interprets and searches, but no filtering
```

### What Could Work with Enhancements:
```
You: search project_docs collection for "API specs"
You: search all technical documentation for "authentication"
You: find meeting notes about "TestRail integration"
```

## Implementation Priority

1. **Metadata Filtering** (easiest, works now)
   - Add source type to all indexed content
   - Enhance RAG to parse filter hints

2. **Collection Parameter** (medium effort)
   - Add optional collection parameter
   - Update prompts to support collection names

3. **Multi-Collection Search** (higher effort)
   - List all collections
   - Search each relevant one
   - Merge and rank results

4. **Smart Routing** (advanced)
   - NLP to determine collection
   - Parallel search
   - Intelligent result merging