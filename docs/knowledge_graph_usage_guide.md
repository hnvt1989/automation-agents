# Knowledge Graph Integration Guide

## Overview

Our RAG system now includes knowledge graph capabilities powered by Graphiti and Neo4j. This enhancement provides:
- Entity and relationship extraction from documents
- Graph-based search and traversal
- Hybrid search combining vector similarity and graph relationships
- Rich contextual understanding through entity connections

## Setup

### Prerequisites

1. **Install Neo4j** (if not already installed):
   ```bash
   # Using Docker
   docker run -d \
     --name neo4j \
     -p 7474:7474 -p 7687:7687 \
     -e NEO4J_AUTH=neo4j/password \
     neo4j:latest
   
   # Or download from https://neo4j.com/download/
   ```

2. **Install Dependencies**:
   ```bash
   pip install graphiti-core neo4j
   ```

3. **Configure Environment Variables**:
   ```bash
   # Add to your local.env file
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=password
   ```

## Usage Examples

### 1. Basic Search with Graph Context

When you search the knowledge base, the system automatically uses both vector search and graph relationships:

```
You: search knowledge base for "Alice project responsibilities"
```

The enhanced search will:
- Find documents mentioning Alice and projects (vector search)
- Discover relationships like "Alice leads Project X" (graph search)
- Combine and rank results for comprehensive answers

### 2. Exploring Entities

Discover information about specific entities and their connections:

```
You: explore entity Alice
```

Returns:
- Direct relationships (e.g., "Alice works on Project X")
- Related entities grouped by type (projects, people, technologies)
- Contextual facts from the knowledge graph

### 3. Finding Connections

Discover how two entities are related:

```
You: find connections between Alice and Project Apollo
```

Returns:
- Direct connections (e.g., "Alice is the project manager for Apollo")
- Indirect connections through shared entities
- Relevant facts linking the entities

### 4. Type-Specific Search

Search with both collection type and graph context:

```
You: search only conversations about project planning with graph context
```

Combines:
- Conversation collection filtering
- Graph relationships for richer context
- Temporal information from the graph

## How It Works

### Automatic Graph Building

When you index content, the system automatically:

1. **Extracts Entities**: Identifies people, projects, technologies, etc.
2. **Infers Relationships**: Creates connections based on context
3. **Preserves Facts**: Stores relationship descriptions as searchable facts

### Hybrid Search Algorithm

The system uses Reciprocal Rank Fusion (RRF) to combine:
- **Vector Similarity**: Traditional semantic search from ChromaDB
- **Graph Relevance**: Relationship-based results from Neo4j
- **Contextual Ranking**: Considers entity proximity and connection strength

### Entity Types

Common entity types automatically recognized:
- **Person**: Individual contributors, managers, stakeholders
- **Project**: Initiatives, programs, products
- **Technology**: Programming languages, frameworks, tools
- **Organization**: Teams, departments, companies
- **Document**: Reports, specifications, notes

## Advanced Features

### 1. Temporal Analysis

Track how relationships evolve over time:
```
You: show timeline for Project Apollo
```

### 2. Multi-Hop Queries

Find indirect relationships:
```
You: who works with people on Alice's team?
```

### 3. Context Expansion

Automatically include related information:
```
You: search for backend architecture

# System also finds:
# - Team members working on backend
# - Related projects using similar architecture
# - Technology stack connections
```

## Best Practices

### 1. Content Preparation

For best entity extraction:
- Use clear entity names (capitalize proper nouns)
- Include context about relationships
- Mention connections explicitly when possible

### 2. Query Formulation

- **For Facts**: "What does Alice work on?"
- **For Relationships**: "How is Alice connected to Bob?"
- **For Exploration**: "Tell me about Project X and related entities"

### 3. Performance Optimization

- Graph building happens asynchronously
- Initial indexing may take longer
- Subsequent searches are faster due to pre-computed relationships

## Monitoring

### View Statistics

```
You: show knowledge base statistics
```

Returns both:
- Vector storage stats (documents by collection)
- Graph stats (nodes, edges, types)

### Performance Metrics

The system tracks:
- Query response times
- Cache hit rates
- Graph traversal efficiency

## Troubleshooting

### Neo4j Connection Issues

If graph features aren't working:
1. Check Neo4j is running: `http://localhost:7474`
2. Verify credentials in environment variables
3. Check logs for connection errors

### Missing Relationships

If entities aren't being connected:
1. Ensure content has clear entity mentions
2. Check entity extraction is working
3. Verify graph building completed successfully

### Slow Queries

If searches are slow:
1. Check Neo4j indexes are created
2. Monitor cache hit rates
3. Consider adjusting result limits

## Examples of Enhanced Queries

### Project Management
```
You: Who are the key stakeholders for Project Apollo and what are their roles?
```

### Technical Dependencies
```
You: What technologies does our authentication service depend on?
```

### Team Collaboration
```
You: Find all cross-team collaborations mentioned in the last month
```

### Knowledge Discovery
```
You: What connections exist between our ML initiatives and cloud infrastructure?
```

## Integration with Existing Features

The knowledge graph seamlessly integrates with:
- **Multi-collection search**: Graph spans all collections
- **Document indexing**: Automatic entity extraction
- **Conversation analysis**: Extracts participants and topics
- **RAG responses**: Provides richer context for answers

## Future Enhancements

Planned improvements include:
- Graph visualization interface
- Custom entity types
- Relationship inference rules
- Graph-based recommendations
- Temporal pattern analysis