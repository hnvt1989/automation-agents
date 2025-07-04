"""Document Manager for Supabase vector storage.

This module provides a unified interface for managing documents, notes, memos,
and interviews using Supabase vector storage with proper categorization and metadata.
"""

import os
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from src.storage.supabase_vector import SupabaseVectorClient
from src.storage.document_storage import DocumentStorage
from src.utils.logging import log_info, log_error, log_warning


class DocumentManager:
    """Manages documents in Supabase vector storage with categorization."""
    
    DOCUMENT_TYPES = {
        'document': 'documents',
        'note': 'notes', 
        'memo': 'memos',
        'interview': 'interviews'
    }
    
    def __init__(self, user_id: Optional[str] = None):
        """Initialize document manager.
        
        Args:
            user_id: User ID for user-scoped document access
        """
        self.user_id = user_id
        
        # Initialize document storage for full documents
        self.document_storage = DocumentStorage(user_id=user_id)
        
        # Create separate collections for each document type (for embeddings)
        self.clients = {
            doc_type: SupabaseVectorClient(
                collection_name=collection_name,
                enable_contextual=True,
                user_id=user_id
            )
            for doc_type, collection_name in self.DOCUMENT_TYPES.items()
        }
        
        log_info(f"DocumentManager initialized for user: {user_id}")
    
    def add_document(
        self,
        content: str,
        name: str,
        doc_type: str,
        description: Optional[str] = None,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a document to both full document storage and vector storage.
        
        Args:
            content: Document content
            name: Document name/title
            doc_type: Type of document (document, note, memo, interview)
            description: Optional description
            filename: Original filename
            metadata: Additional metadata
            
        Returns:
            Document ID
        """
        if doc_type not in self.DOCUMENT_TYPES:
            raise ValueError(f"Invalid document type: {doc_type}")
        
        # Generate unique document ID
        doc_id = str(uuid.uuid4())
        
        # Prepare metadata
        doc_metadata = {
            'name': name,
            'description': description or f"{doc_type.title()} - {name}",
            'filename': filename or f"{name.lower().replace(' ', '_')}.md",
            'doc_type': doc_type,
            'created_at': datetime.now().isoformat(),
            'last_modified': datetime.now().isoformat(),
            **(metadata or {})
        }
        
        # 1. Try to store full document in dedicated table
        storage_result = self.document_storage.create_document(
            document_id=doc_id,
            name=name,
            content=content,
            doc_type=doc_type,
            description=description,
            metadata=doc_metadata
        )
        
        if not storage_result["success"]:
            log_warning(f"Failed to store full document in dedicated table: {storage_result['error']}")
            # Continue with embedding storage as fallback
        
        # 2. Create embeddings for search
        client = self.clients[doc_type]
        
        # Add document with contextual chunking for vector search
        doc_ids = client.add_documents_with_context(
            content=content,
            context_info=doc_metadata,
            use_llm_context=True
        )
        
        log_info(f"Added {doc_type}: {name} with ID: {doc_id} and {len(doc_ids)} chunks")
        return doc_id
    
    def get_documents(self, doc_type: str) -> List[Dict[str, Any]]:
        """Get all documents of a specific type.
        
        Args:
            doc_type: Type of document to retrieve
            
        Returns:
            List of document metadata
        """
        if doc_type not in self.DOCUMENT_TYPES:
            raise ValueError(f"Invalid document type: {doc_type}")
        
        # Get documents from the dedicated storage
        documents = self.document_storage.get_documents(doc_type)
        
        log_info(f"Retrieved {len(documents)} {doc_type}s")
        return documents
    
    def get_document_content(self, doc_id: str, doc_type: str) -> Optional[str]:
        """Get full document content by ID.
        
        Args:
            doc_id: Document ID
            doc_type: Type of document
            
        Returns:
            Document content or None if not found
        """
        if doc_type not in self.DOCUMENT_TYPES:
            raise ValueError(f"Invalid document type: {doc_type}")
        
        # Try to get full document from dedicated storage first
        if self.document_storage.tables_available:
            document = self.document_storage.get_document(doc_id, doc_type)
            if document:
                return document["content"]
        
        # Fallback to getting content from embeddings (chunked)
        client = self.clients[doc_type]
        content = client.get_document_by_id(doc_id)
        
        if content is None:
            log_warning(f"Document not found: {doc_id}")
        
        return content
    
    def update_document(
        self,
        doc_id: str,
        doc_type: str,
        content: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update a document.
        
        Args:
            doc_id: Document ID
            doc_type: Type of document
            content: New content
            name: New name
            description: New description
            metadata: Additional metadata updates
            
        Returns:
            Success status
        """
        if doc_type not in self.DOCUMENT_TYPES:
            raise ValueError(f"Invalid document type: {doc_type}")
        
        try:
            # Update in document storage
            result = self.document_storage.update_document(
                document_id=doc_id,
                doc_type=doc_type,
                name=name,
                content=content,
                description=description,
                metadata=metadata
            )
            
            if result["success"]:
                # If content was updated, re-index for search
                if content is not None:
                    client = self.clients[doc_type]
                    
                    # Delete old embeddings
                    try:
                        # Get all chunks for this document
                        old_results = client.query(
                            query_texts=[""],
                            n_results=1000
                        )
                        
                        # Find chunks that belong to this document
                        chunks_to_delete = []
                        if old_results["ids"] and old_results["ids"][0]:
                            for i, metadata in enumerate(old_results["metadatas"][0]):
                                if metadata and metadata.get("name") == name:
                                    chunks_to_delete.append(old_results["ids"][0][i])
                        
                        if chunks_to_delete:
                            client.delete_documents(chunks_to_delete)
                        
                        # Re-index with new content
                        doc_metadata = {
                            'name': name or doc_id,
                            'description': description or f"Updated {doc_type}",
                            'doc_type': doc_type,
                            'created_at': datetime.now().isoformat(),
                            'last_modified': datetime.now().isoformat(),
                            **(metadata or {})
                        }
                        
                        client.add_documents_with_context(
                            content=content,
                            context_info=doc_metadata,
                            use_llm_context=True
                        )
                        
                    except Exception as e:
                        log_warning(f"Failed to re-index document {doc_id}: {str(e)}")
                
                log_info(f"Updated {doc_type}: {doc_id}")
                return True
            else:
                log_error(f"Failed to update document {doc_id}: {result['error']}")
                return False
            
        except Exception as e:
            log_error(f"Failed to update document {doc_id}: {str(e)}")
            return False
    
    def delete_document(self, doc_id: str, doc_type: str) -> bool:
        """Delete a document.
        
        Args:
            doc_id: Document ID
            doc_type: Type of document
            
        Returns:
            Success status
        """
        if doc_type not in self.DOCUMENT_TYPES:
            raise ValueError(f"Invalid document type: {doc_type}")
        
        try:
            # Delete from document storage
            result = self.document_storage.delete_document(doc_id, doc_type)
            
            if result["success"]:
                # Also delete embeddings
                client = self.clients[doc_type]
                
                try:
                    # Get all chunks for this document by searching for it
                    results = client.query(
                        query_texts=[""],
                        n_results=1000
                    )
                    
                    chunks_to_delete = []
                    if results["ids"] and results["ids"][0]:
                        # Get document name to match chunks
                        doc = self.document_storage.get_document(doc_id, doc_type)
                        doc_name = doc["name"] if doc else None
                        
                        for i, metadata in enumerate(results["metadatas"][0]):
                            if metadata and (
                                metadata.get("name") == doc_name or 
                                results["ids"][0][i] == doc_id
                            ):
                                chunks_to_delete.append(results["ids"][0][i])
                    
                    if chunks_to_delete:
                        client.delete_documents(chunks_to_delete)
                        log_info(f"Deleted {len(chunks_to_delete)} embedding chunks for {doc_id}")
                
                except Exception as e:
                    log_warning(f"Failed to delete embeddings for {doc_id}: {str(e)}")
                
                log_info(f"Deleted {doc_type}: {doc_id}")
                return True
            else:
                log_error(f"Failed to delete document {doc_id}: {result['error']}")
                return False
            
        except Exception as e:
            log_error(f"Failed to delete document {doc_id}: {str(e)}")
            return False
    
    def search_documents(
        self,
        query: str,
        doc_type: Optional[str] = None,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search documents by content.
        
        Args:
            query: Search query
            doc_type: Optional document type filter
            n_results: Number of results to return
            
        Returns:
            Search results with document information
        """
        results = []
        
        # Search in specified type or all types
        types_to_search = [doc_type] if doc_type else list(self.DOCUMENT_TYPES.keys())
        
        for dtype in types_to_search:
            if dtype not in self.DOCUMENT_TYPES:
                continue
                
            client = self.clients[dtype]
            search_results = client.query(
                query_texts=[query],
                n_results=n_results,
                where=None  # Search in both main documents and chunks
            )
            
            if search_results["ids"] and search_results["ids"][0]:
                for i in range(len(search_results["ids"][0])):
                    doc_id = search_results["ids"][0][i]
                    content = search_results["documents"][0][i]
                    metadata = search_results["metadatas"][0][i]
                    similarity = search_results["distances"][0][i]
                    
                    results.append({
                        "id": doc_id,
                        "doc_type": dtype,
                        "name": metadata.get("name", "Untitled"),
                        "content_snippet": content[:200] + "..." if len(content) > 200 else content,
                        "similarity": similarity,
                        "metadata": metadata,
                        "is_main_document": metadata.get("is_main_document", False)
                    })
        
        # Sort by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        log_info(f"Search for '{query}' returned {len(results)} results")
        return results[:n_results]
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for all document collections.
        
        Returns:
            Statistics for each document type
        """
        stats = {}
        
        for doc_type, client in self.clients.items():
            try:
                collection_stats = client.get_collection_stats()
                stats[doc_type] = collection_stats
            except Exception as e:
                log_error(f"Failed to get stats for {doc_type}: {str(e)}")
                stats[doc_type] = {"error": str(e)}
        
        return stats