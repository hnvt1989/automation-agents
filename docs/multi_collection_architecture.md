# Multi-Collection ChromaDB Architecture Design

## Overview
This document outlines the design for implementing multiple collections in ChromaDB to separate different types of data for better organization and performance.

## Collection Structure

### 1. Website Collection (`automation_agents_websites`)
- **Purpose**: Store indexed website content
- **Metadata Fields**:
  - `source_type`: "website"
  - `url`: Website URL
  - `title`: Page title
  - `crawled_at`: Timestamp
  - `domain`: Domain name

### 2. Conversation Collection (`automation_agents_conversations`)
- **Purpose**: Store conversation data from screenshots/messages
- **Metadata Fields**:
  - `source_type`: "conversation"
  - `conversation_id`: Unique conversation identifier
  - `participants`: List of participants
  - `timestamp`: Message timestamp
  - `platform`: Conversation platform (e.g., "slack", "telegram")

### 3. Knowledge Collection (`automation_agents_knowledge`)
- **Purpose**: Store general knowledge documents, files, and notes
- **Metadata Fields**:
  - `source_type`: "knowledge"
  - `file_path`: Original file path
  - `file_type`: File extension
  - `indexed_at`: Timestamp
  - `category`: Optional category tag

## API Design

### ChromaDBClient Updates
```python
class ChromaDBClient:
    def __init__(self, persist_directory: Optional[Path] = None):
        # Initialize without collection_name
        # Collections are managed separately
        
    def get_collection(self, collection_name: str) -> Collection:
        # Get or create a specific collection
        
    def add_to_collection(self, collection_name: str, documents: List[str], ...):
        # Add documents to a specific collection
        
    def query_collection(self, collection_name: str, query_texts: List[str], ...):
        # Query a specific collection
        
    def query_multiple_collections(self, collection_names: List[str], query_texts: List[str], ...):
        # Query multiple collections and merge results
```

### Collection Manager
```python
class CollectionManager:
    """Manages multiple ChromaDB collections with type-specific logic."""
    
    def __init__(self, client: ChromaDBClient):
        self.client = client
        
    def index_website(self, url: str, content: str, metadata: Dict):
        # Index website content with appropriate chunking
        
    def index_conversation(self, messages: List[Dict], metadata: Dict):
        # Index conversation with context preservation
        
    def index_knowledge(self, file_path: Path, content: str, metadata: Dict):
        # Index knowledge documents
        
    def search_all(self, query: str, n_results: int = 5) -> Dict[str, List]:
        # Search across all collections
        
    def search_by_type(self, query: str, source_types: List[str], n_results: int = 5):
        # Search specific collection types
```

## Performance Considerations

### 1. Collection-Specific Optimizations
- **Website Collection**: Larger chunk sizes (1500 tokens) for better context
- **Conversation Collection**: Smaller chunks (500 tokens) to preserve message boundaries
- **Knowledge Collection**: Standard chunks (1000 tokens) with overlap

### 2. Query Strategies
- **Parallel Queries**: Query collections in parallel for better performance
- **Result Merging**: Smart deduplication and relevance scoring across collections
- **Caching**: Implement query result caching for frequently accessed data

### 3. Index Management
- **Batch Processing**: Index documents in batches to reduce overhead
- **Async Operations**: Use async operations for non-blocking indexing
- **Background Jobs**: Schedule reindexing and optimization tasks

## Migration Strategy

### Phase 1: Backward Compatibility
- Keep existing `automation_agents` collection
- Add new collections alongside
- Implement collection routing logic

### Phase 2: Data Migration
- Create migration script to move existing data
- Categorize documents based on metadata
- Validate migrated data

### Phase 3: Deprecation
- Update all agents to use new collections
- Remove references to old collection
- Archive old collection data

## Testing Strategy

### Unit Tests
- Test collection creation and management
- Test collection-specific indexing logic
- Test query routing and merging

### Integration Tests
- Test end-to-end indexing workflows
- Test cross-collection queries
- Test performance with multiple collections

### Performance Tests
- Benchmark query performance
- Test concurrent operations
- Measure memory usage

## Error Handling

### Collection-Specific Errors
```python
class CollectionNotFoundError(ChromaDBError):
    """Raised when a collection doesn't exist."""

class InvalidCollectionTypeError(ChromaDBError):
    """Raised when invalid collection type is specified."""
```

### Graceful Degradation
- If a collection is unavailable, continue with others
- Log warnings for failed operations
- Provide partial results when possible