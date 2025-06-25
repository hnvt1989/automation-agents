# Cloud Setup Guide: Supabase Vectors + Neo4j Aura

This guide covers setting up cloud-based vector storage with Supabase and knowledge graphs with Neo4j Aura.

## Overview

### Architecture
- **Vector Storage**: Supabase pgvector with OpenAI embeddings
- **Knowledge Graph**: Neo4j Aura (managed cloud service)
- **Embedding Model**: OpenAI text-embedding-ada-002
- **Benefits**: Fully cloud-based, scalable, no local dependencies

## Prerequisites

1. **Supabase Account**: Sign up at [supabase.com](https://supabase.com)
2. **Neo4j Aura Account**: Sign up at [neo4j.com/cloud/aura](https://neo4j.com/cloud/aura)
3. **OpenAI API Key**: For generating embeddings

## Step 1: Supabase Vector Setup

### 1.1 Create Supabase Project
1. Log into Supabase Dashboard
2. Create a new project
3. Note your project URL and anon key

### 1.2 Enable pgvector Extension
Run this in the Supabase SQL Editor:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 1.3 Create Vector Schema
Execute the schema from `scripts/supabase_schema.sql`:
```sql
CREATE TABLE document_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_name VARCHAR(255) NOT NULL,
    document_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(collection_name, document_id)
);

-- Create indexes
CREATE INDEX idx_embeddings_collection ON document_embeddings(collection_name);
CREATE INDEX idx_embeddings_metadata ON document_embeddings USING GIN(metadata);
CREATE INDEX idx_embeddings_embedding ON document_embeddings USING ivfflat (embedding vector_cosine_ops);
```

### 1.4 Create Search Functions
Execute the functions from `scripts/supabase_vector_functions.sql`:
```sql
-- See the full file for all functions
CREATE OR REPLACE FUNCTION match_documents(...) 
-- This enables similarity search
```

## Step 2: Neo4j Aura Setup

### 2.1 Create Neo4j Aura Instance
1. Log into Neo4j Aura Console
2. Create a new database (free tier available)
3. Download credentials file
4. Note the connection URI (neo4j+s://...)

### 2.2 Configure Environment
Add to your `local.env`:
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key_here

# Neo4j Aura
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# OpenAI (for embeddings)
OPENAI_API_KEY=your_openai_key_here
```

## Step 3: Data Migration

### 3.1 Migrate Vectors from ChromaDB
```bash
# Dry run first
python scripts/migrate_vectors_to_supabase.py --dry-run

# Actual migration
python scripts/migrate_vectors_to_supabase.py --verify

# Migrate specific collection
python scripts/migrate_vectors_to_supabase.py --collection websites --batch-size 50
```

### 3.2 Migrate Graph from Local Neo4j (if applicable)
```bash
# Export from local Neo4j
# Import to Neo4j Aura using their import tool
```

## Step 4: Update Application Code

### 4.1 Use Cloud Services
The application now supports both local and cloud storage. To use cloud services:

1. **For Vectors**: The RAG agent will automatically use Supabase if configured
2. **For Graphs**: Graph operations will use Neo4j Aura if configured

### 4.2 Test the Setup
```python
# Test vector search
from src.storage.supabase_vector import SupabaseVectorClient

client = SupabaseVectorClient("test_collection")
client.add_documents(["Hello world"], metadatas=[{"source": "test"}])
results = client.query(["Hello"], n_results=1)
print(results)

# Test graph connection
from src.storage.neo4j_cloud import get_neo4j_cloud_client

neo4j = get_neo4j_cloud_client()
summary = neo4j.get_graph_summary()
print(summary)
```

## Performance Optimization

### Supabase Vectors
1. **Indexing**: Use IVFFlat index for large datasets (>1M vectors)
2. **Batch Operations**: Insert documents in batches of 100-500
3. **Query Optimization**: Use metadata filters to reduce search space

### Neo4j Aura
1. **Indexes**: Create indexes on frequently queried properties
2. **Connection Pooling**: Already configured in the client
3. **Query Optimization**: Use EXPLAIN to analyze query performance

## Monitoring and Costs

### Supabase
- **Free Tier**: 500MB database, 1GB bandwidth
- **Monitoring**: Built-in dashboard for query performance
- **Costs**: Based on database size and bandwidth

### Neo4j Aura
- **Free Tier**: 200K nodes, 400K relationships
- **Monitoring**: Built-in metrics dashboard
- **Costs**: Based on database size and operations

### OpenAI Embeddings
- **Cost**: ~$0.0001 per 1K tokens
- **Optimization**: Cache embeddings, batch requests

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Check firewall/network settings
   - Verify credentials in environment
   - Ensure services are running

2. **Performance Issues**
   - Check index usage
   - Monitor query execution times
   - Optimize batch sizes

3. **Migration Failures**
   - Run with --dry-run first
   - Check error logs
   - Migrate in smaller batches

### Debug Commands
```bash
# Test Supabase connection
curl https://your-project.supabase.co/rest/v1/document_embeddings?limit=1 \
  -H "apikey: your_anon_key"

# Test Neo4j connection
cypher-shell -a neo4j+s://your-instance.databases.neo4j.io \
  -u neo4j -p your_password
```

## Best Practices

1. **Security**
   - Use environment variables for credentials
   - Enable RLS in Supabase for production
   - Use secure connections (neo4j+s://)

2. **Performance**
   - Index frequently queried fields
   - Batch operations when possible
   - Monitor and optimize slow queries

3. **Cost Management**
   - Monitor usage regularly
   - Set up alerts for usage limits
   - Optimize embedding generation

## Next Steps

1. **Production Setup**
   - Enable authentication
   - Set up monitoring
   - Configure backups

2. **Advanced Features**
   - Real-time subscriptions (Supabase)
   - Graph algorithms (Neo4j)
   - Hybrid search (vector + graph)

3. **Integration**
   - Connect to existing applications
   - Build APIs on top
   - Add caching layers