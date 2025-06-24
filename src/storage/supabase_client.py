"""Supabase client for database operations."""

import os
from typing import Optional
from supabase import create_client, Client
from src.utils.logging import log_info, log_error


class SupabaseClient:
    """Singleton Supabase client."""
    
    _instance: Optional['SupabaseClient'] = None
    _client: Optional[Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Supabase client."""
        if not self._client:
            try:
                url = os.getenv("SUPABASE_URL")
                key = os.getenv("SUPABASE_KEY")
                
                if not url or not key:
                    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
                
                self._client = create_client(url, key)
                log_info("Supabase client initialized successfully")
            except Exception as e:
                log_error(f"Failed to initialize Supabase client: {str(e)}")
                raise
    
    @property
    def client(self) -> Client:
        """Get the Supabase client instance."""
        if not self._client:
            raise RuntimeError("Supabase client not initialized")
        return self._client
    
    def get_tasks_table(self):
        """Get the tasks table reference."""
        return self.client.table("tasks")
    
    def get_logs_table(self):
        """Get the daily_logs table reference."""
        return self.client.table("daily_logs")


def get_supabase_client() -> SupabaseClient:
    """Get or create the Supabase client instance."""
    return SupabaseClient()