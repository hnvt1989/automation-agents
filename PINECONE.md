# Pinecone Migration Plan

## Executive Summary

This document outlines the comprehensive migration strategy from ChromaDB to Pinecone for the automation-agents multi-agent RAG system. The migration maintains all existing functionality while leveraging Pinecone's cloud-native scalability and Supabase for extended metadata management.

## Current State Analysis

### Existing ChromaDB Architecture

**Core Components:**
- **ChromaDB Client** (`src/storage/chromadb_client.py`): Singleton pattern with OpenAI embeddings (`text-embedding-3-small`)
- **Collection Manager** (`src/storage/collection_manager.py`): Manages 3 specialized collections
- **Contextual Chunker** (`src/storage/contextual_chunker.py`): Advanced chunking with document context
- **Graph Knowledge Manager** (`src/storage/graph_knowledge_manager.py`): Neo4j hybrid search integration
- **Performance Monitor** (`src/storage/performance_monitor.py`): Metrics and timing tracking
- **Query Cache** (`src/storage/query_cache.py`): LRU cache (200 items, 600s TTL)

**Current Collections:**
1. **`automation_agents_websites`**: Web content (1500 char chunks, 200 overlap)
2. **`automation_agents_conversations`**: Chat history (500 char chunks, 50 overlap)
3. **`automation_agents_knowledge`**: Documents/files (1000 char chunks, 100 overlap)

**Metadata Schema:**
```python
{
    "source_type": "website|conversation|knowledge",
    "chunk_index": int,
    "total_chunks": int,
    "has_context": bool,
    "original_text": str,
    "file_path": str,
    "url": str,
    "conversation_id": str,
    "indexed_at": str
}
```

**Neo4j Integration:**
- Entity extraction using `graphiti-core`
- Vector indices on entity names and relationship facts
- Hybrid search with Reciprocal Rank Fusion (RRF)

## Target Architecture: Pinecone + Supabase + Neo4j

### Core Design Principles

1. **Cloud-Native Scalability**: Serverless Pinecone indexes for auto-scaling
2. **Metadata Overflow Strategy**: Core metadata in Pinecone, extended in Supabase
3. **Hybrid Search Preservation**: Maintain Neo4j integration with enhanced capabilities
4. **Zero-Downtime Migration**: Parallel systems during transition
5. **Cost Optimization**: Serverless scaling and efficient indexing

### New Architecture Components

#### Pinecone Layer
- **3 Separate Indexes** (1536 dimensions, serverless):
  - `automation-agents-websites`
  - `automation-agents-conversations`
  - `automation-agents-knowledge`

#### Supabase Layer
- **Extended Metadata Table**: `vector_metadata`
- **Collection Management**: `collections_config`
- **Performance Metrics**: `query_performance`
- **Migration Tracking**: `migration_status`

#### Integration Layer
- **Pinecone Client**: Cloud-native vector operations
- **Supabase Client**: Metadata and relational data
- **Hybrid Search Coordinator**: Pinecone + Neo4j fusion

## Implementation Plan

### Phase 1: Foundation Setup

#### 1.1 Environment Configuration
```env
# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_environment

# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_role_key

# Existing Neo4j (unchanged)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# OpenAI (unchanged)
OPENAI_API_KEY=your_openai_api_key
```

#### 1.2 Dependencies Update
```python
# Add to requirements.txt
pinecone-client>=3.0.0
supabase>=2.0.0
asyncpg>=0.29.0  # For Supabase async operations
```

#### 1.3 Supabase Schema Setup
```sql
-- Extended metadata table
CREATE TABLE vector_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vector_id VARCHAR(255) NOT NULL,
    index_name VARCHAR(100) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    chunk_index INTEGER,
    total_chunks INTEGER,
    has_context BOOLEAN DEFAULT FALSE,
    original_text TEXT,
    file_path VARCHAR(500),
    url VARCHAR(1000),
    conversation_id VARCHAR(255),
    indexed_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB,
    UNIQUE(vector_id, index_name)
);

-- Collections configuration
CREATE TABLE collections_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    pinecone_index VARCHAR(100) NOT NULL,
    chunk_size INTEGER NOT NULL,
    chunk_overlap INTEGER NOT NULL,
    embedding_model VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance metrics
CREATE TABLE query_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_type VARCHAR(50) NOT NULL,
    index_name VARCHAR(100) NOT NULL,
    query_time_ms INTEGER NOT NULL,
    result_count INTEGER NOT NULL,
    cache_hit BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Migration tracking
CREATE TABLE migration_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_name VARCHAR(100) NOT NULL,
    total_documents INTEGER NOT NULL,
    migrated_documents INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT
);

-- Indexes for performance
CREATE INDEX idx_vector_metadata_vector_id ON vector_metadata(vector_id);
CREATE INDEX idx_vector_metadata_index_name ON vector_metadata(index_name);
CREATE INDEX idx_vector_metadata_source_type ON vector_metadata(source_type);
CREATE INDEX idx_query_performance_created_at ON query_performance(created_at);
```

### Phase 2: Core Implementation

#### 2.1 Pinecone Client (`src/storage/pinecone_client.py`)
```python
import pinecone
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import logging
from src.core.config import get_settings
from src.storage.performance_monitor import PerformanceMonitor

class PineconeClient:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.settings = get_settings()
            self.pc = Pinecone(api_key=self.settings.PINECONE_API_KEY)
            self.openai_client = OpenAI(api_key=self.settings.OPENAI_API_KEY)
            self.performance_monitor = PerformanceMonitor()
            self.indexes = {}
            self._initialized = True
    
    def get_or_create_index(self, index_name: str, dimension: int = 1536) -> Any:
        """Get existing index or create new serverless index"""
        if index_name not in self.indexes:
            try:
                index = self.pc.Index(index_name)
                self.indexes[index_name] = index
            except:
                # Create serverless index
                self.pc.create_index(
                    name=index_name,
                    dimension=dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.settings.PINECONE_ENVIRONMENT
                    )
                )
                index = self.pc.Index(index_name)
                self.indexes[index_name] = index
        
        return self.indexes[index_name]
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI text-embedding-3-small"""
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return [data.embedding for data in response.data]
    
    async def upsert_vectors(
        self,
        index_name: str,
        vectors: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """Batch upsert vectors to Pinecone index"""
        start_time = time.time()
        index = self.get_or_create_index(index_name)
        
        # Process in batches
        total_upserted = 0
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            try:
                result = index.upsert(vectors=batch)
                total_upserted += result.upserted_count
            except Exception as e:
                logging.error(f"Batch upsert failed: {e}")
                raise
        
        # Track performance
        duration = time.time() - start_time
        self.performance_monitor.record_operation(
            "upsert", index_name, duration, total_upserted
        )
        
        return {"upserted_count": total_upserted, "duration": duration}
    
    async def query_vectors(
        self,
        index_name: str,
        query_vector: List[float],
        filter_dict: Optional[Dict] = None,
        top_k: int = 10,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """Query vectors from Pinecone index"""
        start_time = time.time()
        index = self.get_or_create_index(index_name)
        
        try:
            result = index.query(
                vector=query_vector,
                filter=filter_dict,
                top_k=top_k,
                include_metadata=include_metadata,
                include_values=False
            )
            
            # Track performance
            duration = time.time() - start_time
            self.performance_monitor.record_operation(
                "query", index_name, duration, len(result.matches)
            )
            
            return {
                "matches": result.matches,
                "duration": duration,
                "total_results": len(result.matches)
            }
            
        except Exception as e:
            logging.error(f"Query failed: {e}")
            raise
```

#### 2.2 Supabase Metadata Manager (`src/storage/supabase_metadata.py`)
```python
from supabase import create_client, Client
from typing import List, Dict, Any, Optional
import json
import asyncio
from src.core.config import get_settings

class SupabaseMetadataManager:
    def __init__(self):
        self.settings = get_settings()
        self.client: Client = create_client(
            self.settings.SUPABASE_URL,
            self.settings.SUPABASE_SERVICE_KEY
        )
    
    async def store_metadata(
        self,
        vector_id: str,
        index_name: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store extended metadata in Supabase"""
        try:
            result = self.client.table('vector_metadata').upsert({
                "vector_id": vector_id,
                "index_name": index_name,
                "source_type": metadata.get("source_type"),
                "chunk_index": metadata.get("chunk_index"),
                "total_chunks": metadata.get("total_chunks"),
                "has_context": metadata.get("has_context", False),
                "original_text": metadata.get("original_text"),
                "file_path": metadata.get("file_path"),
                "url": metadata.get("url"),
                "conversation_id": metadata.get("conversation_id"),
                "metadata": json.dumps(metadata)
            }).execute()
            
            return result.data[0] if result.data else {}
            
        except Exception as e:
            logging.error(f"Metadata storage failed: {e}")
            raise
    
    async def get_metadata(
        self,
        vector_ids: List[str],
        index_name: str
    ) -> Dict[str, Dict[str, Any]]:
        """Retrieve metadata for multiple vectors"""
        try:
            result = self.client.table('vector_metadata').select('*').in_(
                'vector_id', vector_ids
            ).eq('index_name', index_name).execute()
            
            metadata_map = {}
            for row in result.data:
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                metadata.update({
                    "source_type": row['source_type'],
                    "chunk_index": row['chunk_index'],
                    "total_chunks": row['total_chunks'],
                    "has_context": row['has_context'],
                    "original_text": row['original_text'],
                    "file_path": row['file_path'],
                    "url": row['url'],
                    "conversation_id": row['conversation_id'],
                    "indexed_at": row['indexed_at']
                })
                metadata_map[row['vector_id']] = metadata
            
            return metadata_map
            
        except Exception as e:
            logging.error(f"Metadata retrieval failed: {e}")
            return {}
```

#### 2.3 Pinecone Collection Manager (`src/storage/pinecone_collection_manager.py`)
```python
from typing import List, Dict, Any, Optional, Tuple
import hashlib
import time
from src.storage.pinecone_client import PineconeClient
from src.storage.supabase_metadata import SupabaseMetadataManager
from src.storage.contextual_chunker import ContextualChunker
from src.storage.query_cache import QueryCache

class PineconeCollectionManager:
    def __init__(self):
        self.pinecone_client = PineconeClient()
        self.metadata_manager = SupabaseMetadataManager()
        self.contextual_chunker = ContextualChunker()
        self.cache = QueryCache()
        
        # Collection configurations
        self.collections = {
            "websites": {
                "index_name": "automation-agents-websites",
                "chunk_size": 1500,
                "chunk_overlap": 200
            },
            "conversations": {
                "index_name": "automation-agents-conversations", 
                "chunk_size": 500,
                "chunk_overlap": 50
            },
            "knowledge": {
                "index_name": "automation-agents-knowledge",
                "chunk_size": 1000,
                "chunk_overlap": 100
            }
        }
    
    async def add_documents(
        self,
        collection_type: str,
        documents: List[Dict[str, Any]],
        use_contextual_chunking: bool = True
    ) -> Dict[str, Any]:
        """Add documents to Pinecone collection with Supabase metadata"""
        
        if collection_type not in self.collections:
            raise ValueError(f"Unknown collection type: {collection_type}")
        
        config = self.collections[collection_type]
        index_name = config["index_name"]
        
        # Process documents
        vectors_to_upsert = []
        metadata_to_store = []
        
        for doc in documents:
            # Generate chunks
            if use_contextual_chunking:
                chunks = await self.contextual_chunker.chunk_with_context(
                    doc["content"],
                    config["chunk_size"],
                    config["chunk_overlap"],
                    doc.get("context_template")
                )
            else:
                chunks = self.contextual_chunker.chunk_text(
                    doc["content"],
                    config["chunk_size"],
                    config["chunk_overlap"]
                )
            
            # Generate embeddings
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = self.pinecone_client.generate_embeddings(chunk_texts)
            
            # Prepare vectors and metadata
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vector_id = self._generate_vector_id(doc, i)
                
                # Core metadata for Pinecone (size-limited)
                pinecone_metadata = {
                    "source_type": collection_type,
                    "chunk_index": i,
                    "has_context": chunk.get("has_context", False)
                }
                
                # Extended metadata for Supabase
                extended_metadata = {
                    **pinecone_metadata,
                    "total_chunks": len(chunks),
                    "original_text": chunk["original_text"],
                    "file_path": doc.get("file_path"),
                    "url": doc.get("url"),
                    "conversation_id": doc.get("conversation_id")
                }
                
                vectors_to_upsert.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": pinecone_metadata
                })
                
                metadata_to_store.append({
                    "vector_id": vector_id,
                    "index_name": index_name,
                    "metadata": extended_metadata
                })
        
        # Upsert to Pinecone
        pinecone_result = await self.pinecone_client.upsert_vectors(
            index_name, vectors_to_upsert
        )
        
        # Store metadata in Supabase
        for metadata in metadata_to_store:
            await self.metadata_manager.store_metadata(
                metadata["vector_id"],
                metadata["index_name"],
                metadata["metadata"]
            )
        
        return {
            "collection_type": collection_type,
            "documents_processed": len(documents),
            "chunks_created": len(vectors_to_upsert),
            "pinecone_result": pinecone_result
        }
    
    async def search_collection(
        self,
        collection_type: str,
        query_text: str,
        filter_dict: Optional[Dict] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Search Pinecone collection with metadata enrichment"""
        
        # Check cache first
        cache_key = f"{collection_type}:{hashlib.md5(query_text.encode()).hexdigest()}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        if collection_type not in self.collections:
            raise ValueError(f"Unknown collection type: {collection_type}")
        
        config = self.collections[collection_type]
        index_name = config["index_name"]
        
        # Generate query embedding
        query_embedding = self.pinecone_client.generate_embeddings([query_text])[0]
        
        # Search Pinecone
        search_result = await self.pinecone_client.query_vectors(
            index_name, query_embedding, filter_dict, top_k
        )
        
        # Enrich with Supabase metadata
        vector_ids = [match.id for match in search_result["matches"]]
        metadata_map = await self.metadata_manager.get_metadata(vector_ids, index_name)
        
        # Combine results
        enriched_results = []
        for match in search_result["matches"]:
            result = {
                "id": match.id,
                "score": match.score,
                "metadata": {**match.metadata, **metadata_map.get(match.id, {})}
            }
            enriched_results.append(result)
        
        # Cache result
        self.cache.set(cache_key, enriched_results)
        
        return enriched_results
    
    def _generate_vector_id(self, doc: Dict[str, Any], chunk_index: int) -> str:
        """Generate unique vector ID"""
        base_id = doc.get("id") or doc.get("file_path") or doc.get("url") or str(time.time())
        return f"{hashlib.md5(base_id.encode()).hexdigest()}_{chunk_index}"
```

### Phase 3: Migration Utilities

#### 3.1 Data Migration Script (`scripts/migrate_chromadb_to_pinecone.py`)
```python
import asyncio
import logging
from typing import Dict, List, Any
from src.storage.chromadb_client import ChromaDBClient
from src.storage.pinecone_collection_manager import PineconeCollectionManager
from src.storage.supabase_metadata import SupabaseMetadataManager

class ChromaDBToPineconeMigrator:
    def __init__(self):
        self.chromadb_client = ChromaDBClient()
        self.pinecone_manager = PineconeCollectionManager()
        self.supabase_manager = SupabaseMetadataManager()
    
    async def migrate_collection(self, collection_name: str) -> Dict[str, Any]:
        """Migrate single ChromaDB collection to Pinecone"""
        
        logging.info(f"Starting migration for collection: {collection_name}")
        
        # Get ChromaDB collection
        chroma_collection = self.chromadb_client.get_collection(collection_name)
        
        # Get all documents from ChromaDB
        result = chroma_collection.get(
            include=["documents", "metadatas", "embeddings"]
        )
        
        total_docs = len(result["ids"])
        migrated_count = 0
        batch_size = 50
        
        # Update migration status
        await self._update_migration_status(
            collection_name, total_docs, 0, "in_progress"
        )
        
        try:
            # Process in batches
            for i in range(0, total_docs, batch_size):
                batch_ids = result["ids"][i:i + batch_size]
                batch_docs = result["documents"][i:i + batch_size]
                batch_metadata = result["metadatas"][i:i + batch_size]
                batch_embeddings = result["embeddings"][i:i + batch_size]
                
                # Convert to Pinecone format
                vectors_to_upsert = []
                metadata_to_store = []
                
                for j, (doc_id, doc_text, metadata, embedding) in enumerate(
                    zip(batch_ids, batch_docs, batch_metadata, batch_embeddings)
                ):
                    # Prepare Pinecone vector
                    pinecone_metadata = {
                        "source_type": metadata.get("source_type"),
                        "chunk_index": metadata.get("chunk_index", 0),
                        "has_context": metadata.get("has_context", False)
                    }
                    
                    vectors_to_upsert.append({
                        "id": doc_id,
                        "values": embedding,
                        "metadata": pinecone_metadata
                    })
                    
                    # Prepare Supabase metadata
                    metadata_to_store.append({
                        "vector_id": doc_id,
                        "index_name": self._get_pinecone_index_name(collection_name),
                        "metadata": metadata
                    })
                
                # Upsert to Pinecone
                await self.pinecone_manager.pinecone_client.upsert_vectors(
                    self._get_pinecone_index_name(collection_name),
                    vectors_to_upsert
                )
                
                # Store in Supabase
                for metadata in metadata_to_store:
                    await self.supabase_manager.store_metadata(
                        metadata["vector_id"],
                        metadata["index_name"],
                        metadata["metadata"]
                    )
                
                migrated_count += len(batch_ids)
                
                # Update progress
                await self._update_migration_status(
                    collection_name, total_docs, migrated_count, "in_progress"
                )
                
                logging.info(f"Migrated {migrated_count}/{total_docs} documents")
            
            # Mark as completed
            await self._update_migration_status(
                collection_name, total_docs, migrated_count, "completed"
            )
            
            return {
                "collection_name": collection_name,
                "total_documents": total_docs,
                "migrated_documents": migrated_count,
                "status": "completed"
            }
            
        except Exception as e:
            logging.error(f"Migration failed for {collection_name}: {e}")
            await self._update_migration_status(
                collection_name, total_docs, migrated_count, "failed", str(e)
            )
            raise
    
    def _get_pinecone_index_name(self, chroma_collection_name: str) -> str:
        """Map ChromaDB collection names to Pinecone index names"""
        mapping = {
            "automation_agents_websites": "automation-agents-websites",
            "automation_agents_conversations": "automation-agents-conversations",
            "automation_agents_knowledge": "automation-agents-knowledge"
        }
        return mapping.get(chroma_collection_name, chroma_collection_name.replace("_", "-"))
    
    async def _update_migration_status(
        self,
        collection_name: str,
        total_docs: int,
        migrated_docs: int,
        status: str,
        error_message: str = None
    ):
        """Update migration status in Supabase"""
        try:
            self.supabase_manager.client.table('migration_status').upsert({
                "collection_name": collection_name,
                "total_documents": total_docs,
                "migrated_documents": migrated_docs,
                "status": status,
                "error_message": error_message,
                "started_at": "NOW()" if status == "in_progress" else None,
                "completed_at": "NOW()" if status in ["completed", "failed"] else None
            }).execute()
        except Exception as e:
            logging.error(f"Failed to update migration status: {e}")

async def main():
    """Run complete migration"""
    migrator = ChromaDBToPineconeMigrator()
    
    collections_to_migrate = [
        "automation_agents_websites",
        "automation_agents_conversations", 
        "automation_agents_knowledge"
    ]
    
    for collection in collections_to_migrate:
        try:
            result = await migrator.migrate_collection(collection)
            print(f"Migration completed for {collection}: {result}")
        except Exception as e:
            print(f"Migration failed for {collection}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Phase 4: Agent Integration Updates

#### 4.1 Updated RAG Agent (`src/agents/rag.py` modifications)
```python
# Replace ChromaDB imports with Pinecone equivalents
from src.storage.pinecone_collection_manager import PineconeCollectionManager
from src.storage.graph_knowledge_manager import GraphKnowledgeManager

# Update agent tools to use Pinecone backend
@agent.tool
async def search_knowledge_base(
    ctx: RunContext[RAGDeps], 
    query: str, 
    max_results: int = 5
) -> str:
    """Search across all collections using Pinecone"""
    try:
        pinecone_manager = PineconeCollectionManager()
        
        # Search all collections in parallel
        tasks = []
        for collection_type in ["websites", "conversations", "knowledge"]:
            task = pinecone_manager.search_collection(
                collection_type, query, top_k=max_results
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Combine and rank results
        all_results = []
        for collection_results in results:
            all_results.extend(collection_results)
        
        # Sort by score and take top results
        all_results.sort(key=lambda x: x["score"], reverse=True)
        top_results = all_results[:max_results]
        
        # Format results
        formatted_results = []
        for result in top_results:
            metadata = result["metadata"]
            formatted_results.append({
                "content": metadata.get("original_text", ""),
                "source": metadata.get("file_path") or metadata.get("url", "Unknown"),
                "type": metadata.get("source_type", "Unknown"),
                "score": result["score"]
            })
        
        return json.dumps(formatted_results, indent=2)
        
    except Exception as e:
        return f"Search failed: {str(e)}"
```

### Phase 5: Testing Strategy

#### 5.1 Unit Tests (`tests/unit/test_pinecone_integration.py`)
```python
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.storage.pinecone_client import PineconeClient
from src.storage.pinecone_collection_manager import PineconeCollectionManager

class TestPineconeIntegration:
    
    @pytest.fixture
    def mock_pinecone_client(self):
        with patch('src.storage.pinecone_client.Pinecone') as mock:
            yield mock
    
    @pytest.fixture
    def pinecone_client(self, mock_pinecone_client):
        return PineconeClient()
    
    @pytest.mark.asyncio
    async def test_upsert_vectors(self, pinecone_client):
        """Test vector upsert functionality"""
        vectors = [
            {
                "id": "test_1",
                "values": [0.1] * 1536,
                "metadata": {"source_type": "test"}
            }
        ]
        
        with patch.object(pinecone_client, 'get_or_create_index') as mock_index:
            mock_index.return_value.upsert.return_value.upserted_count = 1
            
            result = await pinecone_client.upsert_vectors("test-index", vectors)
            
            assert result["upserted_count"] == 1
            assert "duration" in result
    
    @pytest.mark.asyncio
    async def test_query_vectors(self, pinecone_client):
        """Test vector querying functionality"""
        query_vector = [0.1] * 1536
        
        mock_match = Mock()
        mock_match.id = "test_1"
        mock_match.score = 0.95
        mock_match.metadata = {"source_type": "test"}
        
        with patch.object(pinecone_client, 'get_or_create_index') as mock_index:
            mock_index.return_value.query.return_value.matches = [mock_match]
            
            result = await pinecone_client.query_vectors(
                "test-index", query_vector, top_k=5
            )
            
            assert len(result["matches"]) == 1
            assert result["matches"][0].id == "test_1"
            assert result["matches"][0].score == 0.95

    @pytest.mark.asyncio
    async def test_collection_search_with_cache(self):
        """Test collection search with caching"""
        manager = PineconeCollectionManager()
        
        with patch.object(manager.cache, 'get') as mock_cache_get, \
             patch.object(manager.cache, 'set') as mock_cache_set, \
             patch.object(manager, 'pinecone_client') as mock_client, \
             patch.object(manager, 'metadata_manager') as mock_metadata:
            
            # Test cache miss
            mock_cache_get.return_value = None
            mock_client.generate_embeddings.return_value = [[0.1] * 1536]
            mock_client.query_vectors.return_value = {
                "matches": [Mock(id="test_1", score=0.95, metadata={})]
            }
            mock_metadata.get_metadata.return_value = {
                "test_1": {"original_text": "test content"}
            }
            
            result = await manager.search_collection("knowledge", "test query")
            
            assert len(result) == 1
            assert result[0]["id"] == "test_1"
            mock_cache_set.assert_called_once()
```

#### 5.2 Integration Tests (`tests/integration/test_migration.py`)
```python
import pytest
import asyncio
from scripts.migrate_chromadb_to_pinecone import ChromaDBToPineconeMigrator

class TestMigration:
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_migration(self):
        """Test complete migration from ChromaDB to Pinecone"""
        migrator = ChromaDBToPineconeMigrator()
        
        # Test with small dataset
        test_collection = "test_migration_collection"
        
        try:
            result = await migrator.migrate_collection(test_collection)
            
            assert result["status"] == "completed"
            assert result["migrated_documents"] > 0
            assert result["migrated_documents"] == result["total_documents"]
            
        except Exception as e:
            pytest.fail(f"Migration test failed: {e}")
    
    @pytest.mark.integration 
    @pytest.mark.asyncio
    async def test_search_parity(self):
        """Test that Pinecone search results match ChromaDB results"""
        # This would compare search results between old and new systems
        # to ensure migration preserved semantic search quality
        pass
```

### Phase 6: Configuration Updates

#### 6.1 Updated CLAUDE.md Section
```markdown
## Pinecone + Supabase Configuration

### Environment Variables
```env
# Pinecone Configuration  
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=us-east-1-aws  # or your preferred region

# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_role_key

# Neo4j (unchanged)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# OpenAI (unchanged)
OPENAI_API_KEY=your_openai_api_key
```

### Pinecone Indexes
- **automation-agents-websites**: Web content indexing
- **automation-agents-conversations**: Chat history indexing  
- **automation-agents-knowledge**: Document/file indexing

### Migration Commands
```bash
# Setup Supabase schema
python scripts/setup_supabase_schema.py

# Run migration from ChromaDB
python scripts/migrate_chromadb_to_pinecone.py

# Validate migration
python scripts/validate_migration.py
```
```

## Migration Timeline and Costs

### Timeline Estimate
- **Phase 1 (Setup)**: 2-3 days
- **Phase 2 (Core Implementation)**: 5-7 days  
- **Phase 3 (Migration Utilities)**: 3-4 days
- **Phase 4 (Agent Integration)**: 2-3 days
- **Phase 5 (Testing)**: 3-5 days
- **Phase 6 (Deployment)**: 1-2 days

**Total Estimated Timeline**: 16-24 days

### Cost Considerations

#### Pinecone Costs (Serverless)
- **Storage**: ~$0.00005 per 1K vectors per month
- **Queries**: ~$0.0004 per 1K queries
- **Estimated Monthly**: $10-50 for typical usage

#### Supabase Costs  
- **Database**: Free tier for < 500MB, then $25/month
- **Storage**: $0.021 per GB per month
- **Estimated Monthly**: $0-25 for metadata storage

#### Total Monthly Operating Cost
- **Current (ChromaDB)**: $0 (self-hosted)
- **New (Pinecone + Supabase)**: $10-75/month

## Risk Mitigation

### Data Safety
- **Backup Strategy**: Full ChromaDB export before migration
- **Parallel Systems**: Run both systems during transition
- **Validation**: Automated testing of search result parity
- **Rollback Plan**: Keep ChromaDB active for emergency fallback

### Performance Considerations
- **Network Latency**: Cloud-hosted vs local ChromaDB
- **Rate Limits**: Pinecone API limits and batching
- **Cost Monitoring**: Usage tracking and alerts

### Technical Risks
- **Metadata Size Limits**: Pinecone 40KB metadata limit handled by Supabase overflow
- **API Dependencies**: Network reliability and API availability  
- **Embedding Consistency**: Ensuring identical OpenAI embedding generation

## Success Metrics

### Performance Targets
- **Search Latency**: < 500ms (vs current ChromaDB performance)
- **Search Quality**: Maintain >95% result relevance parity
- **Uptime**: >99.9% availability
- **Cost Efficiency**: Stay within $75/month budget

### Migration Success Criteria
- **Data Integrity**: 100% data migration with validation
- **Feature Parity**: All existing RAG functionality preserved
- **Zero Downtime**: Seamless transition for users
- **Documentation**: Complete migration documentation and runbooks

## Next Steps

1. **Environment Setup**: Create Pinecone and Supabase accounts
2. **Proof of Concept**: Implement core Pinecone client with sample data
3. **Supabase Schema**: Set up metadata tables and relationships
4. **Migration Script**: Build and test data migration utilities
5. **Agent Integration**: Update RAG agents to use new backend
6. **Testing Phase**: Comprehensive testing and validation
7. **Production Migration**: Execute migration with monitoring
8. **Documentation**: Update all documentation and runbooks

This migration will modernize the vector storage infrastructure while maintaining all existing functionality and improving scalability, performance, and operational capabilities.