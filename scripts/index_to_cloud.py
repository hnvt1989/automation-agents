#!/usr/bin/env python3
"""Script to index documents from specified directories to cloud services (Supabase and Neo4j Aura)."""

import os
import sys
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse
from datetime import datetime
import hashlib
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.storage.supabase_vector import SupabaseVectorClient
from src.storage.neo4j_cloud import Neo4jCloudClient, get_neo4j_cloud_client
from src.storage.contextual_chunker import ContextualChunker
from src.utils.logging import setup_logger, log_info, log_error, log_warning
from src.core.config import get_settings
from src.core.constants import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP


class CloudIndexer:
    """Indexes documents to cloud services."""
    
    def __init__(self, collection_name: str = "documents"):
        """Initialize the cloud indexer.
        
        Args:
            collection_name: Name of the collection for vector storage
        """
        self.collection_name = collection_name
        self.settings = get_settings()
        
        # Initialize vector client (Supabase)
        log_info("Initializing Supabase vector client...")
        self.vector_client = SupabaseVectorClient(collection_name)
        
        # Initialize graph client (Neo4j Aura)
        log_info("Initializing Neo4j Aura client...")
        self.graph_client = get_neo4j_cloud_client()
        
        # Initialize contextual chunker
        self.chunker = ContextualChunker()
        
        # Track processed files
        self.processed_files = set()
        self.failed_files = []
        
    def _generate_document_id(self, file_path: str) -> str:
        """Generate a unique ID for a document based on its path."""
        return hashlib.md5(file_path.encode()).hexdigest()
    
    def _extract_metadata_from_path(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from file path and name.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with metadata
        """
        metadata = {
            "source": str(file_path),
            "filename": file_path.name,
            "directory": str(file_path.parent),
            "file_type": file_path.suffix.lower(),
            "indexed_at": datetime.now().isoformat()
        }
        
        # Extract date from filename if present (common patterns)
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{2}-\d{2}-\d{4})',  # MM-DD-YYYY
            r'(\d{8})',              # YYYYMMDD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, file_path.name)
            if match:
                metadata["document_date"] = match.group(1)
                break
        
        # Determine document type from directory
        if "meeting_notes" in str(file_path):
            metadata["document_type"] = "meeting"
        elif "va_notes" in str(file_path):
            metadata["document_type"] = "va_note"
        else:
            metadata["document_type"] = "document"
        
        return metadata
    
    def _document_exists(self, doc_id: str) -> bool:
        """Check if a document already exists in the vector store.
        
        Args:
            doc_id: Document ID to check
            
        Returns:
            True if document exists
        """
        try:
            from src.storage.supabase_client import get_supabase_client
            client = get_supabase_client()
            result = client.client.table("document_embeddings") \
                .select("document_id") \
                .eq("collection_name", self.collection_name) \
                .eq("document_id", f"{doc_id}_chunk_0") \
                .execute()
            
            return len(result.data) > 0 if result.data else False
        except Exception:
            return False
    
    async def index_file(self, file_path: Path, force_reindex: bool = False) -> bool:
        """Index a single file to cloud services.
        
        Args:
            file_path: Path to the file to index
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate document ID
            doc_id = self._generate_document_id(str(file_path))
            
            # Check if document already exists
            if not force_reindex and self._document_exists(doc_id):
                log_info(f"Skipping file (already indexed): {file_path}")
                self.processed_files.add(str(file_path))
                return True
            
            log_info(f"Indexing file: {file_path}")
            
            # Read file content
            content = file_path.read_text(encoding='utf-8')
            if not content.strip():
                log_warning(f"Skipping empty file: {file_path}")
                return False
            
            # Extract metadata
            metadata = self._extract_metadata_from_path(file_path)
            
            # Extract title from content (first line or heading)
            lines = content.split('\n')
            title = None
            for line in lines[:5]:  # Check first 5 lines
                line = line.strip()
                if line.startswith('#'):
                    title = line.lstrip('#').strip()
                    break
                elif line and not title:
                    title = line[:100]  # Use first non-empty line
            
            if title:
                metadata["title"] = title
            
            # 1. Add to vector storage (Supabase)
            log_info(f"  Adding to vector storage...")
            
            # Use contextual chunking for better results
            chunks_with_context = self.chunker.create_contextual_chunks(
                content,
                chunk_size=DEFAULT_CHUNK_SIZE,
                chunk_overlap=DEFAULT_CHUNK_OVERLAP,
                context_info={
                    'source_type': 'knowledge_base',
                    'filename': file_path.name,
                    'category': metadata['document_type'],
                    'document_type': metadata['file_type'],
                    'title': title or file_path.stem
                },
                use_llm_context=False  # Use template context for speed
            )
            
            # Prepare chunks for indexing
            chunk_texts = []
            chunk_metadatas = []
            chunk_ids = []
            
            for i, chunk_context in enumerate(chunks_with_context):
                # Use the contextual text which includes both context and chunk
                chunk_text = chunk_context.contextual_text
                
                # Merge metadata
                chunk_metadata = metadata.copy()
                chunk_metadata.update(chunk_context.metadata)
                
                chunk_texts.append(chunk_text)
                chunk_metadatas.append(chunk_metadata)
                chunk_ids.append(f"{doc_id}_chunk_{i}")
            
            # Add to vector store
            self.vector_client.add_documents(
                documents=chunk_texts,
                metadatas=chunk_metadatas,
                ids=chunk_ids
            )
            
            log_info(f"  Added {len(chunks_with_context)} chunks to vector storage")
            
            # 2. Add to knowledge graph (Neo4j Aura)
            log_info(f"  Adding to knowledge graph...")
            
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
            
            # Create document node
            self.graph_client.create_entity("Document", doc_properties)
            
            # Extract and create entities from content
            entities = self._extract_entities(content, title)
            
            for entity in entities:
                # Create or merge entity node
                entity_props = {
                    "id": entity["id"],
                    "name": entity["name"],
                    "type": entity["type"]
                }
                
                # Create entity if not exists
                query = """
                MERGE (e:Entity {id: $id})
                ON CREATE SET e += $props
                RETURN e
                """
                self.graph_client.execute_query(query, {"id": entity["id"], "props": entity_props})
                
                # Create relationship to document
                self.graph_client.create_relationship(
                    from_id=doc_id,
                    to_id=entity["id"],
                    relationship_type="MENTIONS",
                    properties={"context": entity.get("context", "")}
                )
            
            log_info(f"  Created document node and {len(entities)} entity relationships")
            
            self.processed_files.add(str(file_path))
            return True
            
        except Exception as e:
            log_error(f"Failed to index {file_path}: {str(e)}")
            self.failed_files.append((str(file_path), str(e)))
            return False
    
    def _extract_entities(self, content: str, title: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extract entities from document content.
        
        Args:
            content: Document content
            title: Document title
            
        Returns:
            List of entity dictionaries
        """
        entities = []
        
        # Extract dates
        date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b'
        dates = re.findall(date_pattern, content)
        for date in set(dates):
            entities.append({
                "id": f"date_{date.replace('/', '-').replace(' ', '_')}",
                "name": date,
                "type": "Date"
            })
        
        # Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        for email in set(emails):
            entities.append({
                "id": f"email_{email.replace('@', '_at_').replace('.', '_')}",
                "name": email,
                "type": "Email"
            })
        
        # Extract potential meeting topics from headings
        heading_pattern = r'^#+\s+(.+)$'
        headings = re.findall(heading_pattern, content, re.MULTILINE)
        for heading in headings[:5]:  # Limit to first 5 headings
            heading_clean = heading.strip()
            if len(heading_clean) > 3 and len(heading_clean) < 100:
                entities.append({
                    "id": f"topic_{hashlib.md5(heading_clean.encode()).hexdigest()[:8]}",
                    "name": heading_clean,
                    "type": "Topic"
                })
        
        # Extract action items (common patterns)
        action_patterns = [
            r'(?:TODO|Action|Follow.?up):\s*(.+?)(?:\n|$)',
            r'- \[ \]\s+(.+?)(?:\n|$)',  # Markdown checkboxes
            r'(?:Next steps?|Action items?):\s*(.+?)(?:\n|$)'
        ]
        
        for pattern in action_patterns:
            actions = re.findall(pattern, content, re.IGNORECASE)
            for action in actions[:10]:  # Limit to 10 per pattern
                action_clean = action.strip()
                if len(action_clean) > 5:
                    entities.append({
                        "id": f"action_{hashlib.md5(action_clean.encode()).hexdigest()[:8]}",
                        "name": action_clean[:200],  # Limit length
                        "type": "ActionItem",
                        "context": action_clean
                    })
        
        return entities
    
    async def index_directory(self, directory_path: Path, file_extensions: List[str] = None, force_reindex: bool = False) -> Dict[str, Any]:
        """Index all files in a directory.
        
        Args:
            directory_path: Path to the directory
            file_extensions: List of file extensions to include (e.g., ['.md', '.txt'])
            
        Returns:
            Summary of indexing results
        """
        if not directory_path.exists():
            log_error(f"Directory not found: {directory_path}")
            return {"error": f"Directory not found: {directory_path}"}
        
        if not directory_path.is_dir():
            log_error(f"Not a directory: {directory_path}")
            return {"error": f"Not a directory: {directory_path}"}
        
        # Default to markdown files if no extensions specified
        if not file_extensions:
            file_extensions = ['.md', '.txt']
        
        log_info(f"Indexing directory: {directory_path}")
        log_info(f"File extensions: {file_extensions}")
        
        # Find all matching files
        files_to_index = []
        for ext in file_extensions:
            files_to_index.extend(directory_path.rglob(f"*{ext}"))
        
        # Remove duplicates and sort
        files_to_index = sorted(set(files_to_index))
        
        log_info(f"Found {len(files_to_index)} files to index")
        
        # Index each file
        success_count = 0
        for file_path in files_to_index:
            if await self.index_file(file_path, force_reindex=force_reindex):
                success_count += 1
        
        # Create directory node in graph
        dir_id = self._generate_document_id(str(directory_path))
        dir_properties = {
            "id": dir_id,
            "name": directory_path.name,
            "path": str(directory_path),
            "type": "Directory",
            "file_count": len(files_to_index),
            "indexed_at": datetime.now().isoformat()
        }
        
        self.graph_client.create_entity("Directory", dir_properties)
        
        # Link documents to directory
        for file_path in self.processed_files:
            if str(directory_path) in file_path:
                doc_id = self._generate_document_id(file_path)
                try:
                    self.graph_client.create_relationship(
                        from_id=dir_id,
                        to_id=doc_id,
                        relationship_type="CONTAINS"
                    )
                except Exception as e:
                    log_warning(f"Failed to create directory relationship: {e}")
        
        # Summary
        summary = {
            "directory": str(directory_path),
            "total_files": len(files_to_index),
            "indexed": success_count,
            "failed": len(self.failed_files),
            "collection": self.collection_name
        }
        
        if self.failed_files:
            summary["failures"] = self.failed_files
        
        return summary
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about indexed data."""
        stats = {}
        
        # Vector storage stats
        try:
            vector_stats = self.vector_client.get_collection_stats()
            stats["vector_storage"] = vector_stats
        except Exception as e:
            stats["vector_storage"] = {"error": str(e)}
        
        # Graph stats
        try:
            graph_stats = self.graph_client.get_graph_summary()
            stats["knowledge_graph"] = graph_stats
        except Exception as e:
            stats["knowledge_graph"] = {"error": str(e)}
        
        return stats


async def main():
    """Main function to run the indexing script."""
    parser = argparse.ArgumentParser(
        description="Index documents to cloud services (Supabase and Neo4j Aura)"
    )
    parser.add_argument(
        "--directories",
        nargs="+",
        default=["data/meeting_notes", "data/va_notes"],
        help="Directories to index"
    )
    parser.add_argument(
        "--collection",
        default="documents",
        help="Collection name for vector storage"
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".md", ".txt"],
        help="File extensions to index"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before indexing"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Check what's already indexed without indexing"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-index existing documents"
    )
    parser.add_argument(
        "--env-file",
        default="local.env",
        help="Environment file path"
    )
    
    args = parser.parse_args()
    
    # Load environment
    load_dotenv(args.env_file)
    
    # Setup logging
    setup_logger("cloud_indexer")
    
    # Verify cloud services are configured
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        log_error("Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY")
        sys.exit(1)
    
    if not os.getenv("NEO4J_URI") or not os.getenv("NEO4J_PASSWORD"):
        log_error("Neo4j Aura credentials not found. Please set NEO4J_URI and NEO4J_PASSWORD")
        sys.exit(1)
    
    # Initialize indexer
    indexer = CloudIndexer(collection_name=args.collection)
    
    # Check-only mode
    if args.check_only:
        log_info("\nChecking existing indexed documents...")
        stats = indexer.get_stats()
        log_info(f"Vector storage: {stats.get('vector_storage', {})}")
        log_info(f"Knowledge graph: {stats.get('knowledge_graph', {})}")
        
        # List some sample documents
        try:
            from src.storage.supabase_client import get_supabase_client
            client = get_supabase_client()
            result = client.client.table("document_embeddings") \
                .select("collection_name, document_id, content") \
                .eq("collection_name", args.collection) \
                .limit(10) \
                .execute()
            
            if result.data:
                log_info(f"\nSample documents in collection '{args.collection}':")
                for doc in result.data:
                    log_info(f"  - {doc['document_id']}: {doc['content'][:100]}...")
            else:
                log_info(f"No documents found in collection '{args.collection}'")
        except Exception as e:
            log_error(f"Failed to list documents: {e}")
        
        sys.exit(0)
    
    # Clear existing data if requested
    if args.clear:
        log_info("Clearing existing data...")
        try:
            indexer.vector_client.clear_collection()
            indexer.graph_client.clear_graph()
            log_info("Existing data cleared")
        except Exception as e:
            log_error(f"Failed to clear data: {e}")
    
    # Get initial stats
    log_info("\nInitial statistics:")
    initial_stats = indexer.get_stats()
    log_info(f"Vector storage: {initial_stats.get('vector_storage', {})}")
    log_info(f"Knowledge graph: {initial_stats.get('knowledge_graph', {})}")
    
    # Index each directory
    results = []
    for directory in args.directories:
        dir_path = Path(directory)
        if not dir_path.is_absolute():
            dir_path = project_root / dir_path
        
        log_info(f"\nIndexing directory: {dir_path}")
        result = await indexer.index_directory(dir_path, args.extensions, force_reindex=args.force)
        results.append(result)
        
        # Print summary for this directory
        log_info(f"\nSummary for {directory}:")
        log_info(f"  Total files: {result.get('total_files', 0)}")
        log_info(f"  Successfully indexed: {result.get('indexed', 0)}")
        log_info(f"  Failed: {result.get('failed', 0)}")
        
        if result.get('failures'):
            log_error("  Failed files:")
            for file_path, error in result['failures']:
                log_error(f"    - {file_path}: {error}")
    
    # Final stats
    log_info("\nFinal statistics:")
    final_stats = indexer.get_stats()
    log_info(f"Vector storage: {final_stats.get('vector_storage', {})}")
    log_info(f"Knowledge graph: {final_stats.get('knowledge_graph', {})}")
    
    # Overall summary
    log_info("\n" + "="*50)
    log_info("INDEXING COMPLETE")
    log_info("="*50)
    
    total_files = sum(r.get('total_files', 0) for r in results)
    total_indexed = sum(r.get('indexed', 0) for r in results)
    total_failed = sum(r.get('failed', 0) for r in results)
    
    log_info(f"Total files processed: {total_files}")
    log_info(f"Successfully indexed: {total_indexed}")
    log_info(f"Failed: {total_failed}")
    log_info(f"Success rate: {(total_indexed/total_files*100):.1f}%" if total_files > 0 else "N/A")


if __name__ == "__main__":
    asyncio.run(main())