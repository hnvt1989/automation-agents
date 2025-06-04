# Multi-Collection RAG Search Guide

> **Status**: ✅ Implemented - This guide reflects the current multi-collection architecture.

## Current Implementation

The system now supports multiple ChromaDB collections for better organization and performance:

### Collections
1. **`automation_agents_websites`** - Indexed website content
2. **`automation_agents_conversations`** - Conversation history and messages
3. **`automation_agents_knowledge`** - Knowledge base documents and files

### Key Components

#### 1. Enhanced ChromaDB Client (`src/storage/chromadb_client.py`)
- Multi-collection support with collection caching
- Query caching for improved performance
- Performance monitoring and metrics
- Parallel query execution for multiple collections

#### 2. Collection Manager (`src/storage/collection_manager.py`)
- High-level interface for managing collections
- Type-specific indexing methods
- Cross-collection search capabilities
- Batch processing for bulk operations

#### 3. Performance Optimizations
- **Query Cache**: LRU cache with TTL for frequently accessed queries
- **Performance Monitor**: Tracks operation metrics and response times
- **Parallel Queries**: Concurrent execution when searching multiple collections

## Usage Examples

### Indexing Content

#### Index a Website
```python
from src.storage.collection_manager import CollectionManager

manager = CollectionManager(chromadb_client)
manager.index_website(
    url="https://example.com",
    content="Page content here...",
    title="Example Page"
)
```

#### Index a Conversation
```python
messages = [
    {"sender": "Alice", "content": "How do we implement this?", "timestamp": "2024-01-01T10:00:00"},
    {"sender": "Bob", "content": "Let's use ChromaDB", "timestamp": "2024-01-01T10:01:00"}
]

manager.index_conversation(
    messages=messages,
    platform="slack",
    conversation_id="conv_123"
)
```

#### Index Knowledge Documents
```python
manager.index_knowledge(
    file_path="/docs/guide.md",
    content="Documentation content...",
    category="documentation"
)
```

### Searching Content

#### Search All Collections
```
You: search knowledge base for "ChromaDB implementation"
```
The RAG agent will search across all collections and return merged results.

#### Search Specific Collection Types
```
You: search only websites for "API documentation"
You: search conversations about "project planning"
You: search knowledge files for "setup guide"
```

The enhanced RAG agent now supports the `search_by_type` tool:
```python
results = await search_by_type(
    query="API documentation",
    source_types=["website"],  # Can be ["website", "conversation", "knowledge"]
    n_results=5
)
```

### Performance Monitoring

#### View Performance Stats
```python
stats = chromadb_client.get_performance_stats()
print(f"Cache hit rate: {stats['cache_stats']['hit_rate']:.1%}")
print(f"Average query time: {stats['performance_metrics']['query_collection']['average_time']:.3f}s")
```

#### Log Performance Report
```python
chromadb_client.log_performance_report()
```

## Migration from Single Collection

A migration script is provided to move existing data:

```bash
python scripts/migrate_to_multi_collection.py --help

# Dry run to see what would be migrated
python scripts/migrate_to_multi_collection.py --dry-run

# Perform migration
python scripts/migrate_to_multi_collection.py

# Migrate with custom batch size
python scripts/migrate_to_multi_collection.py --batch-size 200
```

## Configuration

### Collection-Specific Chunk Sizes
Different content types use optimized chunk configurations:
- **Websites**: 1500 tokens with 200 overlap (larger for context)
- **Conversations**: 500 tokens with 50 overlap (preserve message boundaries)
- **Knowledge**: 1000 tokens with 100 overlap (balanced approach)

### Cache Configuration
```python
# In ChromaDBClient initialization
self._query_cache = QueryCache(
    max_size=200,      # Maximum cached queries
    ttl_seconds=600    # 10-minute TTL
)
```

## Agent Integration

### Filesystem Agent
- Automatically uses appropriate collection based on content type
- `index_file` → Knowledge collection
- `analyze_conversation_image` → Conversation collection

### RAG Agent
- `search_knowledge_base` → Searches all collections
- `search_by_type` → Search specific collection types
- `get_collection_stats` → Shows stats for all collections

## Best Practices

1. **Use Collection Manager** for indexing operations instead of direct client calls
2. **Batch Operations** when indexing multiple items
3. **Monitor Performance** regularly to identify bottlenecks
4. **Clear Cache** after bulk updates to ensure fresh results
5. **Use Metadata** effectively for fine-grained filtering

## Performance Considerations

1. **Parallel Queries**: Multiple collections are queried concurrently
2. **Result Merging**: Results are merged and sorted by relevance score
3. **Cache Invalidation**: Cache is automatically invalidated on document updates
4. **Batch Processing**: Use batch methods for bulk indexing operations

## Troubleshooting

### Slow Queries
1. Check cache hit rate with `get_performance_stats()`
2. Monitor query times in performance metrics
3. Consider increasing cache size or TTL

### Missing Results
1. Verify content is indexed in correct collection
2. Check collection stats to ensure documents exist
3. Use metadata filters to narrow search scope

### Migration Issues
1. Run with `--dry-run` first to preview changes
2. Check source collection has expected documents
3. Verify all collections are created successfully