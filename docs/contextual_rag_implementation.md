# Contextual RAG Implementation

## Overview

This document describes the implementation of Contextual Retrieval-Augmented Generation (RAG) in the automation-agents project. Contextual RAG improves retrieval accuracy by adding explanatory context to document chunks before embedding them.

## Key Components

### 1. Contextual Chunker (`src/storage/contextual_chunker.py`)

The `ContextualChunker` class handles the creation of contextual chunks:

- **Template-based context**: Adds contextual information using predefined templates
- **LLM-based context**: Uses an LLM to generate rich contextual descriptions
- **Smart chunking**: Breaks at sentence/paragraph boundaries when possible
- **Context caching**: Caches generated contexts to improve performance

### 2. Enhanced Collection Manager (`src/storage/collection_manager.py`)

New methods for contextual indexing and retrieval:

- `index_with_context()`: Index documents with contextual information
- `contextual_search()`: Search with context-aware ranking
- `hybrid_contextual_search()`: Combine embeddings and BM25 search
- `index_conversation_with_context()`: Special handling for conversations
- `batch_index_with_context()`: Efficient batch indexing
- `reindex_with_context()`: Add context to existing documents

### 3. RAG Agent Integration (`src/agents/rag.py`)

- New `contextual_search` tool for agents
- Public `contextual_search()` method for direct usage
- Automatic fallback to regular search if contextual is disabled

### 4. Filesystem Agent Enhancement (`src/agents/filesystem.py`)

- Automatic contextual indexing when adding files
- Document summary extraction for better context
- Category inference based on file type and path

## Configuration

Add to your `local.env`:

```bash
# Enable contextual RAG (default: true)
ENABLE_CONTEXTUAL_RAG=true

# Chunk size for contextual chunking (default: 1000)
CONTEXTUAL_CHUNK_SIZE=1000

# Model for context generation (default: gpt-4o-mini)
CONTEXT_GENERATION_MODEL=gpt-4o-mini
```

## Usage Examples

### 1. Index a Document with Context

```python
from src.storage.collection_manager import CollectionManager

# Index with contextual information
ids = collection_manager.index_with_context(
    content="Your document content here...",
    metadata={
        "source_type": "knowledge_base",
        "filename": "guide.md",
        "category": "documentation",
        "document_summary": "A guide to using the system"
    },
    collection_name="knowledge_base",
    use_llm_context=False  # Use template-based context
)
```

### 2. Search with Contextual RAG

```python
# Contextual search
results = collection_manager.contextual_search(
    query="How to authenticate?",
    collection_name="knowledge_base",
    n_results=5
)

# Hybrid search (embeddings + BM25)
results = await collection_manager.hybrid_contextual_search(
    query="Python async programming",
    collection_name="knowledge_base",
    n_results=5,
    embedding_weight=0.7,
    bm25_weight=0.3
)
```

### 3. Using the RAG Agent

```python
from src.agents.rag import RAGAgent

# Create agent
rag_agent = RAGAgent(model)

# Use contextual search
result = await rag_agent.contextual_search(
    query="How to set up authentication?",
    use_contextual=True
)
```

### 4. Index Files with Context

When using the filesystem agent, files are automatically indexed with context:

```python
# Files are indexed with contextual information
result = await filesystem_agent.run(
    "index file /path/to/document.md"
)
```

## Context Templates

Different source types use different context templates:

### Website Context
```
This chunk is from a web page titled 'Title' at URL.
This is part X of Y from this page.
Section: [if available]
Page summary: [if available]

Content: [chunk text]
```

### Conversation Context
```
This chunk is from a [platform] conversation (ID: xxx) about [topic].
Participants: [list].
Time: [timestamp].
Part X of Y.

Conversation excerpt: [chunk text]
```

### Knowledge Base Context
```
This chunk is from [filename] in the [category] category.
Document type: [type].
Document summary: [if available]
Section: [if available]
Part X of Y.

Content: [chunk text]
```

## Performance Considerations

1. **Template vs LLM Context**: Template-based context is faster but less rich. Use LLM context for important documents.

2. **Context Caching**: The system caches generated contexts to avoid regenerating them.

3. **Batch Operations**: Use `batch_index_with_context()` for multiple documents.

4. **Hybrid Search**: Combines the benefits of semantic search (embeddings) and keyword search (BM25).

## Benefits

1. **Improved Retrieval**: 35-67% reduction in retrieval failures (based on Anthropic's research)
2. **Better Context Understanding**: Chunks include document-level context
3. **Flexible Implementation**: Works with existing ChromaDB infrastructure
4. **Backward Compatible**: Falls back to regular indexing when disabled

## Future Enhancements

1. **BM25 Implementation**: Currently placeholder, needs full implementation
2. **Reranking**: Add a reranking step for even better results
3. **Dynamic Context**: Adjust context based on query type
4. **Graph Integration**: Combine with knowledge graph for richer context