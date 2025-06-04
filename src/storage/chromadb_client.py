"""ChromaDB integration for vector storage."""
import chromadb
from chromadb import Client, Settings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from src.core.config import get_settings
from src.core.exceptions import ChromaDBError
from src.core.constants import (
    DEFAULT_COLLECTION_NAME,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    COLLECTION_WEBSITES,
    COLLECTION_CONVERSATIONS,
    COLLECTION_KNOWLEDGE,
    COLLECTION_CHUNK_CONFIGS
)
from src.utils.logging import log_info, log_error, log_warning
from src.storage.performance_monitor import get_performance_monitor
from src.storage.query_cache import QueryCache


class ChromaDBClient:
    """Client for interacting with ChromaDB."""
    
    def __init__(
        self,
        persist_directory: Optional[Path] = None,
        collection_name: str = DEFAULT_COLLECTION_NAME
    ):
        """Initialize ChromaDB client.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection to use
        """
        self.settings = get_settings()
        self.persist_directory = persist_directory or self.settings.chroma_persist_directory
        self.collection_name = collection_name
        self._collections_cache = {}
        self._query_cache = QueryCache(max_size=200, ttl_seconds=600)
        self._performance_monitor = get_performance_monitor()
        
        # Ensure persist directory exists
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize client
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            log_info(f"ChromaDB client initialized with persist directory: {self.persist_directory}")
        except Exception as e:
            log_error(f"Failed to initialize ChromaDB client: {str(e)}")
            raise ChromaDBError(f"Failed to initialize ChromaDB client: {str(e)}")
        
        # Initialize embedding function
        self.embedding_function = OpenAIEmbeddingFunction(
            api_key=self.settings.openai_api_key or self.settings.llm_api_key,
            model_name=DEFAULT_EMBEDDING_MODEL
        )
        
        # Get or create collection
        self._initialize_collection()
    
    def _initialize_collection(self) -> None:
        """Initialize the collection."""
        try:
            # Get collection description based on type
            description = self._get_collection_description(self.collection_name)
            
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": description}
            )
            log_info(f"Collection '{self.collection_name}' initialized with {self.collection.count()} documents")
        except Exception as e:
            log_error(f"Failed to initialize collection: {str(e)}")
            raise ChromaDBError(f"Failed to initialize collection: {str(e)}")
    
    def _get_collection_description(self, collection_name: str) -> str:
        """Get description for a collection based on its name."""
        descriptions = {
            COLLECTION_WEBSITES: "Indexed website content",
            COLLECTION_CONVERSATIONS: "Conversation history and messages", 
            COLLECTION_KNOWLEDGE: "Knowledge base documents and files",
            DEFAULT_COLLECTION_NAME: "Automation agents knowledge base"
        }
        return descriptions.get(collection_name, "Custom collection")
    
    @get_performance_monitor().track_operation("add_documents")
    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """Add documents to the collection.
        
        Args:
            documents: List of document texts
            metadatas: Optional metadata for each document
            ids: Optional IDs for each document
        """
        try:
            if not documents:
                log_warning("No documents to add")
                return
            
            # Generate IDs if not provided
            if ids is None:
                import uuid
                ids = [str(uuid.uuid4()) for _ in documents]
            
            # Ensure metadatas match document count
            if metadatas is None:
                metadatas = [{} for _ in documents]
            
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            # Invalidate cache for this collection
            self._query_cache.invalidate_collection(self.collection_name)
            
            log_info(f"Added {len(documents)} documents to collection")
        except Exception as e:
            log_error(f"Failed to add documents: {str(e)}")
            raise ChromaDBError(f"Failed to add documents: {str(e)}")
    
    @get_performance_monitor().track_operation("query_collection")
    def query(
        self,
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query the collection.
        
        Args:
            query_texts: List of query strings
            n_results: Number of results to return
            where: Filter on metadata
            where_document: Filter on document content
            
        Returns:
            Query results dictionary
        """
        # Check cache first (skip if where_document is used)
        if where_document is None:
            cached_results = self._query_cache.get(
                self.collection_name,
                query_texts,
                n_results,
                where
            )
            if cached_results is not None:
                return cached_results
        
        try:
            results = self.collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where,
                where_document=where_document
            )
            
            # Cache results if no where_document filter
            if where_document is None:
                self._query_cache.put(
                    self.collection_name,
                    query_texts,
                    n_results,
                    results,
                    where
                )
            
            log_info(f"Query returned {len(results.get('ids', [[]])[0])} results")
            return results
        except Exception as e:
            log_error(f"Failed to query collection: {str(e)}")
            raise ChromaDBError(f"Failed to query collection: {str(e)}")
    
    def update_documents(
        self,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Update existing documents.
        
        Args:
            ids: IDs of documents to update
            documents: New document texts
            metadatas: New metadata
        """
        try:
            self.collection.update(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            log_info(f"Updated {len(ids)} documents")
        except Exception as e:
            log_error(f"Failed to update documents: {str(e)}")
            raise ChromaDBError(f"Failed to update documents: {str(e)}")
    
    def delete_documents(self, ids: List[str]) -> None:
        """Delete documents by ID.
        
        Args:
            ids: IDs of documents to delete
        """
        try:
            self.collection.delete(ids=ids)
            log_info(f"Deleted {len(ids)} documents")
        except Exception as e:
            log_error(f"Failed to delete documents: {str(e)}")
            raise ChromaDBError(f"Failed to delete documents: {str(e)}")
    
    def get_documents(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get documents from the collection.
        
        Args:
            ids: Specific IDs to retrieve
            where: Filter on metadata
            limit: Maximum number of documents to return
            
        Returns:
            Documents dictionary
        """
        try:
            return self.collection.get(
                ids=ids,
                where=where,
                limit=limit
            )
        except Exception as e:
            log_error(f"Failed to get documents: {str(e)}")
            raise ChromaDBError(f"Failed to get documents: {str(e)}")
    
    def clear_collection(self) -> None:
        """Clear all documents from the collection."""
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(name=self.collection_name)
            self._initialize_collection()
            log_info(f"Cleared collection '{self.collection_name}'")
        except Exception as e:
            log_error(f"Failed to clear collection: {str(e)}")
            raise ChromaDBError(f"Failed to clear collection: {str(e)}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            metadata = self.collection.metadata
            
            return {
                "name": self.collection_name,
                "count": count,
                "metadata": metadata,
                "embedding_function": type(self.embedding_function).__name__
            }
        except Exception as e:
            log_error(f"Failed to get collection stats: {str(e)}")
            raise ChromaDBError(f"Failed to get collection stats: {str(e)}")
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ) -> List[str]:
        """Split text into chunks for indexing.
        
        Args:
            text: Text to split
            chunk_size: Size of each chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at a sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > chunk_size // 2:
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(chunk.strip())
            start = end - chunk_overlap
        
        return chunks
    
    def get_collection(self, collection_name: str):
        """Get or create a specific collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection object
        """
        if collection_name not in self._collections_cache:
            try:
                description = self._get_collection_description(collection_name)
                collection = self.client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"description": description}
                )
                self._collections_cache[collection_name] = collection
                log_info(f"Collection '{collection_name}' loaded with {collection.count()} documents")
            except Exception as e:
                log_error(f"Failed to get collection '{collection_name}': {str(e)}")
                raise ChromaDBError(f"Failed to get collection: {str(e)}")
        
        return self._collections_cache[collection_name]
    
    def add_to_collection(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """Add documents to a specific collection.
        
        Args:
            collection_name: Name of the collection
            documents: List of document texts
            metadatas: Optional metadata for each document
            ids: Optional IDs for each document
        """
        collection = self.get_collection(collection_name)
        
        try:
            if not documents:
                log_warning("No documents to add")
                return
            
            # Generate IDs if not provided
            if ids is None:
                import uuid
                ids = [str(uuid.uuid4()) for _ in documents]
            
            # Ensure metadatas match document count
            if metadatas is None:
                metadatas = [{} for _ in documents]
            
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            log_info(f"Added {len(documents)} documents to collection '{collection_name}'")
        except Exception as e:
            log_error(f"Failed to add documents to collection '{collection_name}': {str(e)}")
            raise ChromaDBError(f"Failed to add documents: {str(e)}")
    
    @get_performance_monitor().track_operation("query_specific_collection")
    def query_collection(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query a specific collection.
        
        Args:
            collection_name: Name of the collection to query
            query_texts: List of query strings
            n_results: Number of results to return
            where: Filter on metadata
            where_document: Filter on document content
            
        Returns:
            Query results dictionary
        """
        # Check cache first (skip if where_document is used)
        if where_document is None:
            cached_results = self._query_cache.get(
                collection_name,
                query_texts,
                n_results,
                where
            )
            if cached_results is not None:
                return cached_results
        
        collection = self.get_collection(collection_name)
        
        try:
            results = collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where,
                where_document=where_document
            )
            
            # Cache results if no where_document filter
            if where_document is None:
                self._query_cache.put(
                    collection_name,
                    query_texts,
                    n_results,
                    results,
                    where
                )
            
            log_info(f"Query on '{collection_name}' returned {len(results.get('ids', [[]])[0])} results")
            return results
        except Exception as e:
            log_error(f"Failed to query collection '{collection_name}': {str(e)}")
            raise ChromaDBError(f"Failed to query collection: {str(e)}")
    
    @get_performance_monitor().track_operation("query_multiple_collections")
    def query_multiple_collections(
        self,
        collection_names: List[str],
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Query multiple collections and merge results.
        
        Args:
            collection_names: List of collection names to query
            query_texts: List of query strings
            n_results: Number of results per collection
            where: Filter on metadata
            
        Returns:
            List of results with collection information
        """
        all_results = []
        
        # Query collections in parallel for better performance
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def query_single_collection(collection_name: str):
            try:
                return collection_name, self.query_collection(
                    collection_name,
                    query_texts,
                    n_results,
                    where
                )
            except ChromaDBError as e:
                log_warning(f"Failed to query collection '{collection_name}': {str(e)}")
                return collection_name, None
        
        with ThreadPoolExecutor(max_workers=min(len(collection_names), 3)) as executor:
            futures = [executor.submit(query_single_collection, name) for name in collection_names]
            
            for future in as_completed(futures):
                collection_name, results = future.result()
                if results is None:
                    continue
                
                # Add collection name to results
                for i in range(len(results.get('ids', [[]])[0])):
                    result_item = {
                        'collection': collection_name,
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i],
                        'distance': results['distances'][0][i],
                        'metadata': results['metadatas'][0][i]
                    }
                    all_results.append(result_item)
        
        # Sort by distance (relevance)
        all_results.sort(key=lambda x: x['distance'])
        
        # Limit total results
        return all_results[:n_results]
    
    def get_collection_chunk_config(self, collection_name: str) -> Tuple[int, int]:
        """Get chunk configuration for a specific collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Tuple of (chunk_size, chunk_overlap)
        """
        config = COLLECTION_CHUNK_CONFIGS.get(
            collection_name,
            {"size": DEFAULT_CHUNK_SIZE, "overlap": DEFAULT_CHUNK_OVERLAP}
        )
        return config["size"], config["overlap"]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics.
        
        Returns:
            Dictionary containing performance and cache statistics
        """
        return {
            'performance_metrics': self._performance_monitor.get_metrics(),
            'cache_stats': self._query_cache.get_stats()
        }
    
    def log_performance_report(self):
        """Log a performance report."""
        self._performance_monitor.log_metrics()
        self._query_cache.log_stats()


# Singleton instance
_chromadb_client: Optional[ChromaDBClient] = None


def get_chromadb_client(
    persist_directory: Optional[Path] = None,
    collection_name: str = DEFAULT_COLLECTION_NAME
) -> ChromaDBClient:
    """Get the ChromaDB client singleton."""
    global _chromadb_client
    if _chromadb_client is None:
        _chromadb_client = ChromaDBClient(persist_directory, collection_name)
    return _chromadb_client