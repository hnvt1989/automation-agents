"""User authentication storage using Supabase."""

import os
import json
import hashlib
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from supabase import create_client, Client
import jwt

from src.utils.logging import log_info, log_error
from src.core.config import get_settings


class AuthStorage:
    """Handles user authentication and session management with Supabase."""
    
    def __init__(self):
        """Initialize the authentication storage."""
        self.settings = get_settings()
        
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.client: Client = create_client(supabase_url, supabase_key)
        
        # JWT secret for session tokens
        self.jwt_secret = os.getenv("JWT_SECRET", "your-secret-key-change-this")
        
        log_info("AuthStorage initialized")
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256.
        
        Note: As of the security update, passwords are pre-hashed on the client side.
        This method now performs a second hash for additional security (double hashing).
        """
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _generate_token(self, user_id: str, email: str) -> str:
        """Generate a JWT token for the user."""
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(days=7),  # 7 days expiry
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def _verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            log_error("Token has expired")
            return None
        except jwt.InvalidTokenError:
            log_error("Invalid token")
            return None
    
    def register_user(self, email: str, password: str) -> Dict[str, Any]:
        """Register a new user."""
        try:
            # Check if user already exists
            existing_user = self.client.table("users").select("*").eq("email", email).execute()
            if existing_user.data:
                return {"success": False, "error": "User already exists"}
            
            # Hash password
            password_hash = self._hash_password(password)
            
            # Create user record
            user_id = str(uuid.uuid4())
            user_data = {
                "id": user_id,
                "email": email,
                "password_hash": password_hash,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "is_active": True
            }
            
            # Insert user
            result = self.client.table("users").insert(user_data).execute()
            
            if result.data:
                # Generate token
                token = self._generate_token(user_id, email)
                
                log_info(f"User registered successfully: {email}")
                return {
                    "success": True,
                    "user": {
                        "id": user_id,
                        "email": email,
                        "created_at": user_data["created_at"]
                    },
                    "token": token
                }
            else:
                return {"success": False, "error": "Failed to create user"}
                
        except Exception as e:
            log_error(f"Error registering user: {str(e)}")
            return {"success": False, "error": "Registration failed"}
    
    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Login a user with email and password."""
        try:
            # Hash the provided password
            password_hash = self._hash_password(password)
            
            # Find user by email and password hash
            result = self.client.table("users").select("*").eq("email", email).eq("password_hash", password_hash).execute()
            
            if not result.data:
                return {"success": False, "error": "Invalid credentials"}
            
            user = result.data[0]
            
            if not user.get("is_active", False):
                return {"success": False, "error": "Account is disabled"}
            
            # Generate token
            token = self._generate_token(user["id"], email)
            
            # Update last login
            self.client.table("users").update({"updated_at": datetime.utcnow().isoformat()}).eq("id", user["id"]).execute()
            
            log_info(f"User logged in successfully: {email}")
            return {
                "success": True,
                "user": {
                    "id": user["id"],
                    "email": user["email"],
                    "created_at": user["created_at"]
                },
                "token": token
            }
            
        except Exception as e:
            log_error(f"Error logging in user: {str(e)}")
            return {"success": False, "error": "Login failed"}
    
    def verify_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a session token and return user info."""
        try:
            payload = self._verify_token(token)
            if not payload:
                return None
            
            # Get user from database
            result = self.client.table("users").select("*").eq("id", payload["user_id"]).execute()
            
            if not result.data:
                return None
            
            user = result.data[0]
            
            if not user.get("is_active", False):
                return None
            
            return {
                "user_id": user["id"],
                "email": user["email"],
                "created_at": user["created_at"]
            }
            
        except Exception as e:
            log_error(f"Error verifying session: {str(e)}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            result = self.client.table("users").select("id, email, created_at, updated_at, is_active").eq("id", user_id).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            log_error(f"Error getting user by ID: {str(e)}")
            return None
    
    def update_user_data_ownership(self, user_id: str) -> Dict[str, Any]:
        """Update existing data to be owned by the specified user."""
        try:
            # Update document_embeddings table - only update records where user_id is NULL
            embeddings_result = self.client.table("document_embeddings").update({"user_id": user_id}).is_("user_id", "null").execute()
            
            log_info(f"Updated {len(embeddings_result.data) if embeddings_result.data else 0} document embeddings for user {user_id}")
            
            return {
                "success": True,
                "updated_embeddings": len(embeddings_result.data) if embeddings_result.data else 0
            }
            
        except Exception as e:
            log_error(f"Error updating user data ownership: {str(e)}")
            return {"success": False, "error": "Failed to update data ownership"}
    
    def create_default_user(self, email: str, password: str) -> Dict[str, Any]:
        """Create the default user and migrate existing data."""
        try:
            # Register user
            result = self.register_user(email, password)
            
            if result["success"]:
                user_id = result["user"]["id"]
                
                # Update ownership of existing data
                ownership_result = self.update_user_data_ownership(user_id)
                
                log_info(f"Created default user and migrated data: {email}")
                return {
                    "success": True,
                    "user": result["user"],
                    "token": result["token"],
                    "migration": ownership_result
                }
            else:
                return result
                
        except Exception as e:
            log_error(f"Error creating default user: {str(e)}")
            return {"success": False, "error": "Failed to create default user"}


# SQL schema for user authentication
USER_AUTH_SCHEMA = """
-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    is_active BOOLEAN DEFAULT true
);

-- Create index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Add user_id column to document_embeddings table
ALTER TABLE document_embeddings 
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);

-- Create index on user_id for faster filtering
CREATE INDEX IF NOT EXISTS idx_document_embeddings_user_id ON document_embeddings(user_id);

-- Update the match_documents function to include user filtering
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