"""Document management using Supabase storage."""

import os
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from .supabase_vector import SupabaseVectorClient
from ..utils.logging import log_info, log_error, log_warning


class SupabaseDocumentManager:
    """Manages documents in Supabase with full CRUD operations."""
    
    def __init__(self, collection_name: str = "documents", user_id: Optional[str] = None):
        """Initialize the document manager.
        
        Args:
            collection_name: Name of the collection for documents
            user_id: User ID for filtering user-specific documents
        """
        self.collection_name = collection_name
        self.user_id = user_id
        self.client = SupabaseVectorClient(collection_name=collection_name, user_id=user_id)
        
        log_info(f"SupabaseDocumentManager initialized for collection '{collection_name}'")
    
    def create_document(
        self,
        filename: str,
        content: str,
        category: str = "document",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new document.
        
        Args:
            filename: Name of the document
            content: Document content
            category: Document category
            metadata: Additional metadata
            
        Returns:
            Document ID
        """
        try:
            if not content.strip():
                raise ValueError("Document content cannot be empty")
            
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Create metadata
            doc_metadata = {
                "file_path": filename,
                "filename": filename,
                "category": category,
                "file_size": len(content.encode('utf-8')),
                "created_at": datetime.now().isoformat(),
                "modified_at": datetime.now().isoformat(),
                "file_extension": Path(filename).suffix,
                "document_type": "user_created"
            }
            
            # Add user-provided metadata
            if metadata:
                doc_metadata.update(metadata)
            
            # Add to Supabase using contextual chunking
            chunk_ids = self.client.add_documents_with_context(
                content=content,
                context_info=doc_metadata,
                use_llm_context=False
            )
            
            log_info(f"Created document '{filename}' with {len(chunk_ids)} chunks")
            return doc_id
            
        except Exception as e:
            log_error(f"Failed to create document '{filename}': {str(e)}")
            raise
    
    def get_document(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get a document by filename.
        
        Args:
            filename: Name of the document
            
        Returns:
            Document data or None if not found
        """
        try:
            # Search for document chunks by filename
            # Try multiple search strategies
            results = None
            
            # Strategy 1: Search by metadata filter
            try:
                results = self.client.query(
                    [filename],  # Use filename as query
                    n_results=50,
                    where={"filename": filename}
                )
                if results and results["documents"] and results["documents"][0]:
                    log_info(f"Found document using metadata filter: {len(results['documents'][0])} chunks")
                else:
                    results = None
            except Exception as e:
                log_warning(f"Metadata filter search failed: {e}")
            
            # Strategy 2: If metadata filter failed, try broader search
            if not results or not results["documents"] or not results["documents"][0]:
                try:
                    results = self.client.query(
                        [filename.replace('.md', '').replace('_', ' ')],  # Clean filename for search
                        n_results=50
                    )
                    
                    # Filter results by filename in metadata
                    if results and results["documents"] and results["documents"][0]:
                        filtered_docs = []
                        filtered_metadata = []
                        filtered_distances = []
                        
                        for i, doc in enumerate(results["documents"][0]):
                            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                            if metadata.get("filename") == filename:
                                filtered_docs.append(doc)
                                filtered_metadata.append(metadata)
                                filtered_distances.append(results["distances"][0][i])
                        
                        if filtered_docs:
                            results = {
                                "documents": [filtered_docs],
                                "metadatas": [filtered_metadata],
                                "distances": [filtered_distances]
                            }
                            log_info(f"Found document using filtered search: {len(filtered_docs)} chunks")
                        else:
                            results = None
                except Exception as e:
                    log_warning(f"Filtered search failed: {e}")
                    results = None
            
            if not results["documents"] or not results["documents"][0]:
                return None
            
            # Reconstruct document from chunks
            chunks = []
            metadata = None
            
            for i, chunk in enumerate(results["documents"][0]):
                chunk_metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                
                # Use metadata from first chunk
                if metadata is None:
                    metadata = chunk_metadata
                
                # Extract original content if available
                original_content = chunk_metadata.get('original_content', chunk)
                chunks.append({
                    "content": original_content,
                    "chunk_index": chunk_metadata.get('chunk_index', i),
                    "distance": results["distances"][0][i]
                })
            
            # Sort chunks by index and combine
            chunks.sort(key=lambda x: x.get('chunk_index', 0))
            full_content = "\n".join(chunk["content"] for chunk in chunks)
            
            return {
                "filename": filename,
                "content": full_content,
                "metadata": metadata,
                "chunk_count": len(chunks)
            }
            
        except Exception as e:
            log_error(f"Failed to get document '{filename}': {str(e)}")
            return None
    
    def update_document(
        self,
        filename: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update an existing document.
        
        Args:
            filename: Name of the document
            content: New document content
            metadata: Additional metadata updates
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not content.strip():
                raise ValueError("Document content cannot be empty")
            
            # First, delete existing document chunks
            if not self.delete_document(filename):
                log_warning(f"Document '{filename}' not found, creating new one")
            
            # Create updated document
            doc_metadata = {
                "file_path": filename,
                "filename": filename,
                "category": "document",
                "file_size": len(content.encode('utf-8')),
                "created_at": datetime.now().isoformat(),
                "modified_at": datetime.now().isoformat(),
                "file_extension": Path(filename).suffix,
                "document_type": "user_updated"
            }
            
            # Add user-provided metadata
            if metadata:
                doc_metadata.update(metadata)
            
            # Add updated content
            chunk_ids = self.client.add_documents_with_context(
                content=content,
                context_info=doc_metadata,
                use_llm_context=False
            )
            
            log_info(f"Updated document '{filename}' with {len(chunk_ids)} chunks")
            return True
            
        except Exception as e:
            log_error(f"Failed to update document '{filename}': {str(e)}")
            return False
    
    def delete_document(self, filename: str) -> bool:
        """Delete a document by filename.
        
        Args:
            filename: Name of the document
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find all chunks for this document using same strategy as get_document
            results = None
            
            # Strategy 1: Search by metadata filter
            try:
                results = self.client.query(
                    [filename],
                    n_results=100,
                    where={"filename": filename}
                )
                if results and results["documents"] and results["documents"][0]:
                    log_info(f"Found document for deletion using metadata filter: {len(results['documents'][0])} chunks")
                else:
                    results = None
            except Exception as e:
                log_warning(f"Metadata filter search for deletion failed: {e}")
            
            # Strategy 2: If metadata filter failed, try broader search
            if not results or not results["documents"] or not results["documents"][0]:
                try:
                    results = self.client.query(
                        [filename.replace('.md', '').replace('_', ' ')],
                        n_results=100
                    )
                    
                    # Filter results by filename in metadata
                    if results and results["documents"] and results["documents"][0]:
                        filtered_ids = []
                        
                        for i, doc in enumerate(results["documents"][0]):
                            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                            if metadata.get("filename") == filename:
                                filtered_ids.append(results["ids"][0][i])
                        
                        if filtered_ids:
                            # Reconstruct results with filtered IDs
                            results = {"ids": [filtered_ids]}
                            log_info(f"Found document for deletion using filtered search: {len(filtered_ids)} chunks")
                        else:
                            results = None
                except Exception as e:
                    log_warning(f"Filtered search for deletion failed: {e}")
                    results = None
            
            if not results["ids"] or not results["ids"][0]:
                log_warning(f"Document '{filename}' not found")
                return False
            
            # Delete all chunks
            chunk_ids = results["ids"][0]
            self.client.delete_documents(chunk_ids)
            
            log_info(f"Deleted document '{filename}' ({len(chunk_ids)} chunks)")
            return True
            
        except Exception as e:
            log_error(f"Failed to delete document '{filename}': {str(e)}")
            return False
    
    def list_documents(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all documents.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of document summaries
        """
        try:
            # Get collection stats first
            stats = self.client.get_collection_stats()
            
            if stats["count"] == 0:
                return []
            
            # Query for documents with a broad search
            where_filter = {}
            if category:
                where_filter["category"] = category
            
            # Use a generic query to get documents
            results = self.client.query(
                ["document"],  # Generic search term
                n_results=min(stats["count"], 100),  # Limit to reasonable number
                where=where_filter if where_filter else None
            )
            
            if not results["documents"] or not results["documents"][0]:
                return []
            
            # Group by filename to get unique documents
            documents = {}
            
            for i, chunk in enumerate(results["documents"][0]):
                chunk_metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                filename = chunk_metadata.get("filename", f"unknown_{i}")
                
                if filename not in documents:
                    documents[filename] = {
                        "filename": filename,
                        "category": chunk_metadata.get("category", "unknown"),
                        "file_size": chunk_metadata.get("file_size", 0),
                        "created_at": chunk_metadata.get("created_at"),
                        "modified_at": chunk_metadata.get("modified_at"),
                        "file_extension": chunk_metadata.get("file_extension", ".md"),
                        "chunk_count": 0
                    }
                
                documents[filename]["chunk_count"] += 1
            
            # Return sorted list
            doc_list = list(documents.values())
            doc_list.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            
            log_info(f"Listed {len(doc_list)} documents")
            return doc_list
            
        except Exception as e:
            log_error(f"Failed to list documents: {str(e)}")
            return []
    
    def search_documents(
        self,
        query: str,
        n_results: int = 10,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search documents by content.
        
        Args:
            query: Search query
            n_results: Number of results to return
            category: Optional category filter
            
        Returns:
            List of search results with content snippets
        """
        try:
            where_filter = {}
            if category:
                where_filter["category"] = category
            
            # Search using vector similarity
            results = self.client.query(
                [query],
                n_results=n_results,
                where=where_filter if where_filter else None
            )
            
            if not results["documents"] or not results["documents"][0]:
                return []
            
            search_results = []
            
            for i, chunk in enumerate(results["documents"][0]):
                chunk_metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                
                result = {
                    "filename": chunk_metadata.get("filename", "unknown"),
                    "content_snippet": chunk[:200] + "..." if len(chunk) > 200 else chunk,
                    "full_content": chunk,
                    "similarity": results["distances"][0][i],
                    "metadata": chunk_metadata
                }
                
                search_results.append(result)
            
            log_info(f"Search for '{query}' returned {len(search_results)} results")
            return search_results
            
        except Exception as e:
            log_error(f"Failed to search documents: {str(e)}")
            return []
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the document collection.
        
        Returns:
            Collection statistics and information
        """
        try:
            stats = self.client.get_collection_stats()
            
            # Get document count by listing unique filenames
            documents = self.list_documents()
            
            return {
                "collection_name": self.collection_name,
                "total_chunks": stats["count"],
                "total_documents": len(documents),
                "embedding_model": stats["embedding_model"],
                "vector_dimensions": stats["vector_dimensions"]
            }
            
        except Exception as e:
            log_error(f"Failed to get collection info: {str(e)}")
            return {
                "collection_name": self.collection_name,
                "total_chunks": 0,
                "total_documents": 0,
                "embedding_model": "unknown",
                "vector_dimensions": 0
            }


# Helper function for backward compatibility
def get_document_manager(user_id: Optional[str] = None) -> SupabaseDocumentManager:
    """Get a document manager instance.
    
    Args:
        user_id: Optional user ID for filtering
        
    Returns:
        SupabaseDocumentManager instance
    """
    return SupabaseDocumentManager(collection_name="documents", user_id=user_id)