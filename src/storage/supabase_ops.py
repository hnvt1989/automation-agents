"""Supabase operations for tasks and daily logs management."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
from src.utils.logging import log_info, log_error
from src.storage.supabase_client import get_supabase_client


def generate_task_id() -> str:
    """Generate a unique task ID."""
    # Use UUID for better uniqueness in distributed systems
    return f"TASK-{uuid.uuid4().hex[:8].upper()}"


def find_task_by_identifier(tasks: List[Dict[str, Any]], identifier: str) -> Optional[Dict[str, Any]]:
    """Find a task by ID or title from a list of tasks."""
    identifier_lower = identifier.lower().strip()
    
    # Try exact ID match
    for task in tasks:
        if task.get("id", "").lower() == identifier_lower:
            return task
    
    # Try exact title match
    for task in tasks:
        if task.get("title", "").lower() == identifier_lower:
            return task
    
    # Try partial title match
    for task in tasks:
        if identifier_lower in task.get("title", "").lower():
            return task
    
    # Try fuzzy matching for individual words
    identifier_words = identifier_lower.split()
    for task in tasks:
        title_lower = task.get("title", "").lower()
        words_found = 0
        for word in identifier_words:
            if word in title_lower:
                words_found += 1
            elif len(word) > 3:
                for title_word in title_lower.split():
                    if len(title_word) > 3:
                        matches = sum(1 for a, b in zip(word, title_word) if a == b)
                        if matches >= len(word) - 1 and abs(len(word) - len(title_word)) <= 1:
                            words_found += 1
                            break
        
        if words_found >= len(identifier_words) * 0.8:
            return task
    
    return None


class SupabaseOperations:
    """Database operations for planner data using Supabase."""
    
    def __init__(self):
        """Initialize with Supabase client."""
        self.client = get_supabase_client()
    
    def add_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new task."""
        try:
            # Check if a task with the same title already exists
            title = data.get("title", "New task")
            existing = self.client.get_tasks_table().select("*").eq("title", title).execute()
            
            if existing.data:
                log_info(f"Task with title '{title}' already exists, skipping creation")
                return {"success": False, "error": f"Task with title '{title}' already exists"}
            
            # Use custom ID if provided, otherwise generate one
            custom_id = data.get("id") or data.get("identifier")
            if custom_id:
                # Check if the custom ID already exists
                existing_id = self.client.get_tasks_table().select("*").eq("id", custom_id).execute()
                if existing_id.data:
                    return {"success": False, "error": f"Task with ID '{custom_id}' already exists"}
                task_id = custom_id
            else:
                task_id = generate_task_id()
            
            # Create task with defaults
            task = {
                "id": task_id,
                "title": title,
                "description": data.get("description"),
                "priority": data.get("priority", "medium"),
                "status": data.get("status", "pending"),
                "tags": data.get("tags", []),
                "due_date": data.get("due_date", (datetime.now().date() + timedelta(weeks=1)).isoformat()),
                "estimate_hours": data.get("estimate_hours"),
                "todo": data.get("todo")
            }
            
            # Insert into database
            result = self.client.get_tasks_table().insert(task).execute()
            
            if result.data:
                log_info(f"Successfully created task: {task_id} - {title}")
                return {"success": True, "task": result.data[0]}
            else:
                return {"success": False, "error": "Failed to insert task"}
            
        except Exception as e:
            log_error(f"Error adding task: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def update_task(self, identifier: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing task."""
        try:
            log_info(f"Updating task '{identifier}' with updates: {updates}")
            
            # First, find the task
            tasks = self.client.get_tasks_table().select("*").execute()
            task = find_task_by_identifier(tasks.data, identifier)
            
            if not task:
                log_error(f"Task '{identifier}' not found for update")
                return {"success": False, "error": f"Task '{identifier}' not found"}
            
            task_id = task["id"]
            changes = []
            
            # Process updates
            update_data = {}
            for field, value in updates.items():
                if field == "add_tags":
                    # Add tags to existing
                    existing_tags = task.get("tags", [])
                    update_data["tags"] = list(set(existing_tags + value))
                    changes.append(f"added tags: {', '.join(value)}")
                elif field == "remove_tags":
                    # Remove tags
                    existing_tags = task.get("tags", [])
                    update_data["tags"] = [t for t in existing_tags if t not in value]
                    changes.append(f"removed tags: {', '.join(value)}")
                else:
                    # Direct update
                    old_value = task.get(field, "not set")
                    update_data[field] = value
                    changes.append(f"{field}: {old_value} → {value}")
            
            # Update in database
            result = self.client.get_tasks_table().update(update_data).eq("id", task_id).execute()
            
            if result.data:
                updated_task = result.data[0]
                log_info(f"Successfully updated task '{task_id}' - {updated_task['title']}: {'; '.join(changes)}")
                
                return {
                    "success": True,
                    "task": updated_task,
                    "changes": changes,
                    "message": f"Updated task '{updated_task['title']}': {'; '.join(changes)}"
                }
            else:
                return {"success": False, "error": "Failed to update task"}
            
        except Exception as e:
            log_error(f"Error updating task: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def remove_task(self, identifier: str) -> Dict[str, Any]:
        """Remove a task."""
        try:
            # First, find the task
            tasks = self.client.get_tasks_table().select("*").execute()
            task = find_task_by_identifier(tasks.data, identifier)
            
            if not task:
                return {"success": False, "error": f"Task '{identifier}' not found"}
            
            # Delete from database
            result = self.client.get_tasks_table().delete().eq("id", task["id"]).execute()
            
            if result:
                return {"success": True, "message": f"Removed task '{task['title']}' ({task['id']})"}
            else:
                return {"success": False, "error": "Failed to delete task"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks from the database."""
        try:
            result = self.client.get_tasks_table().select("*").order("created_at", desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            log_error(f"Error fetching tasks: {str(e)}")
            return []
    
    def add_log(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a work log entry."""
        try:
            # Get date
            log_date = data.get("date", datetime.now().date().isoformat())
            
            # Create log entry
            log_entry = {
                "log_date": log_date,
                "log_id": data.get("log_id", data.get("task_id", f"LOG-{uuid.uuid4().hex[:8].upper()}")),
                "description": data.get("description", ""),
                "actual_hours": float(data.get("hours", data.get("actual_hours", 0))),
                "task_id": data.get("task_id")  # Optional foreign key
            }
            
            # Insert into database
            result = self.client.get_logs_table().insert(log_entry).execute()
            
            if result.data:
                return {"success": True, "log": result.data[0], "date": log_date}
            else:
                return {"success": False, "error": "Failed to insert log"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_all_logs(self) -> List[Dict[str, Any]]:
        """Get all logs from the database."""
        try:
            result = self.client.get_logs_table().select("*").order("log_date", desc=True).order("created_at", desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            log_error(f"Error fetching logs: {str(e)}")
            return []
    
    def get_logs_by_date(self, date: str) -> List[Dict[str, Any]]:
        """Get logs for a specific date."""
        try:
            result = self.client.get_logs_table().select("*").eq("log_date", date).execute()
            return result.data if result.data else []
        except Exception as e:
            log_error(f"Error fetching logs for date {date}: {str(e)}")
            return []
    
    def update_log(self, log_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a log entry."""
        try:
            # Update in database
            result = self.client.get_logs_table().update(updates).eq("id", log_id).execute()
            
            if result.data:
                return {"success": True, "log": result.data[0]}
            else:
                return {"success": False, "error": "Failed to update log"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def remove_log(self, log_id: int) -> Dict[str, Any]:
        """Remove a log entry."""
        try:
            # Get log details first
            log_result = self.client.get_logs_table().select("*").eq("id", log_id).execute()
            
            if not log_result.data:
                return {"success": False, "error": "Log not found"}
            
            log = log_result.data[0]
            
            # Delete from database
            result = self.client.get_logs_table().delete().eq("id", log_id).execute()
            
            if result:
                return {"success": True, "message": "Log deleted successfully", "deleted_log": log}
            else:
                return {"success": False, "error": "Failed to delete log"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_task_and_log(self, description: str, hours: float) -> Dict[str, Any]:
        """Create a task and immediately log work against it."""
        try:
            # First create the task
            task_result = self.add_task({"title": description})
            if not task_result["success"]:
                return task_result
            
            task_id = task_result["task"]["id"]
            
            # Then log work
            log_result = self.add_log({
                "task_id": task_id,
                "description": description,
                "hours": hours
            })
            
            if not log_result["success"]:
                return log_result
            
            return {
                "success": True,
                "message": f"Created task '{description}' ({task_id}) and logged {hours} hours",
                "task": task_result["task"],
                "log": log_result["log"]
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}