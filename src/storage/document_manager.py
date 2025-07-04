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
        # Create separate collections for each document type
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
        """Add a document to vector storage.
        
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
        
        client = self.clients[doc_type]
        
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
        
        # Add document with contextual chunking
        doc_ids = client.add_documents_with_context(
            content=content,
            context_info=doc_metadata,
            use_llm_context=True
        )
        
        # Store the main document metadata
        main_doc_id = str(uuid.uuid4())
        main_metadata = doc_metadata.copy()
        main_metadata['is_main_document'] = True
        main_metadata['chunk_ids'] = doc_ids
        
        client.add_documents(
            documents=[content],
            metadatas=[main_metadata],
            ids=[main_doc_id]
        )
        
        log_info(f"Added {doc_type}: {name} with ID: {main_doc_id}")
        return main_doc_id
    
    def get_documents(self, doc_type: str) -> List[Dict[str, Any]]:
        """Get all documents of a specific type.
        
        Args:
            doc_type: Type of document to retrieve
            
        Returns:
            List of document metadata
        """
        if doc_type not in self.DOCUMENT_TYPES:
            raise ValueError(f"Invalid document type: {doc_type}")
        
        client = self.clients[doc_type]
        
        # Query for main documents only
        results = client.query(
            query_texts=[""],
            n_results=1000,  # Large number to get all
            where={"is_main_document": True}
        )
        
        documents = []
        if results["metadatas"] and results["metadatas"][0]:
            for i, metadata in enumerate(results["metadatas"][0]):
                doc_id = results["ids"][0][i]
                
                documents.append({
                    "id": doc_id,
                    "name": metadata.get("name", "Untitled"),
                    "description": metadata.get("description", ""),
                    "filename": metadata.get("filename", ""),
                    "doc_type": metadata.get("doc_type", doc_type),
                    "created_at": metadata.get("created_at"),
                    "last_modified": metadata.get("last_modified"),
                    "path": f"supabase://{self.DOCUMENT_TYPES[doc_type]}/{doc_id}",
                    **{k: v for k, v in metadata.items() 
                       if k not in ['name', 'description', 'filename', 'doc_type', 'created_at', 'last_modified', 'is_main_document', 'chunk_ids']}
                })
        
        # Sort by last_modified descending
        documents.sort(key=lambda x: x.get("last_modified", ""), reverse=True)
        
        log_info(f"Retrieved {len(documents)} {doc_type}s")
        return documents
    
    def get_document_content(self, doc_id: str, doc_type: str) -> Optional[str]:
        """Get document content by ID.
        
        Args:
            doc_id: Document ID
            doc_type: Type of document
            
        Returns:
            Document content or None if not found
        """
        if doc_type not in self.DOCUMENT_TYPES:
            raise ValueError(f"Invalid document type: {doc_type}")
        
        client = self.clients[doc_type]
        
        # Query for the specific document
        results = client.query(
            query_texts=[""],
            n_results=1,
            where={"is_main_document": True}
        )
        
        if results["ids"] and results["ids"][0]:
            for i, result_id in enumerate(results["ids"][0]):
                if result_id == doc_id:
                    return results["documents"][0][i]
        
        log_warning(f"Document not found: {doc_id}")
        return None
    
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
        
        client = self.clients[doc_type]
        
        try:
            # Get current metadata
            current_results = client.query(
                query_texts=[""],
                n_results=1000,
                where={"is_main_document": True}
            )
            
            current_metadata = None
            doc_index = None
            
            if current_results["ids"] and current_results["ids"][0]:
                for i, result_id in enumerate(current_results["ids"][0]):
                    if result_id == doc_id:
                        current_metadata = current_results["metadatas"][0][i]
                        doc_index = i
                        break
            
            if current_metadata is None:
                log_error(f"Document not found for update: {doc_id}")
                return False
            
            # Update metadata
            updated_metadata = current_metadata.copy()
            updated_metadata['last_modified'] = datetime.now().isoformat()
            
            if name is not None:
                updated_metadata['name'] = name
            if description is not None:
                updated_metadata['description'] = description
            if metadata:
                updated_metadata.update(metadata)
            
            # Update document
            update_content = content if content is not None else current_results["documents"][0][doc_index]
            
            client.update_documents(
                ids=[doc_id],
                documents=[update_content],
                metadatas=[updated_metadata]
            )
            
            log_info(f"Updated {doc_type}: {doc_id}")
            return True
            
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
        
        client = self.clients[doc_type]
        
        try:
            # Get document metadata to find associated chunks
            results = client.query(
                query_texts=[""],
                n_results=1000,
                where={"is_main_document": True}
            )
            
            chunk_ids = []
            if results["ids"] and results["ids"][0]:
                for i, result_id in enumerate(results["ids"][0]):
                    if result_id == doc_id:
                        metadata = results["metadatas"][0][i]
                        chunk_ids = metadata.get("chunk_ids", [])
                        break
            
            # Delete main document and associated chunks
            all_ids = [doc_id] + chunk_ids
            client.delete_documents(all_ids)
            
            log_info(f"Deleted {doc_type}: {doc_id} and {len(chunk_ids)} chunks")
            return True
            
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