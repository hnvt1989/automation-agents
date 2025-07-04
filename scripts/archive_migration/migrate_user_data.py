#!/usr/bin/env python3
"""Migrate existing file-based data to be owned by the default user."""

import os
import sys
import yaml
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from dotenv import load_dotenv
from src.storage.auth_storage import AuthStorage

def migrate_file_data_to_user():
    """Add user_id to all existing file-based data."""
    
    # Load environment variables
    env_file = project_root / "local.env"
    load_dotenv(env_file)
    
    # Get the default user
    auth_storage = AuthStorage()
    
    # Find the default user by email
    try:
        result = auth_storage.client.table("users").select("*").eq("email", "huynguyenvt1989@gmail.com").execute()
        
        if not result.data:
            print("❌ Default user not found! Please run setup_auth.py first.")
            return False
            
        user = result.data[0]
        user_id = user["id"]
        print(f"✅ Found default user: {user['email']} (ID: {user_id})")
        
    except Exception as e:
        print(f"❌ Error finding user: {e}")
        return False
    
    # Migrate tasks.yaml
    tasks_file = project_root / "data" / "tasks.yaml"
    if tasks_file.exists():
        try:
            with open(tasks_file, 'r') as f:
                tasks = yaml.safe_load(f) or []
            
            updated_tasks = 0
            for task in tasks:
                if 'user_id' not in task:
                    task['user_id'] = user_id
                    updated_tasks += 1
            
            with open(tasks_file, 'w') as f:
                yaml.dump(tasks, f, default_flow_style=False, allow_unicode=True)
            
            print(f"✅ Updated {updated_tasks} tasks with user_id")
            
        except Exception as e:
            print(f"❌ Error migrating tasks: {e}")
    
    # Migrate daily_logs.yaml
    logs_file = project_root / "data" / "daily_logs.yaml"
    if logs_file.exists():
        try:
            with open(logs_file, 'r') as f:
                logs_data = yaml.safe_load(f) or {}
            
            updated_logs = 0
            for date, daily_logs in logs_data.items():
                if daily_logs:
                    for log in daily_logs:
                        if 'user_id' not in log:
                            log['user_id'] = user_id
                            updated_logs += 1
            
            with open(logs_file, 'w') as f:
                yaml.dump(logs_data, f, default_flow_style=False, allow_unicode=True)
            
            print(f"✅ Updated {updated_logs} log entries with user_id")
            
        except Exception as e:
            print(f"❌ Error migrating logs: {e}")
    
    # Migrate meetings.yaml
    meetings_file = project_root / "data" / "meetings.yaml"
    if meetings_file.exists():
        try:
            with open(meetings_file, 'r') as f:
                meetings = yaml.safe_load(f) or []
            
            updated_meetings = 0
            for meeting in meetings:
                if 'user_id' not in meeting:
                    meeting['user_id'] = user_id
                    updated_meetings += 1
            
            with open(meetings_file, 'w') as f:
                yaml.dump(meetings, f, default_flow_style=False, allow_unicode=True)
            
            print(f"✅ Updated {updated_meetings} meetings with user_id")
            
        except Exception as e:
            print(f"❌ Error migrating meetings: {e}")
    
    # Add user ownership metadata to all markdown files
    data_dirs = [
        project_root / "data" / "va_notes",
        project_root / "data" / "meeting_notes", 
        project_root / "data" / "memos",
        project_root / "data" / "interviews"
    ]
    
    total_files = 0
    for data_dir in data_dirs:
        if data_dir.exists():
            for file_path in data_dir.rglob("*.md"):
                try:
                    # Add a comment at the top of markdown files indicating ownership
                    content = file_path.read_text()
                    if not content.startswith(f"<!-- user_id: {user_id} -->"):
                        new_content = f"<!-- user_id: {user_id} -->\n{content}"
                        file_path.write_text(new_content)
                        total_files += 1
                except Exception as e:
                    print(f"⚠️  Warning: Could not update {file_path}: {e}")
    
    print(f"✅ Added user ownership to {total_files} markdown files")
    
    return True

def main():
    """Main migration function."""
    print("🔄 User Data Migration Script")
    print("=" * 40)
    
    if migrate_file_data_to_user():
        print("\n🎉 Migration completed successfully!")
        print("All existing data is now mapped to the default user.")
        print("Restart the application to see the changes.")
    else:
        print("\n❌ Migration failed!")

if __name__ == "__main__":
    main()