"""Collection manager for handling multiple ChromaDB collections."""
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import re
from urllib.parse import urlparse
import asyncio

from src.storage.chromadb_client import ChromaDBClient
from src.storage.contextual_chunker import ContextualChunker, ChunkContext
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
    
    def __init__(self, chromadb_client: ChromaDBClient, graph_manager: Optional[Any] = None, enable_contextual: bool = True):
        """Initialize collection manager.
        
        Args:
            chromadb_client: ChromaDB client instance
            graph_manager: Optional GraphKnowledgeManager instance
            enable_contextual: Whether to enable contextual chunking
        """
        self.client = chromadb_client
        self.graph_manager = graph_manager
        self.enable_contextual = enable_contextual
        self._ensure_collections_exist()
        
        # Initialize contextual chunker if enabled
        if self.enable_contextual:
            self.contextual_chunker = ContextualChunker()
            log_info("CollectionManager initialized with contextual chunking")
        else:
            self.contextual_chunker = None
        
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
    
    # Contextual RAG methods
    
    def index_with_context(
        self,
        content: str,
        metadata: Dict[str, Any],
        collection_name: str,
        context_template: Optional[str] = None,
        use_llm_context: bool = False,
        generate_context: bool = True
    ) -> List[str]:
        """Index content with contextual information.
        
        Args:
            content: Content to index
            metadata: Document metadata
            collection_name: Target collection
            context_template: Optional template for context generation
            use_llm_context: Whether to use LLM for context generation
            generate_context: Whether to generate context (vs template)
            
        Returns:
            List of document IDs
        """
        if not self.enable_contextual or not self.contextual_chunker:
            # Fall back to regular indexing
            return self._index_without_context(content, metadata, collection_name)
        
        # Get chunk configuration
        chunk_size, chunk_overlap = self.client.get_collection_chunk_config(collection_name)
        
        # Prepare context info
        context_info = metadata.copy()
        context_info['source_type'] = metadata.get('source_type', 'document')
        
        # Create contextual chunks
        contextual_chunks = self.contextual_chunker.create_contextual_chunks(
            content=content,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            context_info=context_info,
            use_llm_context=use_llm_context and generate_context
        )
        
        # Prepare documents and metadata for indexing
        documents = []
        metadatas = []
        ids = []
        
        import uuid
        for chunk in contextual_chunks:
            # Use contextual text for embedding
            documents.append(chunk.contextual_text)
            
            # Add metadata including original text
            chunk_metadata = chunk.metadata.copy()
            chunk_metadata['original_text'] = chunk.original_text
            chunk_metadata['has_context'] = True
            metadatas.append(chunk_metadata)
            
            ids.append(str(uuid.uuid4()))
        
        # Index to collection
        self.client.add_to_collection(
            collection_name,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        log_info(f"Indexed {len(documents)} contextual chunks to {collection_name}")
        
        # Add to knowledge graph if available
        if self.graph_manager and GRAPH_AVAILABLE:
            self._add_to_graph_if_available(content, metadata, collection_name)
        
        return ids
    
    def contextual_search(
        self,
        query: str,
        collection_name: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search with contextual retrieval.
        
        Args:
            query: Search query
            collection_name: Collection to search
            n_results: Number of results
            where: Metadata filter
            
        Returns:
            List of search results with context
        """
        # Regular search
        results = self.client.query_collection(
            collection_name,
            [query],
            n_results * 2,  # Get more results for re-ranking
            where
        )
        
        # Format results
        formatted_results = []
        if results and 'ids' in results and results['ids']:
            for i, doc_id in enumerate(results['ids'][0]):
                result = {
                    'id': doc_id,
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if 'metadatas' in results else {},
                    'distance': results['distances'][0][i] if 'distances' in results else 0
                }
                
                # Calculate relevance score (inverse of distance)
                result['score'] = 1.0 - result['distance']
                
                # Boost score for contextual results
                if result['metadata'].get('has_context'):
                    result['score'] *= 1.2
                
                formatted_results.append(result)
        
        # Sort by score and return top N
        formatted_results.sort(key=lambda x: x['score'], reverse=True)
        return formatted_results[:n_results]
    
    async def hybrid_contextual_search(
        self,
        query: str,
        collection_name: str,
        n_results: int = 5,
        embedding_weight: float = 0.7,
        bm25_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining embeddings and BM25.
        
        Args:
            query: Search query
            collection_name: Collection to search
            n_results: Number of results
            embedding_weight: Weight for embedding search
            bm25_weight: Weight for BM25 search
            
        Returns:
            Combined and ranked results
        """
        # Embedding search
        embedding_results = self.contextual_search(query, collection_name, n_results * 2)
        
        # BM25 search (if implemented)
        bm25_results = self._bm25_search(query, collection_name, n_results * 2)
        
        # Combine results
        combined_results = {}
        
        # Add embedding results
        for result in embedding_results:
            doc_id = result['id']
            combined_results[doc_id] = {
                'id': doc_id,
                'content': result['content'],
                'metadata': result['metadata'],
                'embedding_score': result['score'] * embedding_weight,
                'bm25_score': 0,
                'total_score': result['score'] * embedding_weight
            }
        
        # Add BM25 results
        for result in bm25_results:
            doc_id = result['id']
            if doc_id in combined_results:
                combined_results[doc_id]['bm25_score'] = result['score'] * bm25_weight
                combined_results[doc_id]['total_score'] += result['score'] * bm25_weight
            else:
                combined_results[doc_id] = {
                    'id': doc_id,
                    'content': result['text'],
                    'metadata': result.get('metadata', {}),
                    'embedding_score': 0,
                    'bm25_score': result['score'] * bm25_weight,
                    'total_score': result['score'] * bm25_weight
                }
        
        # Sort by total score
        sorted_results = sorted(
            combined_results.values(),
            key=lambda x: x['total_score'],
            reverse=True
        )
        
        return sorted_results[:n_results]
    
    def index_conversation_with_context(
        self,
        messages: List[Dict[str, Any]],
        conversation_id: str,
        platform: str,
        topic_summary: Optional[str] = None
    ) -> List[str]:
        """Index conversation with contextual information.
        
        Args:
            messages: Conversation messages
            conversation_id: Conversation ID
            platform: Platform name
            topic_summary: Optional summary of conversation topic
            
        Returns:
            List of document IDs
        """
        # Format conversation
        conversation_text = self._format_conversation(messages)
        
        # Extract participants
        participants = list(set(msg.get('sender', 'Unknown') for msg in messages))
        
        # Create context info
        context_info = {
            'source_type': 'conversation',
            'conversation_id': conversation_id,
            'platform': platform,
            'participants': participants,
            'message_count': len(messages),
            'topic': topic_summary or 'general discussion'
        }
        
        # Index with context
        return self.index_with_context(
            content=conversation_text,
            metadata=context_info,
            collection_name=COLLECTION_CONVERSATIONS,
            use_llm_context=bool(topic_summary)
        )
    
    def index_large_document_with_context(
        self,
        content: str,
        metadata: Dict[str, Any],
        collection_name: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[str]:
        """Index large document with contextual chunking.
        
        Args:
            content: Document content
            metadata: Document metadata
            collection_name: Target collection
            chunk_size: Size of each chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of document IDs
        """
        if not self.enable_contextual or not self.contextual_chunker:
            return self._index_without_context(content, metadata, collection_name)
        
        # Add document summary to context if available
        context_info = metadata.copy()
        context_info['source_type'] = metadata.get('source_type', 'document')
        
        # Create contextual chunks
        contextual_chunks = self.contextual_chunker.create_contextual_chunks(
            content=content,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            context_info=context_info,
            use_llm_context=False  # Use template for large documents
        )
        
        # Index chunks
        documents = []
        metadatas = []
        ids = []
        
        import uuid
        for chunk in contextual_chunks:
            documents.append(chunk.contextual_text)
            metadatas.append(chunk.metadata)
            ids.append(str(uuid.uuid4()))
        
        # Batch index
        self.client.add_to_collection(
            collection_name,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        log_info(f"Indexed {len(documents)} contextual chunks from large document")
        return ids
    
    def batch_index_with_context(
        self,
        documents: List[Dict[str, Any]],
        collection_name: str,
        shared_context: Optional[str] = None
    ) -> List[str]:
        """Batch index multiple documents with context.
        
        Args:
            documents: List of documents with 'content' and 'metadata'
            collection_name: Target collection
            shared_context: Optional shared context for all documents
            
        Returns:
            List of all document IDs
        """
        all_ids = []
        
        for doc in documents:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            if shared_context:
                metadata['shared_context'] = shared_context
            
            ids = self.index_with_context(
                content=content,
                metadata=metadata,
                collection_name=collection_name,
                use_llm_context=False  # Use template for batch
            )
            all_ids.extend(ids)
        
        log_info(f"Batch indexed {len(documents)} documents with {len(all_ids)} total chunks")
        return all_ids
    
    def reindex_with_context(
        self,
        collection_name: str,
        context_template: str = "This document is from {source}: {content}"
    ):
        """Reindex existing documents with contextual information.
        
        Args:
            collection_name: Collection to reindex
            context_template: Template for context generation
        """
        # Get all documents from collection
        collection = self.client.get_collection(collection_name)
        all_docs = collection.get()
        
        if not all_docs or not all_docs.get('ids'):
            log_warning(f"No documents found in {collection_name}")
            return
        
        # Process each document
        updated_count = 0
        for i, doc_id in enumerate(all_docs['ids']):
            content = all_docs['documents'][i]
            metadata = all_docs['metadatas'][i] if 'metadatas' in all_docs else {}
            
            # Skip if already has context
            if metadata.get('has_context'):
                continue
            
            # Generate contextual version
            context_info = metadata.copy()
            contextual_text = context_template.format(
                source=metadata.get('source', 'unknown'),
                content=content,
                **metadata
            )
            
            # Update document
            self.client.update_documents(
                ids=[doc_id],
                documents=[contextual_text],
                metadatas=[{**metadata, 'has_context': True, 'original_text': content}]
            )
            updated_count += 1
        
        log_info(f"Reindexed {updated_count} documents with context in {collection_name}")
    
    def enable_context_cache(self, max_size: int = 1000):
        """Enable caching for context generation.
        
        Args:
            max_size: Maximum cache size
        """
        if self.contextual_chunker:
            # Cache is already built into the chunker
            log_info(f"Context caching enabled")
    
    def get_context_cache_stats(self) -> Dict[str, Any]:
        """Get context cache statistics.
        
        Returns:
            Cache statistics
        """
        if self.contextual_chunker:
            return self.contextual_chunker.get_cache_stats()
        return {'size': 0, 'memory_bytes': 0}
    
    def _index_without_context(
        self,
        content: str,
        metadata: Dict[str, Any],
        collection_name: str
    ) -> List[str]:
        """Index without contextual chunking (fallback).
        
        Args:
            content: Content to index
            metadata: Document metadata
            collection_name: Target collection
            
        Returns:
            List of document IDs
        """
        # Get chunk configuration
        chunk_size, chunk_overlap = self.client.get_collection_chunk_config(collection_name)
        
        # Create regular chunks
        chunks = self.client.chunk_text(content, chunk_size, chunk_overlap)
        
        # Prepare for indexing
        import uuid
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [metadata.copy() for _ in chunks]
        
        # Add chunk info to metadata
        for i, meta in enumerate(metadatas):
            meta['chunk_index'] = i
            meta['total_chunks'] = len(chunks)
            meta['has_context'] = False
        
        # Index
        self.client.add_to_collection(
            collection_name,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        
        return ids
    
    def _bm25_search(
        self,
        query: str,
        collection_name: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """BM25 search implementation (placeholder).
        
        Args:
            query: Search query
            collection_name: Collection to search
            n_results: Number of results
            
        Returns:
            BM25 search results
        """
        # TODO: Implement actual BM25 search
        # For now, return empty list
        return []
    
    def _add_to_graph_if_available(
        self,
        content: str,
        metadata: Dict[str, Any],
        collection_name: str
    ):
        """Add to knowledge graph if available.
        
        Args:
            content: Content to add
            metadata: Document metadata
            collection_name: Source collection
        """
        if self.graph_manager and GRAPH_AVAILABLE:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._add_to_graph_async(
                        content=content,
                        metadata=metadata,
                        name=metadata.get('title', metadata.get('source', 'Document'))
                    ))
                else:
                    loop.run_until_complete(self._add_to_graph_async(
                        content=content,
                        metadata=metadata,
                        name=metadata.get('title', metadata.get('source', 'Document'))
                    ))
            except Exception as e:
                log_warning(f"Failed to add to knowledge graph: {str(e)}")