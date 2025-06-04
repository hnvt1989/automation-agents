"""Collection manager for handling multiple ChromaDB collections."""
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import re
from urllib.parse import urlparse

from src.storage.chromadb_client import ChromaDBClient
from src.core.constants import (
    COLLECTION_WEBSITES,
    COLLECTION_CONVERSATIONS,
    COLLECTION_KNOWLEDGE
)
from src.utils.logging import log_info, log_error, log_warning

# Optional graph integration
try:
    from src.storage.graph_knowledge_manager import GraphKnowledgeManager
    GRAPH_AVAILABLE = True
except ImportError:
    GraphKnowledgeManager = None
    GRAPH_AVAILABLE = False


class CollectionManager:
    """Manages multiple ChromaDB collections with type-specific logic."""
    
    def __init__(self, chromadb_client: ChromaDBClient, graph_manager: Optional[Any] = None):
        """Initialize collection manager.
        
        Args:
            chromadb_client: ChromaDB client instance
            graph_manager: Optional GraphKnowledgeManager instance
        """
        self.client = chromadb_client
        self.graph_manager = graph_manager
        self._ensure_collections_exist()
        
        if self.graph_manager:
            log_info("CollectionManager initialized with knowledge graph support")
        else:
            log_info("CollectionManager initialized without knowledge graph")
    
    def _ensure_collections_exist(self):
        """Ensure all required collections exist."""
        collections = [
            COLLECTION_WEBSITES,
            COLLECTION_CONVERSATIONS,
            COLLECTION_KNOWLEDGE
        ]
        
        for collection_name in collections:
            try:
                self.client.get_collection(collection_name)
                log_info(f"Collection '{collection_name}' is ready")
            except Exception as e:
                log_error(f"Failed to ensure collection '{collection_name}': {str(e)}")
    
    def index_website(
        self,
        url: str,
        content: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Index website content with appropriate chunking.
        
        Args:
            url: Website URL
            content: Website content
            title: Page title
            metadata: Additional metadata
            
        Returns:
            List of document IDs
        """
        # Parse domain from URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Get chunk configuration for websites
        chunk_size, chunk_overlap = self.client.get_collection_chunk_config(COLLECTION_WEBSITES)
        
        # Chunk the content
        chunks = self.client.chunk_text(content, chunk_size, chunk_overlap)
        
        # Prepare metadata for each chunk
        base_metadata = {
            "source_type": "website",
            "url": url,
            "domain": domain,
            "title": title or "Untitled"
        }
        
        if metadata:
            base_metadata.update(metadata)
        
        # Create metadata for each chunk
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = len(chunks)
            metadatas.append(chunk_metadata)
        
        # Index chunks
        import uuid
        ids = [str(uuid.uuid4()) for _ in chunks]
        
        self.client.add_to_collection(
            COLLECTION_WEBSITES,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        
        log_info(f"Indexed {len(chunks)} chunks from {url}")
        
        # Add to knowledge graph if available
        if self.graph_manager and GRAPH_AVAILABLE:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule as task if loop is already running
                    asyncio.create_task(self._add_to_graph_async(
                        content=content,
                        metadata=base_metadata,
                        name=f"Website: {title or url}"
                    ))
                else:
                    # Run directly if no loop
                    loop.run_until_complete(self._add_to_graph_async(
                        content=content,
                        metadata=base_metadata,
                        name=f"Website: {title or url}"
                    ))
            except Exception as e:
                log_warning(f"Failed to add website to knowledge graph: {str(e)}")
        
        return ids
    
    def index_conversation(
        self,
        messages: List[Dict[str, Any]],
        conversation_id: Optional[str] = None,
        platform: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Index conversation messages with context preservation.
        
        Args:
            messages: List of message dictionaries
            conversation_id: Unique conversation identifier
            platform: Conversation platform
            metadata: Additional metadata
            
        Returns:
            List of document IDs
        """
        if not messages:
            log_warning("No messages to index")
            return []
        
        # Get chunk configuration for conversations
        chunk_size, chunk_overlap = self.client.get_collection_chunk_config(COLLECTION_CONVERSATIONS)
        
        # Format messages into conversation text
        conversation_text = self._format_conversation(messages)
        
        # Chunk the conversation
        chunks = self.client.chunk_text(conversation_text, chunk_size, chunk_overlap)
        
        # Extract participants
        participants = list(set(msg.get("sender", "Unknown") for msg in messages))
        
        # Prepare metadata
        base_metadata = {
            "source_type": "conversation",
            "conversation_id": conversation_id or self._generate_conversation_id(),
            "participants": participants,
            "platform": platform or "unknown",
            "message_count": len(messages)
        }
        
        if metadata:
            base_metadata.update(metadata)
        
        # Create metadata for each chunk
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = len(chunks)
            metadatas.append(chunk_metadata)
        
        # Index chunks
        import uuid
        ids = [str(uuid.uuid4()) for _ in chunks]
        
        self.client.add_to_collection(
            COLLECTION_CONVERSATIONS,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        
        log_info(f"Indexed {len(chunks)} chunks from conversation with {len(messages)} messages")
        
        # Add to knowledge graph if available
        if self.graph_manager and GRAPH_AVAILABLE:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._add_conversation_to_graph_async(
                        messages=messages,
                        conversation_id=conversation_id or self._generate_conversation_id(),
                        platform=platform or "unknown",
                        metadata=base_metadata
                    ))
                else:
                    loop.run_until_complete(self._add_conversation_to_graph_async(
                        messages=messages,
                        conversation_id=conversation_id or self._generate_conversation_id(),
                        platform=platform or "unknown",
                        metadata=base_metadata
                    ))
            except Exception as e:
                log_warning(f"Failed to add conversation to knowledge graph: {str(e)}")
        
        return ids
    
    def index_knowledge(
        self,
        file_path: Union[str, Path],
        content: str,
        category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Index knowledge documents.
        
        Args:
            file_path: Path to the file
            content: File content
            category: Document category
            metadata: Additional metadata
            
        Returns:
            List of document IDs
        """
        file_path = Path(file_path)
        
        # Get chunk configuration for knowledge
        chunk_size, chunk_overlap = self.client.get_collection_chunk_config(COLLECTION_KNOWLEDGE)
        
        # Chunk the content
        chunks = self.client.chunk_text(content, chunk_size, chunk_overlap)
        
        # Prepare metadata
        base_metadata = {
            "source_type": "knowledge",
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix,
            "category": category or self._infer_category(file_path)
        }
        
        if metadata:
            base_metadata.update(metadata)
        
        # Create metadata for each chunk
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = len(chunks)
            metadatas.append(chunk_metadata)
        
        # Index chunks
        import uuid
        ids = [str(uuid.uuid4()) for _ in chunks]
        
        self.client.add_to_collection(
            COLLECTION_KNOWLEDGE,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        
        log_info(f"Indexed {len(chunks)} chunks from {file_path}")
        
        # Add to knowledge graph if available
        if self.graph_manager and GRAPH_AVAILABLE:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._add_to_graph_async(
                        content=content,
                        metadata=base_metadata,
                        name=f"Document: {file_path.name}"
                    ))
                else:
                    loop.run_until_complete(self._add_to_graph_async(
                        content=content,
                        metadata=base_metadata,
                        name=f"Document: {file_path.name}"
                    ))
            except Exception as e:
                log_warning(f"Failed to add document to knowledge graph: {str(e)}")
        
        return ids
    
    def search_all(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search across all collections.
        
        Args:
            query: Search query
            n_results: Total number of results to return
            where: Metadata filter
            
        Returns:
            List of search results from all collections
        """
        collections = [
            COLLECTION_WEBSITES,
            COLLECTION_CONVERSATIONS,
            COLLECTION_KNOWLEDGE
        ]
        
        return self.client.query_multiple_collections(
            collections,
            [query],
            n_results,
            where
        )
    
    def search_by_type(
        self,
        query: str,
        source_types: List[str],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search specific collection types.
        
        Args:
            query: Search query
            source_types: List of source types to search
            n_results: Number of results to return
            where: Metadata filter
            
        Returns:
            List of search results from specified collections
        """
        # Map source types to collection names
        type_to_collection = {
            "website": COLLECTION_WEBSITES,
            "conversation": COLLECTION_CONVERSATIONS,
            "knowledge": COLLECTION_KNOWLEDGE
        }
        
        collections = []
        for source_type in source_types:
            if source_type in type_to_collection:
                collections.append(type_to_collection[source_type])
        
        if not collections:
            log_warning(f"No valid collections found for source types: {source_types}")
            return []
        
        return self.client.query_multiple_collections(
            collections,
            [query],
            n_results,
            where
        )
    
    def get_collection_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all collections.
        
        Returns:
            Dictionary of collection statistics
        """
        stats = {}
        collections = [
            COLLECTION_WEBSITES,
            COLLECTION_CONVERSATIONS,
            COLLECTION_KNOWLEDGE
        ]
        
        for collection_name in collections:
            try:
                collection = self.client.get_collection(collection_name)
                stats[collection_name] = {
                    "count": collection.count(),
                    "metadata": collection.metadata
                }
            except Exception as e:
                log_error(f"Failed to get stats for '{collection_name}': {str(e)}")
                stats[collection_name] = {"error": str(e)}
        
        return stats
    
    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages into conversation text.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Formatted conversation text
        """
        lines = []
        for msg in messages:
            sender = msg.get("sender", "Unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            
            if timestamp:
                lines.append(f"[{timestamp}] {sender}: {content}")
            else:
                lines.append(f"{sender}: {content}")
        
        return "\n".join(lines)
    
    def _generate_conversation_id(self) -> str:
        """Generate a unique conversation ID.
        
        Returns:
            Conversation ID
        """
        import uuid
        return f"conv_{uuid.uuid4().hex[:8]}"
    
    def _infer_category(self, file_path: Path) -> str:
        """Infer category from file path.
        
        Args:
            file_path: Path to file
            
        Returns:
            Inferred category
        """
        # Check file extension
        if file_path.suffix in [".py", ".js", ".java", ".cpp", ".c"]:
            return "code"
        elif file_path.suffix in [".md", ".txt", ".rst"]:
            return "documentation"
        elif file_path.suffix in [".json", ".yaml", ".yml", ".toml"]:
            return "configuration"
        elif file_path.suffix in [".csv", ".xlsx", ".xls"]:
            return "data"
        
        # Check path components
        path_str = str(file_path).lower()
        if "doc" in path_str:
            return "documentation"
        elif "test" in path_str:
            return "testing"
        elif "config" in path_str:
            return "configuration"
        
        return "general"
    
    def batch_index_websites(
        self,
        websites: List[Dict[str, Any]],
        batch_size: int = 50
    ) -> Dict[str, int]:
        """Batch index multiple websites.
        
        Args:
            websites: List of website dictionaries with 'url', 'content', 'title', 'metadata'
            batch_size: Number of documents to process in each batch
            
        Returns:
            Dictionary with indexing statistics
        """
        stats = {'total': 0, 'success': 0, 'errors': 0}
        
        # Get chunk configuration
        chunk_size, chunk_overlap = self.client.get_collection_chunk_config(COLLECTION_WEBSITES)
        
        # Process in batches
        all_documents = []
        all_metadatas = []
        all_ids = []
        
        for website in websites:
            try:
                content = website.get('content', '')
                url = website.get('url', '')
                
                if not content or not url:
                    stats['errors'] += 1
                    continue
                
                # Chunk content
                chunks = self.client.chunk_text(content, chunk_size, chunk_overlap)
                
                # Prepare metadata
                parsed_url = urlparse(url)
                base_metadata = {
                    "source_type": "website",
                    "url": url,
                    "domain": parsed_url.netloc,
                    "title": website.get('title', 'Untitled')
                }
                
                if 'metadata' in website:
                    base_metadata.update(website['metadata'])
                
                # Add chunks
                import uuid
                for i, chunk in enumerate(chunks):
                    chunk_metadata = base_metadata.copy()
                    chunk_metadata["chunk_index"] = i
                    chunk_metadata["total_chunks"] = len(chunks)
                    
                    all_documents.append(chunk)
                    all_metadatas.append(chunk_metadata)
                    all_ids.append(str(uuid.uuid4()))
                
                stats['success'] += 1
                
                # Process batch if reached batch size
                if len(all_documents) >= batch_size:
                    self.client.add_to_collection(
                        COLLECTION_WEBSITES,
                        documents=all_documents[:batch_size],
                        metadatas=all_metadatas[:batch_size],
                        ids=all_ids[:batch_size]
                    )
                    
                    # Keep remaining
                    all_documents = all_documents[batch_size:]
                    all_metadatas = all_metadatas[batch_size:]
                    all_ids = all_ids[batch_size:]
                    
            except Exception as e:
                log_error(f"Error indexing website {website.get('url', 'unknown')}: {str(e)}")
                stats['errors'] += 1
        
        # Process remaining documents
        if all_documents:
            self.client.add_to_collection(
                COLLECTION_WEBSITES,
                documents=all_documents,
                metadatas=all_metadatas,
                ids=all_ids
            )
        
        stats['total'] = len(websites)
        log_info(f"Batch indexed websites: {stats['success']} success, {stats['errors']} errors")
        return stats
    
    async def _add_to_graph_async(self, content: str, metadata: Dict[str, Any], name: str):
        """Async helper to add content to knowledge graph."""
        if self.graph_manager:
            try:
                await self.graph_manager.add_document_episode(
                    content=content,
                    metadata=metadata,
                    name=name
                )
            except Exception as e:
                log_error(f"Failed to add to graph: {str(e)}")
    
    async def _add_conversation_to_graph_async(
        self,
        messages: List[Dict[str, Any]],
        conversation_id: str,
        platform: str,
        metadata: Dict[str, Any]
    ):
        """Async helper to add conversation to knowledge graph."""
        if self.graph_manager:
            try:
                await self.graph_manager.add_conversation_episode(
                    messages=messages,
                    conversation_id=conversation_id,
                    platform=platform,
                    metadata=metadata
                )
            except Exception as e:
                log_error(f"Failed to add conversation to graph: {str(e)}")