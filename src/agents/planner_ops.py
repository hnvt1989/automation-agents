"""Simplified planner operations focused on CRUD."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import yaml
import os

from src.utils.logging import log_info, log_error


def load_yaml(path: str) -> Any:
    """Load data from a YAML file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"YAML file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def save_yaml(path: str, data: Any) -> None:
    """Save data to a YAML file."""
    # Convert datetime.date keys to strings for consistency
    if isinstance(data, dict):
        data = {str(k): v for k, v in data.items()}
    
    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False, allow_unicode=True, sort_keys=False)


def generate_task_id(tasks: List[Dict[str, Any]]) -> str:
    """Generate a unique task ID."""
    existing_ids = [task.get("id", "") for task in tasks]
    counter = 1
    while f"TASK-{counter}" in existing_ids:
        counter += 1
    return f"TASK-{counter}"


def find_task(tasks: List[Dict[str, Any]], identifier: str) -> Optional[Dict[str, Any]]:
    """Find a task by ID or title."""
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
        # Check if all words from identifier are found in the title (allowing for typos)
        words_found = 0
        for word in identifier_words:
            # Direct match
            if word in title_lower:
                words_found += 1
            # Fuzzy match (allow 1 character difference for words > 3 chars)
            elif len(word) > 3:
                for title_word in title_lower.split():
                    if len(title_word) > 3:
                        # Simple fuzzy matching: check if most characters match
                        matches = sum(1 for a, b in zip(word, title_word) if a == b)
                        if matches >= len(word) - 1 and abs(len(word) - len(title_word)) <= 1:
                            words_found += 1
                            break
        
        # If most words match, consider it a match
        if words_found >= len(identifier_words) * 0.8:  # 80% of words must match
            return task
    
    return None


class PlannerOperations:
    """Simple CRUD operations for planner data."""
    
    def __init__(self, paths: Optional[Dict[str, str]] = None):
        """Initialize with file paths."""
        self.paths = paths or {
            'tasks': 'data/tasks.yaml',
            'meetings': 'data/meetings.yaml',
            'logs': 'data/daily_logs.yaml'
        }
    
    def add_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new task."""
        try:
            tasks = load_yaml(self.paths['tasks']) or []
            if not isinstance(tasks, list):
                return {"success": False, "error": "Invalid tasks file structure"}
            
            # Use custom ID if provided, otherwise generate one
            custom_id = data.get("id") or data.get("identifier")
            if custom_id:
                # Check if the custom ID already exists
                existing_ids = [task.get("id", "") for task in tasks]
                if custom_id in existing_ids:
                    return {"success": False, "error": f"Task with ID '{custom_id}' already exists"}
                task_id = custom_id
            else:
                task_id = generate_task_id(tasks)
            
            # Create task with defaults
            task = {
                "id": task_id,
                "title": data.get("title", "New task"),
                "priority": data.get("priority", "medium"),
                "status": data.get("status", "pending"),
                "tags": data.get("tags", []),
                "due_date": data.get("due_date", (datetime.now().date() + timedelta(weeks=1)).isoformat())
            }
            
            # Add optional fields
            if "estimate_hours" in data:
                task["estimate_hours"] = data["estimate_hours"]
            
            tasks.append(task)
            save_yaml(self.paths['tasks'], tasks)
            
            return {"success": True, "task": task}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update_task(self, identifier: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing task."""
        try:
            tasks = load_yaml(self.paths['tasks']) or []
            task = find_task(tasks, identifier)
            
            if not task:
                return {"success": False, "error": f"Task '{identifier}' not found"}
            
            # Track what changed
            changes = []
            
            # Apply updates
            for field, value in updates.items():
                if field == "add_tags":
                    # Add tags to existing
                    existing_tags = task.get("tags", [])
                    task["tags"] = list(set(existing_tags + value))
                    changes.append(f"added tags: {', '.join(value)}")
                elif field == "remove_tags":
                    # Remove tags
                    existing_tags = task.get("tags", [])
                    task["tags"] = [t for t in existing_tags if t not in value]
                    changes.append(f"removed tags: {', '.join(value)}")
                else:
                    # Direct update
                    old_value = task.get(field, "not set")
                    task[field] = value
                    changes.append(f"{field}: {old_value} → {value}")
            
            save_yaml(self.paths['tasks'], tasks)
            
            return {
                "success": True,
                "task": task,
                "changes": changes,
                "message": f"Updated task '{task['title']}': {'; '.join(changes)}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def remove_task(self, identifier: str) -> Dict[str, Any]:
        """Remove a task."""
        try:
            tasks = load_yaml(self.paths['tasks']) or []
            task = find_task(tasks, identifier)
            
            if not task:
                return {"success": False, "error": f"Task '{identifier}' not found"}
            
            tasks = [t for t in tasks if t != task]
            save_yaml(self.paths['tasks'], tasks)
            
            return {"success": True, "message": f"Removed task '{task['title']}' ({task['id']})"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def add_meeting(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new meeting."""
        try:
            meetings = load_yaml(self.paths['meetings']) or []
            if not isinstance(meetings, list):
                return {"success": False, "error": "Invalid meetings file structure"}
            
            meeting = {
                "date": data.get("date", datetime.now().date().isoformat()),
                "time": data.get("time", "10:00"),
                "event": data.get("title", data.get("event", "Meeting"))
            }
            
            meetings.append(meeting)
            save_yaml(self.paths['meetings'], meetings)
            
            return {"success": True, "meeting": meeting}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def remove_meeting(self, date: str, time: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
        """Remove a meeting."""
        try:
            meetings = load_yaml(self.paths['meetings']) or []
            
            # Find matching meetings
            matches = []
            for meeting in meetings:
                if meeting.get("date") == date:
                    if time and meeting.get("time") != time:
                        continue
                    if title and title.lower() not in meeting.get("event", "").lower():
                        continue
                    matches.append(meeting)
            
            if not matches:
                return {"success": False, "error": "No matching meetings found"}
            
            if len(matches) > 1:
                return {"success": False, "error": f"Multiple meetings found. Please be more specific."}
            
            meetings.remove(matches[0])
            save_yaml(self.paths['meetings'], meetings)
            
            return {"success": True, "message": f"Removed meeting: {matches[0]['event']}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def add_log(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a work log entry."""
        try:
            logs = load_yaml(self.paths['logs']) or {}
            if not isinstance(logs, dict):
                return {"success": False, "error": "Invalid logs file structure"}
            
            # Convert date keys to strings
            logs = {str(k): v for k, v in logs.items()}
            
            # Get date
            log_date = data.get("date", datetime.now().date().isoformat())
            
            # Create log entry
            log_entry = {
                "log_id": data.get("log_id", data.get("task_id", "UNKNOWN")),
                "description": data.get("description", ""),
                "actual_hours": data.get("hours", 0)
            }
            
            # Add to logs
            if log_date not in logs:
                logs[log_date] = []
            logs[log_date].append(log_entry)
            
            save_yaml(self.paths['logs'], logs)
            
            return {"success": True, "log": log_entry, "date": log_date}
            
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

