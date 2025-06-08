# Knowledge Graph Integration Guide

This guide consolidates all knowledge graph documentation for the automation-agents system.

## Overview

The system integrates Graphiti, a real-time knowledge graph builder for AI agents, into our RAG system to enhance search capabilities with entity relationships and contextual understanding.

## Architecture Design

### Core Components

#### GraphKnowledgeManager
- Manages Graphiti client connection to Neo4j
- Handles entity extraction and relationship creation
- Provides graph search and traversal capabilities
- Integrates with existing ChromaDB collections

#### Enhanced RAG Agent
- New tools for graph-based search
- Hybrid search combining vector similarity and graph relationships
- Context-aware retrieval using entity relationships

### Data Flow

```
Document/Conversation → ChromaDB (Vector Storage)
                    ↓
                    → Graphiti → Neo4j (Knowledge Graph)
                                    ↓
                              Entities & Relationships
```

### Key Features

#### Entity Extraction
- Automatic extraction from indexed content
- Support for custom entity types
- Relationship inference between entities

#### Graph Search Capabilities
- Find related entities
- Traverse relationships
- Context-aware search from center nodes
- Temporal queries (time-based relationships)

#### Hybrid Search
- Combine vector similarity (ChromaDB) with graph relationships (Neo4j)
- Re-rank results based on graph proximity
- Provide richer context for LLM responses

## Implementation Plan

### Phase 1: Core Infrastructure
1. Set up Neo4j connection
2. Create GraphKnowledgeManager class
3. Implement basic entity extraction

### Phase 2: Integration
1. Connect with ChromaDB indexing pipeline
2. Add graph building to document processing
3. Implement graph search tools

### Phase 3: Enhanced Search
1. Create hybrid search algorithm
2. Add relationship-based re-ranking
3. Implement context expansion

### Phase 4: Advanced Features
1. Graph visualization
2. Relationship inference
3. Temporal analysis

## Usage Guide

### Basic Setup

1. **Install Dependencies**
   ```bash
   pip install graphiti-core neo4j
   ```

2. **Configure Neo4j**
   Add to your `local.env`:
   ```env
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   ```

3. **Initialize Graph Manager**
   ```python
   from src.storage.graph_knowledge_manager import GraphKnowledgeManager
   
   graph_manager = GraphKnowledgeManager()
   await graph_manager.initialize()
   ```

### Adding Knowledge to Graph

```python
# Index documents with graph building
await graph_manager.add_to_graph(
    content="Meeting notes about Project X with Alice and Bob",
    metadata={"type": "meeting", "date": "2024-01-15"}
)
```

### Searching the Graph

```python
# Find related entities
results = await graph_manager.search_related_entities("Alice")

# Search with context
context_results = await graph_manager.search_with_context(
    query="Project X status",
    context_nodes=["Alice", "Bob"]
)
```

## Benefits

1. **Better Context Understanding**: Entities and their relationships provide richer context
2. **Improved Search Relevance**: Graph relationships help find related information
3. **Personalization**: User-specific nodes enable personalized responses
4. **Knowledge Discovery**: Uncover hidden connections between information
5. **Temporal Awareness**: Track how knowledge evolves over time

## Use Cases

1. **Question Answering**: "What projects is Alice working on with Bob?"
2. **Context Expansion**: Find all related documents when searching for a topic
3. **Relationship Queries**: "Show me all meetings about Project X"
4. **Timeline Analysis**: "How has our approach to testing evolved?"
5. **Expert Finding**: "Who knows about GraphQL in our team?"

## Technical Requirements

- Neo4j database (local or cloud)
- Graphiti-core library
- OpenAI API for entity extraction
- Additional storage for graph data

## Performance Considerations

1. **Async Processing**: Build graph asynchronously during indexing
2. **Batch Operations**: Process entities in batches
3. **Caching**: Cache frequently accessed graph patterns
4. **Indexing**: Proper Neo4j indexes for performance

## Troubleshooting

### Common Issues

**Neo4j Connection Errors**
- Verify Neo4j is running and accessible
- Check connection credentials in environment variables
- Ensure firewall allows connection on port 7687

**Entity Extraction Issues**
- Verify OpenAI API key is configured
- Check model availability and rate limits
- Review content quality and format

**Performance Issues**
- Monitor Neo4j memory usage
- Check query complexity and optimization
- Consider batching large operations

### Configuration

The knowledge graph system is configured through environment variables:

```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Graphiti Configuration
GRAPHITI_ENTITY_EXTRACTION_MODEL=gpt-4o-mini
GRAPHITI_RELATIONSHIP_MODEL=gpt-4o-mini
```

For more technical details, see the implementation in `src/storage/graph_knowledge_manager.py`.