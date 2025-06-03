Storage
=======

The storage module provides database clients and storage management for the automation agents system, including vector storage with ChromaDB and file-based storage.

ChromaDB Client (:mod:`src.storage.chromadb_client`)
----------------------------------------------------

The ChromaDB client provides vector database functionality for storing and searching document embeddings.

.. automodule:: src.storage.chromadb_client
   :members:
   :undoc-members:
   :show-inheritance:

**Key Features:**

- Vector storage and similarity search
- Document embedding and retrieval
- Collection management and statistics
- Persistent storage with configurable backend

**Usage Example:**

.. code-block:: python

   from src.storage.chromadb_client import get_chromadb_client

   # Get client instance
   client = get_chromadb_client()

   # Add documents
   documents = ["Document content 1", "Document content 2"]
   metadatas = [{"source": "file1.txt"}, {"source": "file2.txt"}]
   ids = ["doc1", "doc2"]
   
   client.add_documents(documents, metadatas, ids)

   # Search for similar documents
   results = client.query(
       query_texts=["search query"],
       n_results=5
   )

ChromaDB Integration
-------------------

**Collection Management:**

The system uses a single collection for all documents with rich metadata:

.. code-block:: python

   # Collection configuration
   collection_config = {
       "name": "automation_agents_knowledge",
       "embedding_function": "default",  # OpenAI embeddings
       "metadata": {
           "description": "Knowledge base for automation agents",
           "created_at": "2024-01-01T00:00:00Z"
       }
   }

**Document Schema:**

Documents stored in ChromaDB follow this schema:

.. code-block:: python

   document_schema = {
       "id": "unique_document_identifier",
       "document": "text_content_of_document", 
       "metadata": {
           "source": "file_path_or_url",
           "chunk_index": 0,  # For large documents split into chunks
           "file_type": "py|md|txt|json",
           "indexed_at": "2024-01-01T12:00:00Z",
           "file_size": 1024,  # in bytes
           "checksum": "md5_hash_of_content"
       },
       "embedding": [0.1, 0.2, 0.3, ...]  # Vector embedding
   }

**Advanced Search Features:**

.. code-block:: python

   # Filtered search with metadata
   results = client.query(
       query_texts=["authentication methods"],
       n_results=10,
       where={"file_type": "py"},  # Only Python files
       include=["documents", "metadatas", "distances"]
   )

   # Multi-query search
   results = client.query(
       query_texts=[
           "error handling",
           "exception management", 
           "try catch blocks"
       ],
       n_results=5
   )

**Collection Statistics:**

.. code-block:: python

   # Get detailed statistics
   stats = client.get_collection_stats()
   print(f"Total documents: {stats['count']}")
   print(f"Collection name: {stats['name']}")
   print(f"Embedding function: {stats['embedding_function']}")

Storage Configuration
--------------------

**ChromaDB Settings:**

Configure ChromaDB through the application settings:

.. code-block:: python

   # In src/core/config.py
   class Settings(BaseSettings):
       chroma_persist_directory: Path = Field(
           default_factory=lambda: Path(__file__).parent.parent.parent / "chroma_db"
       )
       chroma_collection_name: str = "automation_agents_knowledge"
       chroma_embedding_function: str = "openai"  # or "sentence_transformers"

**Persistence:**

ChromaDB data is persisted to disk automatically:

.. code-block:: python

   # Data is stored in the configured directory
   # Structure:
   # chroma_db/
   # ├── chroma.sqlite3          # Metadata database
   # ├── index/                  # Vector index files  
   # └── collections/            # Collection data

Document Indexing Workflows
---------------------------

**Single File Indexing:**

.. code-block:: python

   async def index_single_file(file_path: str) -> Dict[str, Any]:
       """Index a single file into the knowledge base."""
       
       client = get_chromadb_client()
       
       # Read file content
       with open(file_path, 'r', encoding='utf-8') as f:
           content = f.read()
       
       # Create metadata
       import os
       from datetime import datetime
       
       metadata = {
           "source": file_path,
           "file_type": os.path.splitext(file_path)[1][1:],  # Remove dot
           "indexed_at": datetime.now().isoformat(),
           "file_size": os.path.getsize(file_path)
       }
       
       # Generate unique ID
       import hashlib
       doc_id = hashlib.md5(file_path.encode()).hexdigest()
       
       # Add to collection
       client.add_documents(
           documents=[content],
           metadatas=[metadata],
           ids=[doc_id]
       )
       
       return {"success": True, "doc_id": doc_id, "metadata": metadata}

**Directory Indexing:**

.. code-block:: python

   async def index_directory(directory_path: str, 
                           file_extensions: List[str] = None) -> Dict[str, Any]:
       """Index all files in a directory."""
       
       import os
       from pathlib import Path
       
       if file_extensions is None:
           file_extensions = ['.py', '.md', '.txt', '.json', '.yaml', '.yml']
       
       indexed_files = []
       failed_files = []
       
       for root, dirs, files in os.walk(directory_path):
           for file in files:
               file_path = os.path.join(root, file)
               file_ext = os.path.splitext(file)[1]
               
               if file_ext in file_extensions:
                   try:
                       result = await index_single_file(file_path)
                       indexed_files.append(result)
                   except Exception as e:
                       failed_files.append({"file": file_path, "error": str(e)})
       
       return {
           "indexed_count": len(indexed_files),
           "failed_count": len(failed_files),
           "indexed_files": indexed_files,
           "failed_files": failed_files
       }

**Large Document Chunking:**

.. code-block:: python

   def chunk_large_document(content: str, 
                           chunk_size: int = 1000, 
                           overlap: int = 100) -> List[str]:
       """Split large documents into overlapping chunks."""
       
       if len(content) <= chunk_size:
           return [content]
       
       chunks = []
       start = 0
       
       while start < len(content):
           end = start + chunk_size
           
           # Try to break at word boundary
           if end < len(content):
               last_space = content.rfind(' ', start, end)
               if last_space > start:
                   end = last_space
           
           chunk = content[start:end].strip()
           if chunk:
               chunks.append(chunk)
           
           start = end - overlap
       
       return chunks

   async def index_large_file(file_path: str) -> Dict[str, Any]:
       """Index a large file by splitting into chunks."""
       
       with open(file_path, 'r', encoding='utf-8') as f:
           content = f.read()
       
       chunks = chunk_large_document(content)
       client = get_chromadb_client()
       
       documents = []
       metadatas = []
       ids = []
       
       base_metadata = {
           "source": file_path,
           "file_type": os.path.splitext(file_path)[1][1:],
           "indexed_at": datetime.now().isoformat(),
           "total_chunks": len(chunks)
       }
       
       for i, chunk in enumerate(chunks):
           chunk_metadata = base_metadata.copy()
           chunk_metadata["chunk_index"] = i
           
           chunk_id = f"{hashlib.md5(file_path.encode()).hexdigest()}_{i}"
           
           documents.append(chunk)
           metadatas.append(chunk_metadata)
           ids.append(chunk_id)
       
       client.add_documents(documents, metadatas, ids)
       
       return {
           "success": True,
           "chunks_created": len(chunks),
           "file_path": file_path
       }

Search and Retrieval
--------------------

**Semantic Search:**

.. code-block:: python

   async def semantic_search(query: str, 
                           n_results: int = 5,
                           file_type_filter: str = None) -> List[Dict]:
       """Perform semantic search on the knowledge base."""
       
       client = get_chromadb_client()
       
       # Build filter criteria
       where_clause = {}
       if file_type_filter:
           where_clause["file_type"] = file_type_filter
       
       # Perform search
       results = client.query(
           query_texts=[query],
           n_results=n_results,
           where=where_clause if where_clause else None,
           include=["documents", "metadatas", "distances"]
       )
       
       # Format results
       formatted_results = []
       if results['ids'] and results['ids'][0]:
           for i, doc_id in enumerate(results['ids'][0]):
               result = {
                   "id": doc_id,
                   "content": results['documents'][0][i],
                   "metadata": results['metadatas'][0][i],
                   "similarity": 1 - results['distances'][0][i],  # Convert distance to similarity
                   "relevance_score": results['distances'][0][i]
               }
               formatted_results.append(result)
       
       return formatted_results

**Contextual Retrieval:**

.. code-block:: python

   async def get_context_for_query(query: str, 
                                  max_context_length: int = 4000) -> str:
       """Get relevant context for a query, respecting length limits."""
       
       # Get initial results
       results = await semantic_search(query, n_results=10)
       
       context_parts = []
       current_length = 0
       
       for result in results:
           content = result['content']
           source = result['metadata'].get('source', 'unknown')
           
           # Add source attribution
           attributed_content = f"From {source}:\n{content}\n"
           
           if current_length + len(attributed_content) <= max_context_length:
               context_parts.append(attributed_content)
               current_length += len(attributed_content)
           else:
               # Truncate to fit
               remaining_space = max_context_length - current_length
               if remaining_space > 100:  # Only add if meaningful space
                   truncated = attributed_content[:remaining_space-3] + "..."
                   context_parts.append(truncated)
               break
       
       return "\n---\n".join(context_parts)

File-Based Storage
-----------------

**YAML Storage:**

The system uses YAML files for structured data storage:

.. code-block:: python

   # Example YAML structures

   # tasks.yaml
   tasks_schema = [
       {
           "id": "task_001",
           "title": "Implement authentication",
           "description": "Add user authentication system",
           "status": "in_progress",  # pending, in_progress, completed
           "priority": "high",       # low, medium, high
           "due_date": "2024-03-15",
           "created_at": "2024-03-01T10:00:00Z",
           "tags": ["auth", "security", "backend"]
       }
   ]

   # meetings.yaml
   meetings_schema = [
       {
           "date": "2024-03-15",
           "time": "14:00",
           "event": "Sprint planning meeting",
           "duration": "1 hour",
           "attendees": ["team_lead", "developers"],
           "location": "Conference Room A"
       }
   ]

   # daily_logs.yaml
   logs_schema = [
       {
           "date": "2024-03-15",
           "task_id": "task_001", 
           "hours": 3.5,
           "description": "Implemented OAuth integration",
           "logged_at": "2024-03-15T17:00:00Z"
       }
   ]

**File Operations:**

.. code-block:: python

   import yaml
   from pathlib import Path
   from typing import Any, List, Dict

   def load_yaml(file_path: str) -> Any:
       """Load data from YAML file."""
       path = Path(file_path)
       if not path.exists():
           return None
       
       with open(path, 'r', encoding='utf-8') as f:
           return yaml.safe_load(f)

   def save_yaml(data: Any, file_path: str) -> None:
       """Save data to YAML file."""
       path = Path(file_path)
       path.parent.mkdir(parents=True, exist_ok=True)
       
       with open(path, 'w', encoding='utf-8') as f:
           yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

   def append_to_yaml_list(item: Dict, file_path: str) -> None:
       """Append item to YAML list file."""
       data = load_yaml(file_path) or []
       data.append(item)
       save_yaml(data, file_path)

Backup and Recovery
------------------

**Database Backup:**

.. code-block:: python

   import shutil
   from datetime import datetime

   def backup_chromadb(backup_dir: str = "backups") -> str:
       """Create backup of ChromaDB data."""
       
       settings = get_settings()
       source_dir = settings.chroma_persist_directory
       
       timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       backup_path = Path(backup_dir) / f"chromadb_backup_{timestamp}"
       
       # Copy entire ChromaDB directory
       shutil.copytree(source_dir, backup_path)
       
       return str(backup_path)

   def restore_chromadb(backup_path: str) -> bool:
       """Restore ChromaDB from backup."""
       
       settings = get_settings()
       target_dir = settings.chroma_persist_directory
       
       try:
           # Remove current data
           if target_dir.exists():
               shutil.rmtree(target_dir)
           
           # Restore from backup
           shutil.copytree(backup_path, target_dir)
           return True
           
       except Exception as e:
           print(f"Restore failed: {e}")
           return False

**Data Migration:**

.. code-block:: python

   async def migrate_documents(old_collection: str, new_collection: str) -> Dict:
       """Migrate documents between collections."""
       
       # This is a conceptual example
       # Actual implementation would depend on specific migration needs
       
       old_client = ChromaDBClient(collection_name=old_collection)
       new_client = ChromaDBClient(collection_name=new_collection)
       
       # Get all documents from old collection
       all_docs = old_client.get_documents()
       
       # Migrate in batches
       batch_size = 100
       migrated_count = 0
       
       for i in range(0, len(all_docs['ids']), batch_size):
           batch_ids = all_docs['ids'][i:i+batch_size]
           batch_docs = all_docs['documents'][i:i+batch_size]  
           batch_metadata = all_docs['metadatas'][i:i+batch_size]
           
           new_client.add_documents(batch_docs, batch_metadata, batch_ids)
           migrated_count += len(batch_ids)
       
       return {"migrated_documents": migrated_count}