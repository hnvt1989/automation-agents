"""Supabase vector storage client using pgvector and OpenAI embeddings."""

import os
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import openai
from supabase import create_client, Client

from src.utils.logging import log_info, log_error, log_warning
from src.core.config import get_settings
from src.core.constants import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP
)
from src.storage.contextual_chunker import ContextualChunker, ChunkContext


class SupabaseVectorClient:
    """Client for vector operations using Supabase pgvector and OpenAI embeddings."""
    
    def __init__(self, collection_name: str = "default", enable_contextual: bool = True, user_id: Optional[str] = None):
        """Initialize Supabase vector client.
        
        Args:
            collection_name: Name of the collection (used for filtering)
            enable_contextual: Whether to enable contextual chunking
            user_id: User ID for filtering user-specific data
        """
        self.settings = get_settings()
        self.collection_name = collection_name
        self.enable_contextual = enable_contextual
        self.user_id = user_id
        
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.client: Client = create_client(supabase_url, supabase_key)
        
        # Initialize OpenAI for embeddings
        openai.api_key = self.settings.openai_api_key or self.settings.llm_api_key
        self.embedding_model = DEFAULT_EMBEDDING_MODEL
        
        # Initialize contextual chunker if enabled
        self.contextual_chunker = ContextualChunker() if enable_contextual else None
        
        log_info(f"SupabaseVectorClient initialized for collection '{collection_name}' (contextual: {enable_contextual})")
    
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            response = openai.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            log_error(f"Error generating embeddings: {str(e)}")
            raise
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """Add documents to the vector store.
        
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
                ids = [str(uuid.uuid4()) for _ in documents]
            
            # Ensure metadatas match document count
            if metadatas is None:
                metadatas = [{} for _ in documents]
            
            # Generate embeddings
            embeddings = self._get_embeddings(documents)
            
            # Prepare data for insertion
            records = []
            for i, (doc, embedding, doc_id, metadata) in enumerate(
                zip(documents, embeddings, ids, metadatas)
            ):
                record = {
                    "collection_name": self.collection_name,
                    "document_id": doc_id,
                    "content": doc,
                    "embedding": embedding,
                    "metadata": json.dumps(metadata) if metadata else json.dumps({}),
                    "user_id": self.user_id
                }
                records.append(record)
            
            # Upsert into Supabase (update if exists, insert if not)
            result = self.client.table("document_embeddings").upsert(
                records,
                on_conflict="collection_name,document_id"
            ).execute()
            
            log_info(f"Added {len(documents)} documents to collection '{self.collection_name}'")
            
        except Exception as e:
            log_error(f"Failed to add documents: {str(e)}")
            raise
    
    def query(
        self,
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query the vector store.
        
        Args:
            query_texts: List of query strings
            n_results: Number of results to return
            where: Optional metadata filter
            
        Returns:
            Query results with documents, distances, and metadata
        """
        try:
            # For now, use the first query text (can extend to multiple)
            query_text = query_texts[0] if query_texts else ""
            
            if not query_text:
                log_warning("Empty query text provided")
                return {
                    "ids": [[]],
                    "documents": [[]],
                    "distances": [[]],
                    "metadatas": [[]]
                }
            
            # Generate query embedding
            query_embeddings = self._get_embeddings([query_text])
            query_embedding = query_embeddings[0]
            
            # Build the query
            query = self.client.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "match_count": n_results,
                    "filter_collection": self.collection_name,
                    "filter_metadata": json.dumps(where) if where else None,
                    "filter_user_id": self.user_id
                }
            )
            
            result = query.execute()
            
            # Format results to match ChromaDB interface
            if result.data:
                ids = [[item["document_id"] for item in result.data]]
                documents = [[item["content"] for item in result.data]]
                distances = [[item["similarity"] for item in result.data]]
                metadatas = [[json.loads(item["metadata"]) for item in result.data]]
                
                formatted_results = {
                    "ids": ids,
                    "documents": documents,
                    "distances": distances,
                    "metadatas": metadatas
                }
            else:
                formatted_results = {
                    "ids": [[]],
                    "documents": [[]],
                    "distances": [[]],
                    "metadatas": [[]]
                }
            
            log_info(f"Query returned {len(formatted_results['ids'][0])} results")
            return formatted_results
            
        except Exception as e:
            log_error(f"Failed to query collection: {str(e)}")
            raise
    
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
            updates = {}
            
            if documents:
                # Generate new embeddings
                embeddings = self._get_embeddings(documents)
                updates["embedding"] = embeddings[0]  # Handle one at a time for now
                updates["content"] = documents[0]
            
            if metadatas:
                updates["metadata"] = json.dumps(metadatas[0])
            
            # Update in Supabase
            result = self.client.table("document_embeddings") \
                .update(updates) \
                .eq("document_id", ids[0]) \
                .eq("collection_name", self.collection_name) \
                .execute()
            
            log_info(f"Updated {len(ids)} documents")
            
        except Exception as e:
            log_error(f"Failed to update documents: {str(e)}")
            raise
    
    def delete_documents(self, ids: List[str]) -> None:
        """Delete documents by ID.
        
        Args:
            ids: IDs of documents to delete
        """
        try:
            result = self.client.table("document_embeddings") \
                .delete() \
                .in_("document_id", ids) \
                .eq("collection_name", self.collection_name) \
                .execute()
            
            log_info(f"Deleted {len(ids)} documents")
            
        except Exception as e:
            log_error(f"Failed to delete documents: {str(e)}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            # Count documents in collection
            result = self.client.table("document_embeddings") \
                .select("*", count="exact") \
                .eq("collection_name", self.collection_name) \
                .execute()
            
            count = result.count if result else 0
            
            return {
                "name": self.collection_name,
                "count": count,
                "embedding_model": self.embedding_model,
                "vector_dimensions": 1536  # OpenAI ada-002
            }
            
        except Exception as e:
            log_error(f"Failed to get collection stats: {str(e)}")
            raise
    
    def clear_collection(self) -> None:
        """Clear all documents from the collection."""
        try:
            result = self.client.table("document_embeddings") \
                .delete() \
                .eq("collection_name", self.collection_name) \
                .execute()
            
            log_info(f"Cleared collection '{self.collection_name}'")
            
        except Exception as e:
            log_error(f"Failed to clear collection: {str(e)}")
            raise
    
    def get_document_by_id(self, document_id: str) -> Optional[str]:
        """Get document content by ID.
        
        Args:
            document_id: ID of the document to retrieve
            
        Returns:
            Document content or None if not found
        """
        try:
            result = self.client.table("document_embeddings") \
                .select("content") \
                .eq("document_id", document_id) \
                .eq("collection_name", self.collection_name) \
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]["content"]
            
            return None
            
        except Exception as e:
            log_error(f"Failed to get document by ID {document_id}: {str(e)}")
            return None
    
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
    
    def add_documents_with_context(
        self,
        content: str,
        context_info: Dict[str, Any],
        use_llm_context: bool = False
    ) -> List[str]:
        """Add a document with contextual chunking.
        
        Args:
            content: Document content
            context_info: Context information for the document
            use_llm_context: Whether to use LLM for context generation
            
        Returns:
            List of document IDs
        """
        if not self.contextual_chunker:
            log_warning("Contextual chunker not enabled, falling back to regular chunking")
            chunks = self.chunk_text(content)
            metadatas = [context_info.copy() for _ in chunks]
            self.add_documents(chunks, metadatas=metadatas)
            return []
        
        try:
            # Create contextual chunks
            chunk_contexts = self.contextual_chunker.create_contextual_chunks(
                content=content,
                chunk_size=DEFAULT_CHUNK_SIZE,
                chunk_overlap=DEFAULT_CHUNK_OVERLAP,
                context_info=context_info,
                use_llm_context=use_llm_context
            )
            
            # Prepare documents and metadata
            documents = []
            metadatas = []
            ids = []
            
            for chunk_ctx in chunk_contexts:
                # Store both original and contextual content
                documents.append(chunk_ctx.contextual_text)
                
                # Enhanced metadata
                metadata = chunk_ctx.metadata.copy()
                metadata['original_content'] = chunk_ctx.original_text
                metadata['has_context'] = True
                metadatas.append(metadata)
                
                # Generate ID
                doc_id = str(uuid.uuid4())
                ids.append(doc_id)
            
            # Add to vector store
            self.add_documents(documents, metadatas=metadatas, ids=ids)
            
            log_info(f"Added {len(documents)} contextual chunks to collection '{self.collection_name}'")
            return ids
            
        except Exception as e:
            log_error(f"Failed to add contextual documents: {str(e)}")
            raise
    
    def hybrid_search(
        self,
        query: str,
        n_results: int = 5,
        alpha: float = 0.5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Perform hybrid search combining vector and full-text search.
        
        Args:
            query: Search query
            n_results: Number of results
            alpha: Weight for vector search (1-alpha for text search)
            where: Optional metadata filter
            
        Returns:
            Combined search results
        """
        try:
            # Get vector search results
            vector_results = self.query([query], n_results=n_results * 2, where=where)
            
            # Get full-text search results
            text_results = self.full_text_search(query, n_results=n_results * 2, where=where)
            
            # Combine results using reciprocal rank fusion
            combined_results = self._reciprocal_rank_fusion(
                [vector_results, text_results],
                weights=[alpha, 1 - alpha]
            )
            
            # Take top n_results
            final_results = {
                "ids": [[r["id"] for r in combined_results[:n_results]]],
                "documents": [[r["document"] for r in combined_results[:n_results]]],
                "distances": [[r["score"] for r in combined_results[:n_results]]],
                "metadatas": [[r["metadata"] for r in combined_results[:n_results]]]
            }
            
            log_info(f"Hybrid search returned {len(final_results['ids'][0])} results")
            return final_results
            
        except Exception as e:
            log_error(f"Hybrid search failed: {str(e)}")
            # Fallback to vector search
            return self.query([query], n_results=n_results, where=where)
    
    def full_text_search(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Perform full-text search using PostgreSQL.
        
        Args:
            query: Search query
            n_results: Number of results
            where: Optional metadata filter
            
        Returns:
            Search results
        """
        try:
            # Since we're using the minimal migration, continue with vector search
            # The hybrid_search function in the database will handle this
            log_info("Using vector search (full-text indexes not created due to memory constraints)")
            return self.query([query], n_results=n_results, where=where)
            
        except Exception as e:
            log_error(f"Full-text search failed: {str(e)}")
            # Return empty results
            return {
                "ids": [[]],
                "documents": [[]],
                "distances": [[]],
                "metadatas": [[]]
            }
    
    def _reciprocal_rank_fusion(
        self,
        result_lists: List[Dict[str, Any]],
        weights: Optional[List[float]] = None,
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """Fuse multiple result lists using Reciprocal Rank Fusion.
        
        Args:
            result_lists: List of result dictionaries
            weights: Optional weights for each list
            k: RRF parameter
            
        Returns:
            Fused results
        """
        if not weights:
            weights = [1.0 / len(result_lists)] * len(result_lists)
        
        # Track scores for each document
        doc_scores = {}
        
        for list_idx, results in enumerate(result_lists):
            if not results["ids"] or not results["ids"][0]:
                continue
                
            for rank, doc_id in enumerate(results["ids"][0]):
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        "score": 0,
                        "document": results["documents"][0][rank],
                        "metadata": results["metadatas"][0][rank] if results["metadatas"] else {},
                        "id": doc_id
                    }
                
                # Add weighted RRF score
                doc_scores[doc_id]["score"] += weights[list_idx] / (k + rank + 1)
        
        # Sort by score
        sorted_docs = sorted(
            doc_scores.values(),
            key=lambda x: x["score"],
            reverse=True
        )
        
        return sorted_docs


# SQL function to create in Supabase for similarity search
MATCH_DOCUMENTS_FUNCTION = """
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    match_count int,
    filter_collection text DEFAULT NULL,
    filter_metadata jsonb DEFAULT NULL,
    filter_user_id uuid DEFAULT NULL
)
RETURNS TABLE (
    document_id text,
    content text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        de.document_id::text,
        de.content::text,
        de.metadata::jsonb,
        (1 - (de.embedding <=> query_embedding))::float AS similarity
    FROM document_embeddings de
    WHERE
        (filter_collection IS NULL OR de.collection_name = filter_collection)
        AND (filter_metadata IS NULL OR de.metadata @> filter_metadata)
        AND (filter_user_id IS NULL OR de.user_id = filter_user_id)
    ORDER BY de.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""