# Cloud Services Setup Guide

This guide covers setting up and using cloud services (Supabase for vector storage and Neo4j Aura for knowledge graphs) with the automation agents system.

## Overview

The system supports both local and cloud storage configurations:
- **Local**: ChromaDB for vectors, local Neo4j for graphs
- **Cloud**: Supabase (pgvector) for vectors, Neo4j Aura for graphs

## Supabase Setup (Vector Storage)

### 1. Create Supabase Project
1. Go to [supabase.com](https://supabase.com) and create a new project
2. Note your project URL and anon/public key

### 2. Enable pgvector Extension
In your Supabase SQL editor, run:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Create Vector Storage Schema
Run the schema from `scripts/supabase_vector_schema.sql`:
```sql
-- Create table for document embeddings
CREATE TABLE IF NOT EXISTS document_embeddings (
    id SERIAL PRIMARY KEY,
    collection_name VARCHAR(255) NOT NULL,
    document_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(collection_name, document_id)
);

-- Create required indexes and functions
-- (see full schema in scripts/supabase_vector_schema.sql)
```

### 4. Configure Environment Variables
Add to your `local.env`:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
```

## Neo4j Aura Setup (Knowledge Graph)

### 1. Create Neo4j Aura Instance
1. Go to [neo4j.com/cloud/aura](https://neo4j.com/cloud/aura)
2. Create a new AuraDB instance (Free tier available)
3. Save the connection URI and generated password

### 2. Configure Environment Variables
Add to your `local.env`:
```env
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_generated_password_here
```

### 3. Migrate Existing Data (Optional)
If you have existing data in local Neo4j:
```bash
python scripts/migrate_neo4j_to_cloud.py
```

## Configuration

### Automatic Cloud Detection
The system automatically uses cloud services when configured:
```env
USE_CLOUD_STORAGE=auto  # auto, true, or false
```

- `auto` (default): Use cloud if credentials are configured
- `true`: Always use cloud (error if not configured)
- `false`: Always use local storage

### Using Cloud Services

#### In Main Application
```bash
# The system automatically detects and uses cloud services
python -m src.main
```

#### In API Server
```bash
# Use the Supabase-enabled API server
python -m src.api_server_supabase
```

#### Programmatic Usage
```python
from src.agents.rag_cloud import CloudRAGAgent
from pydantic_ai.models.openai import OpenAIModel

# Create cloud-enabled RAG agent
rag_agent = CloudRAGAgent(model, use_cloud=True)

# Use the agent normally
result = await rag_agent.run("Search for information about Python")
```

## Migration Scripts

### ChromaDB to Supabase Migration
```bash
python scripts/migrate_chromadb_to_supabase.py
```

Options:
- `--collection`: Specific collection to migrate
- `--clear-target`: Clear target before migration
- `--batch-size`: Number of documents per batch

### Neo4j Local to Cloud Migration
```bash
python scripts/migrate_neo4j_to_cloud.py
```

Options:
- `--clear-target`: Clear cloud database before import
- `--verify-only`: Only verify the target database

## Features Comparison

| Feature | Local | Cloud |
|---------|-------|-------|
| Vector Storage | ChromaDB | Supabase (pgvector) |
| Embedding Model | OpenAI | OpenAI |
| Knowledge Graph | Neo4j Community | Neo4j Aura |
| Scalability | Limited by hardware | Auto-scaling |
| Persistence | Local disk | Managed cloud |
| Backup | Manual | Automatic |
| Cost | Infrastructure only | Usage-based |

## Troubleshooting

### Supabase Issues

1. **pgvector not found**: Ensure extension is enabled in Supabase dashboard
2. **RLS errors**: Check Row Level Security settings or disable for development
3. **Connection errors**: Verify SUPABASE_URL and SUPABASE_KEY are correct

### Neo4j Aura Issues

1. **Connection refused**: Ensure using `neo4j+s://` protocol for secure connection
2. **Authentication failed**: Verify password and username
3. **Timeout errors**: Check network connectivity and firewall rules

### Performance Tips

1. **Batch Operations**: Use batch inserts for better performance
2. **Indexes**: Ensure all required indexes are created
3. **Embedding Cache**: Consider caching embeddings for frequently accessed content
4. **Connection Pooling**: Both clients use connection pooling by default

## Monitoring

### Supabase Dashboard
- Monitor query performance
- Check storage usage
- View real-time logs

### Neo4j Aura Console
- Query performance metrics
- Node/relationship counts
- Memory usage

## Security Best Practices

1. **Environment Variables**: Never commit credentials to version control
2. **Row Level Security**: Enable RLS in Supabase for production
3. **API Keys**: Use service-specific keys with minimal permissions
4. **Network Security**: Restrict access by IP if possible
5. **Regular Backups**: Enable automated backups in both services

## Cost Optimization

1. **Supabase**:
   - Free tier: 500MB database, 1GB storage
   - Optimize embedding dimensions if needed
   - Clean up old embeddings periodically

2. **Neo4j Aura**:
   - Free tier: 200K nodes, 400K relationships
   - Use indexes effectively
   - Batch operations to reduce API calls

## Next Steps

1. Set up monitoring and alerting
2. Implement automated backups
3. Create performance benchmarks
4. Set up staging environment
5. Document disaster recovery procedures