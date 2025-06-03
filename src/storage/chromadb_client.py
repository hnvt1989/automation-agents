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
    DEFAULT_CHUNK_OVERLAP
)
from src.utils.logging import log_info, log_error, log_warning


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
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "Automation agents knowledge base"}
            )
            log_info(f"Collection '{self.collection_name}' initialized with {self.collection.count()} documents")
        except Exception as e:
            log_error(f"Failed to initialize collection: {str(e)}")
            raise ChromaDBError(f"Failed to initialize collection: {str(e)}")
    
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
            
            log_info(f"Added {len(documents)} documents to collection")
        except Exception as e:
            log_error(f"Failed to add documents: {str(e)}")
            raise ChromaDBError(f"Failed to add documents: {str(e)}")
    
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
        try:
            results = self.collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where,
                where_document=where_document
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