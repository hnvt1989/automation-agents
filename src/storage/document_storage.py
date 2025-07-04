"""Document storage for full documents using Supabase."""

import os
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from supabase import create_client, Client

from src.utils.logging import log_info, log_error, log_warning
from src.core.config import get_settings


# SQL schema for full document storage
DOCUMENT_STORAGE_SCHEMA = """
-- Create documents table for storing full documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    metadata JSONB DEFAULT '{}',
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_document_id ON documents(document_id);
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);

-- Create notes table for storing full notes
CREATE TABLE IF NOT EXISTS notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create indexes for notes
CREATE INDEX IF NOT EXISTS idx_notes_document_id ON notes(document_id);
CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes(user_id);
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at);

-- Create memos table for storing full memos
CREATE TABLE IF NOT EXISTS memos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create indexes for memos
CREATE INDEX IF NOT EXISTS idx_memos_document_id ON memos(document_id);
CREATE INDEX IF NOT EXISTS idx_memos_user_id ON memos(user_id);
CREATE INDEX IF NOT EXISTS idx_memos_created_at ON memos(created_at);

-- Create interviews table for storing full interviews
CREATE TABLE IF NOT EXISTS interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create indexes for interviews
CREATE INDEX IF NOT EXISTS idx_interviews_document_id ON interviews(document_id);
CREATE INDEX IF NOT EXISTS idx_interviews_user_id ON interviews(user_id);
CREATE INDEX IF NOT EXISTS idx_interviews_created_at ON interviews(created_at);
"""


class DocumentStorage:
    """Handles full document storage and retrieval using Supabase."""
    
    # Map document types to table names
    TABLE_MAPPING = {
        "document": "documents",
        "note": "notes", 
        "memo": "memos",
        "interview": "interviews"
    }
    
    def __init__(self, user_id: Optional[str] = None):
        """Initialize the document storage."""
        self.settings = get_settings()
        self.user_id = user_id
        self.tables_available = False
        
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.client: Client = create_client(supabase_url, supabase_key)
        
        # Test if tables are available
        try:
            self.client.table("documents").select("id").limit(1).execute()
            self.tables_available = True
            log_info(f"DocumentStorage initialized for user: {user_id} (tables available)")
        except Exception as e:
            log_warning(f"DocumentStorage tables not available: {e}")
            log_info(f"DocumentStorage initialized for user: {user_id} (fallback mode)")
    
    def create_document(
        self,
        document_id: str,
        name: str,
        content: str,
        doc_type: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new document.
        
        Args:
            document_id: Unique document identifier
            name: Document name
            content: Full document content
            doc_type: Type of document (document, note, memo, interview)
            description: Optional description
            metadata: Optional metadata
            
        Returns:
            Result dictionary with success status and document data
        """
        try:
            if not self.tables_available:
                return {"success": False, "error": "Document storage tables not available"}
            
            if doc_type not in self.TABLE_MAPPING:
                return {"success": False, "error": f"Invalid document type: {doc_type}"}
            
            table_name = self.TABLE_MAPPING[doc_type]
            
            # Prepare document data
            doc_data = {
                "document_id": document_id,
                "name": name,
                "content": content,
                "doc_type": doc_type,
                "description": description or "",
                "metadata": json.dumps(metadata or {}),
                "user_id": self.user_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Insert document
            result = self.client.table(table_name).insert(doc_data).execute()
            
            if result.data:
                log_info(f"Created {doc_type}: {name} (ID: {document_id})")
                return {
                    "success": True,
                    "document": {
                        "id": document_id,
                        "name": name,
                        "description": description,
                        "doc_type": doc_type,
                        "created_at": doc_data["created_at"]
                    }
                }
            else:
                return {"success": False, "error": "Failed to create document"}
                
        except Exception as e:
            log_error(f"Error creating document: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_document(self, document_id: str, doc_type: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID.
        
        Args:
            document_id: Document ID
            doc_type: Document type
            
        Returns:
            Document data or None if not found
        """
        try:
            if doc_type not in self.TABLE_MAPPING:
                log_error(f"Invalid document type: {doc_type}")
                return None
            
            table_name = self.TABLE_MAPPING[doc_type]
            
            # Build query
            query = self.client.table(table_name).select("*").eq("document_id", document_id)
            
            # Add user filter if user_id is provided
            if self.user_id:
                query = query.eq("user_id", self.user_id)
            
            result = query.execute()
            
            if result.data and len(result.data) > 0:
                doc = result.data[0]
                return {
                    "id": doc["document_id"],
                    "name": doc["name"],
                    "description": doc["description"],
                    "content": doc["content"],
                    "doc_type": doc["doc_type"],
                    "metadata": json.loads(doc["metadata"]) if doc["metadata"] else {},
                    "created_at": doc["created_at"],
                    "updated_at": doc["updated_at"]
                }
            
            return None
            
        except Exception as e:
            log_error(f"Error getting document {document_id}: {str(e)}")
            return None
    
    def get_documents(self, doc_type: str) -> List[Dict[str, Any]]:
        """Get all documents of a specific type.
        
        Args:
            doc_type: Document type
            
        Returns:
            List of documents
        """
        try:
            if doc_type not in self.TABLE_MAPPING:
                log_error(f"Invalid document type: {doc_type}")
                return []
            
            table_name = self.TABLE_MAPPING[doc_type]
            
            # Build query
            query = self.client.table(table_name).select("*")
            
            # Add user filter if user_id is provided
            if self.user_id:
                query = query.eq("user_id", self.user_id)
            
            # Order by created_at descending
            result = query.order("created_at", desc=True).execute()
            
            documents = []
            for doc in result.data:
                documents.append({
                    "id": doc["document_id"],
                    "name": doc["name"],
                    "description": doc["description"],
                    "doc_type": doc["doc_type"],
                    "metadata": json.loads(doc["metadata"]) if doc["metadata"] else {},
                    "created_at": doc["created_at"],
                    "updated_at": doc["updated_at"]
                })
            
            log_info(f"Retrieved {len(documents)} {doc_type}s")
            return documents
            
        except Exception as e:
            log_error(f"Error getting documents: {str(e)}")
            return []
    
    def update_document(
        self,
        document_id: str,
        doc_type: str,
        name: Optional[str] = None,
        content: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update a document.
        
        Args:
            document_id: Document ID
            doc_type: Document type
            name: New name
            content: New content
            description: New description
            metadata: New metadata
            
        Returns:
            Result dictionary with success status
        """
        try:
            if doc_type not in self.TABLE_MAPPING:
                return {"success": False, "error": f"Invalid document type: {doc_type}"}
            
            table_name = self.TABLE_MAPPING[doc_type]
            
            # Prepare update data
            update_data = {
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if name is not None:
                update_data["name"] = name
            if content is not None:
                update_data["content"] = content
            if description is not None:
                update_data["description"] = description
            if metadata is not None:
                update_data["metadata"] = json.dumps(metadata)
            
            # Build query
            query = self.client.table(table_name).update(update_data).eq("document_id", document_id)
            
            # Add user filter if user_id is provided
            if self.user_id:
                query = query.eq("user_id", self.user_id)
            
            result = query.execute()
            
            if result.data:
                log_info(f"Updated {doc_type}: {document_id}")
                return {"success": True}
            else:
                return {"success": False, "error": "Document not found or no permission"}
                
        except Exception as e:
            log_error(f"Error updating document {document_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def delete_document(self, document_id: str, doc_type: str) -> Dict[str, Any]:
        """Delete a document.
        
        Args:
            document_id: Document ID
            doc_type: Document type
            
        Returns:
            Result dictionary with success status
        """
        try:
            if doc_type not in self.TABLE_MAPPING:
                return {"success": False, "error": f"Invalid document type: {doc_type}"}
            
            table_name = self.TABLE_MAPPING[doc_type]
            
            # Build query
            query = self.client.table(table_name).delete().eq("document_id", document_id)
            
            # Add user filter if user_id is provided
            if self.user_id:
                query = query.eq("user_id", self.user_id)
            
            result = query.execute()
            
            if result.data:
                log_info(f"Deleted {doc_type}: {document_id}")
                return {"success": True}
            else:
                return {"success": False, "error": "Document not found or no permission"}
                
        except Exception as e:
            log_error(f"Error deleting document {document_id}: {str(e)}")
            return {"success": False, "error": str(e)}