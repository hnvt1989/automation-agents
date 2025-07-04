#!/usr/bin/env python3
"""Index documents to cloud services (Supabase + Neo4j Aura) without embeddings."""

import asyncio
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv("local.env")

from src.storage.supabase_vector import SupabaseVectorClient
from src.storage.neo4j_cloud import get_neo4j_cloud_client
from src.storage.contextual_chunker import ContextualChunker
from src.utils.logging import log_info, log_error, log_warning


class CloudDocumentIndexer:
    """Index documents to cloud services without vector embeddings in Neo4j."""
    
    def __init__(self, collection_name: str = "knowledge_base"):
        """Initialize the cloud indexer."""
        self.collection_name = collection_name
        self.processed_files = set()
        self.failed_files = []
        
        # Initialize Supabase vector client
        self.vector_client = SupabaseVectorClient(collection_name)
        log_info(f"Using Supabase collection: {collection_name}")
        
        # Initialize Neo4j cloud client (no embeddings)
        try:
            self.graph_client = get_neo4j_cloud_client()
            log_info("Connected to Neo4j Aura cloud")
        except Exception as e:
            log_error(f"Failed to connect to Neo4j: {e}")
            self.graph_client = None
        
        # Initialize contextual chunker
        self.chunker = ContextualChunker()
    
    def _generate_document_id(self, file_path: str) -> str:
        """Generate unique document ID."""
        return hashlib.md5(file_path.encode()).hexdigest()
    
    async def index_file(self, file_path: Path, force_reindex: bool = False) -> bool:
        """Index a single file to cloud services."""
        try:
            log_info(f"Indexing file: {file_path}")
            
            # Check if already indexed
            doc_id = self._generate_document_id(str(file_path))
            
            if not force_reindex:
                # Check if exists in Supabase
                existing = self.vector_client.client.table("document_embeddings") \
                    .select("document_id") \
                    .eq("collection_name", self.collection_name) \
                    .eq("document_id", doc_id) \
                    .limit(1) \
                    .execute()
                
                if existing.data:
                    log_info(f"  Already indexed: {file_path} (use --force to reindex)")
                    return True
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract title
            title = None
            if content.startswith('#'):
                title_match = re.match(r'^#\s+(.+)$', content, re.MULTILINE)
                if title_match:
                    title = title_match.group(1).strip()
            
            # Prepare metadata
            metadata = {
                "source": str(file_path),
                "file_path": str(file_path),
                "file_type": file_path.suffix,
                "document_type": "knowledge_base",
                "indexed_at": datetime.now().isoformat(),
                "title": title or file_path.stem
            }
            
            # Extract date if present
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file_path.stem)
            if date_match:
                metadata["document_date"] = date_match.group(1)
            
            # 1. Add to vector storage (Supabase)
            log_info(f"  Chunking content...")
            
            # Use contextual chunking
            chunks_with_context = self.chunker.create_contextual_chunks(
                content,
                chunk_size=1000,
                chunk_overlap=200,
                context_info={
                    'source_type': 'knowledge_base',
                    'filename': file_path.name,
                    'category': metadata['document_type'],
                    'document_type': metadata['file_type'],
                    'title': title or file_path.stem
                },
                use_llm_context=False
            )
            
            # Prepare chunks for vector storage
            chunk_texts = []
            chunk_metadatas = []
            chunk_ids = []
            
            for i, chunk in enumerate(chunks_with_context):
                chunk_texts.append(chunk.contextual_text)
                
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunk_index": i,
                    "total_chunks": len(chunks_with_context),
                    "has_context": True,
                    "original_content": chunk.original_text[:200]
                })
                chunk_metadatas.append(chunk_metadata)
                
                chunk_ids.append(f"{doc_id}_chunk_{i}")
            
            # Add to vector storage
            self.vector_client.add_documents(
                documents=chunk_texts,
                metadatas=chunk_metadatas,
                ids=chunk_ids
            )
            
            log_info(f"  Added {len(chunks_with_context)} chunks to Supabase")
            
            # 2. Add to knowledge graph (Neo4j Aura) - WITHOUT embeddings
            if self.graph_client:
                log_info(f"  Adding to Neo4j graph...")
                
                # Create document node
                doc_properties = {
                    "id": doc_id,
                    "title": title or file_path.stem,
                    "path": str(file_path),
                    "type": metadata["document_type"],
                    "indexed_at": metadata["indexed_at"],
                    "chunk_count": len(chunks_with_context)
                }
                
                if "document_date" in metadata:
                    doc_properties["date"] = metadata["document_date"]
                
                # Use MERGE to avoid duplicates
                query = """
                MERGE (d:Document {id: $id})
                SET d += $props
                RETURN d
                """
                self.graph_client.execute_query(query, {"id": doc_id, "props": doc_properties})
                
                # Extract and create simple entities (no embeddings)
                entities = self._extract_entities(content, title)
                
                for entity in entities:
                    # Create entity without embeddings
                    entity_query = """
                    MERGE (e:Entity {id: $id})
                    SET e.name = $name, e.type = $type
                    RETURN e
                    """
                    self.graph_client.execute_query(entity_query, {
                        "id": entity["id"],
                        "name": entity["name"],
                        "type": entity["type"]
                    })
                    
                    # Create relationship
                    rel_query = """
                    MATCH (d:Document {id: $doc_id})
                    MATCH (e:Entity {id: $entity_id})
                    MERGE (d)-[r:MENTIONS]->(e)
                    SET r.context = $context
                    RETURN r
                    """
                    self.graph_client.execute_query(rel_query, {
                        "doc_id": doc_id,
                        "entity_id": entity["id"],
                        "context": entity.get("context", "")[:200]
                    })
                
                log_info(f"  Created document node and {len(entities)} entity relationships")
            
            self.processed_files.add(str(file_path))
            return True
            
        except Exception as e:
            log_error(f"Failed to index {file_path}: {str(e)}")
            self.failed_files.append((str(file_path), str(e)))
            return False
    
    def _extract_entities(self, content: str, title: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extract simple entities from content."""
        entities = []
        
        # Extract dates
        date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b'
        dates = re.findall(date_pattern, content)
        for date in set(dates[:5]):  # Limit to 5 dates
            entities.append({
                "id": f"date_{date.replace('/', '-').replace(' ', '_')}",
                "name": date,
                "type": "Date"
            })
        
        # Extract topics from headings
        heading_pattern = r'^#+\s+(.+)$'
        headings = re.findall(heading_pattern, content, re.MULTILINE)
        for heading in headings[:10]:  # Limit to 10 headings
            heading_clean = heading.strip()
            if len(heading_clean) > 3 and len(heading_clean) < 100:
                entities.append({
                    "id": f"topic_{hashlib.md5(heading_clean.encode()).hexdigest()[:8]}",
                    "name": heading_clean,
                    "type": "Topic"
                })
        
        # Extract action items
        action_patterns = [
            r'(?:TODO|Action|Follow.?up):\s*(.+?)(?:\n|$)',
            r'- \[ \]\s+(.+?)(?:\n|$)'
        ]
        
        for pattern in action_patterns:
            actions = re.findall(pattern, content, re.IGNORECASE)
            for action in actions[:5]:  # Limit to 5 per pattern
                action_clean = action.strip()
                if len(action_clean) > 5:
                    entities.append({
                        "id": f"action_{hashlib.md5(action_clean.encode()).hexdigest()[:8]}",
                        "name": action_clean[:200],
                        "type": "ActionItem",
                        "context": action_clean
                    })
        
        return entities
    
    async def index_directory(self, directory_path: Path, file_extensions: List[str] = None, force_reindex: bool = False) -> Dict[str, Any]:
        """Index all files in a directory."""
        if not directory_path.exists():
            return {"error": f"Directory not found: {directory_path}"}
        
        if not directory_path.is_dir():
            return {"error": f"Not a directory: {directory_path}"}
        
        # Default to markdown files
        if not file_extensions:
            file_extensions = ['.md', '.txt']
        
        log_info(f"Indexing directory: {directory_path}")
        log_info(f"File extensions: {file_extensions}")
        
        # Find all matching files
        files_to_index = []
        for ext in file_extensions:
            files_to_index.extend(directory_path.rglob(f"*{ext}"))
        
        files_to_index = sorted(set(files_to_index))
        log_info(f"Found {len(files_to_index)} files to index")
        
        # Index each file
        success_count = 0
        for file_path in files_to_index:
            if await self.index_file(file_path, force_reindex=force_reindex):
                success_count += 1
        
        # Create directory node in graph
        if self.graph_client:
            dir_id = self._generate_document_id(str(directory_path))
            dir_query = """
            MERGE (d:Directory {id: $id})
            SET d.name = $name, d.path = $path, d.file_count = $file_count, d.indexed_at = $indexed_at
            RETURN d
            """
            self.graph_client.execute_query(dir_query, {
                "id": dir_id,
                "name": directory_path.name,
                "path": str(directory_path),
                "file_count": len(files_to_index),
                "indexed_at": datetime.now().isoformat()
            })
        
        # Summary
        summary = {
            "directory": str(directory_path),
            "total_files": len(files_to_index),
            "indexed": success_count,
            "failed": len(self.failed_files),
            "failures": self.failed_files
        }
        
        return summary


async def main():
    """Main function to run cloud indexing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Index documents to cloud services")
    parser.add_argument("directories", nargs="+", help="Directories to index")
    parser.add_argument("--collection", default="knowledge_base", help="Collection name")
    parser.add_argument("--extensions", nargs="+", default=[".md", ".txt"], help="File extensions")
    parser.add_argument("--force", action="store_true", help="Force reindexing")
    
    args = parser.parse_args()
    
    # Create indexer
    indexer = CloudDocumentIndexer(collection_name=args.collection)
    
    # Index each directory
    for dir_path in args.directories:
        directory = Path(dir_path)
        summary = await indexer.index_directory(
            directory,
            file_extensions=args.extensions,
            force_reindex=args.force
        )
        
        print(f"\nIndexing Summary for {directory}:")
        print(f"  Total files: {summary.get('total_files', 0)}")
        print(f"  Successfully indexed: {summary.get('indexed', 0)}")
        print(f"  Failed: {summary.get('failed', 0)}")
        
        if summary.get('failures'):
            print("\nFailures:")
            for file_path, error in summary['failures']:
                print(f"  - {file_path}: {error}")
    
    # Close connections
    if indexer.graph_client:
        indexer.graph_client.close()


if __name__ == "__main__":
    asyncio.run(main())
