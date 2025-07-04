"""User settings storage using Supabase."""

import os
from typing import Dict, Any, Optional
from supabase import create_client, Client
from src.utils.logging import get_logger

logger = get_logger(__name__)


class UserSettingsStorage:
    """Manages user settings in Supabase."""
    
    def __init__(self):
        """Initialize Supabase client for user settings."""
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")
        
        self.client: Client = create_client(url, key)
        self.table_name = "user_settings"
        
        # Ensure table exists
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Ensure the user_settings table exists."""
        try:
            # Try to query the table to see if it exists
            result = self.client.table(self.table_name).select("id").limit(1).execute()
            logger.info("User settings table exists")
        except Exception as e:
            logger.error(f"User settings table might not exist: {e}")
            # Note: Table creation should be done via Supabase dashboard or migration scripts
    
    def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        """Get all settings for a user."""
        try:
            result = self.client.table(self.table_name).select("*").eq("user_id", user_id).execute()
            
            if result.data:
                # Convert list of settings to a dictionary
                settings = {}
                for setting in result.data:
                    settings[setting["setting_key"]] = setting["setting_value"]
                return settings
            else:
                return {}
        except Exception as e:
            logger.error(f"Error getting user settings for user {user_id}: {e}")
            return {}
    
    def get_user_setting(self, user_id: str, setting_key: str) -> Optional[str]:
        """Get a specific setting for a user."""
        try:
            result = self.client.table(self.table_name).select("setting_value").eq("user_id", user_id).eq("setting_key", setting_key).execute()
            
            if result.data:
                return result.data[0]["setting_value"]
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting setting {setting_key} for user {user_id}: {e}")
            return None
    
    def set_user_setting(self, user_id: str, setting_key: str, setting_value: str) -> bool:
        """Set a specific setting for a user."""
        try:
            # Check if setting already exists
            existing = self.client.table(self.table_name).select("id").eq("user_id", user_id).eq("setting_key", setting_key).execute()
            
            if existing.data:
                # Update existing setting
                result = self.client.table(self.table_name).update({
                    "setting_value": setting_value,
                    "updated_at": "now()"
                }).eq("user_id", user_id).eq("setting_key", setting_key).execute()
            else:
                # Create new setting
                result = self.client.table(self.table_name).insert({
                    "user_id": user_id,
                    "setting_key": setting_key,
                    "setting_value": setting_value
                }).execute()
            
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error setting {setting_key} for user {user_id}: {e}")
            return False
    
    def update_user_settings(self, user_id: str, settings: Dict[str, str]) -> bool:
        """Update multiple settings for a user."""
        try:
            success_count = 0
            for setting_key, setting_value in settings.items():
                if self.set_user_setting(user_id, setting_key, setting_value):
                    success_count += 1
            
            return success_count == len(settings)
        except Exception as e:
            logger.error(f"Error updating settings for user {user_id}: {e}")
            return False
    
    def delete_user_setting(self, user_id: str, setting_key: str) -> bool:
        """Delete a specific setting for a user."""
        try:
            result = self.client.table(self.table_name).delete().eq("user_id", user_id).eq("setting_key", setting_key).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error deleting setting {setting_key} for user {user_id}: {e}")
            return False
    
    def delete_all_user_settings(self, user_id: str) -> bool:
        """Delete all settings for a user."""
        try:
            result = self.client.table(self.table_name).delete().eq("user_id", user_id).execute()
            return True  # Success even if no rows were deleted
        except Exception as e:
            logger.error(f"Error deleting all settings for user {user_id}: {e}")
            return False