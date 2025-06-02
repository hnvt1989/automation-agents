"""Tests for the planner agent's update task functionality."""

import pytest
from datetime import datetime, timedelta
import yaml
from src.agents.planner import update_task, _find_task_by_identifier


class TestFindTaskByIdentifier:
    """Test the task finder functionality."""
    
    def test_find_by_exact_id(self):
        """Test finding task by exact ID match."""
        tasks = [
            {"id": "TASK-1", "title": "First task"},
            {"id": "TASK-2", "title": "Second task"},
            {"id": "ONBOARDING-1", "title": "Onboarding task"}
        ]
        
        result = _find_task_by_identifier(tasks, "TASK-2")
        assert result is not None
        assert result["id"] == "TASK-2"
        assert result["title"] == "Second task"
    
    def test_find_by_exact_title(self):
        """Test finding task by exact title match."""
        tasks = [
            {"id": "TASK-1", "title": "First task"},
            {"id": "TASK-2", "title": "job search"},
            {"id": "TASK-3", "title": "Another task"}
        ]
        
        result = _find_task_by_identifier(tasks, "job search")
        assert result is not None
        assert result["id"] == "TASK-2"
    
    def test_find_by_partial_title(self):
        """Test finding task by partial title match."""
        tasks = [
            {"id": "TASK-1", "title": "Prepare presentation for meeting"},
            {"id": "TASK-2", "title": "Review code"},
            {"id": "TASK-3", "title": "Write documentation"}
        ]
        
        result = _find_task_by_identifier(tasks, "presentation")
        assert result is not None
        assert result["id"] == "TASK-1"
    
    def test_find_by_fuzzy_match(self):
        """Test finding task by fuzzy title match."""
        tasks = [
            {"id": "TASK-1", "title": "job search"},
            {"id": "TASK-2", "title": "research project"},
            {"id": "TASK-3", "title": "meeting notes"}
        ]
        
        result = _find_task_by_identifier(tasks, "job serch")  # Typo
        assert result is not None
        assert result["id"] == "TASK-1"
    
    def test_no_match_found(self):
        """Test when no task matches."""
        tasks = [
            {"id": "TASK-1", "title": "First task"},
            {"id": "TASK-2", "title": "Second task"}
        ]
        
        result = _find_task_by_identifier(tasks, "nonexistent")
        assert result is None


class TestUpdateTask:
    """Test the update_task functionality."""
    
    def test_update_status_by_id(self, tmp_path):
        """Test updating task status using task ID."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_data = [
            {
                "id": "TASK-1",
                "title": "job search",
                "priority": "high",
                "status": "pending",
                "tags": ["personal"],
                "due_date": "2025-06-09"
            }
        ]
        with open(tasks_file, 'w') as f:
            yaml.dump(tasks_data, f)
        
        paths = {"tasks": str(tasks_file)}
        result = update_task("change status of TASK-1 to in progress", paths)
        
        assert result["success"] is True
        assert "status: pending → in_progress" in result["message"]
        
        # Verify the file was updated
        with open(tasks_file) as f:
            tasks = yaml.safe_load(f)
        assert tasks[0]["status"] == "in_progress"
    
    def test_update_status_by_title(self, tmp_path):
        """Test updating task status using task title."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_data = [
            {
                "id": "TASK-1",
                "title": "job search",
                "priority": "high",
                "status": "pending",
                "tags": ["personal"]
            }
        ]
        with open(tasks_file, 'w') as f:
            yaml.dump(tasks_data, f)
        
        paths = {"tasks": str(tasks_file)}
        result = update_task("change status of job search task to in progress", paths)
        
        assert result["success"] is True
        assert "in_progress" in result["message"]
        
        with open(tasks_file) as f:
            tasks = yaml.safe_load(f)
        assert tasks[0]["status"] == "in_progress"
    
    def test_update_priority(self, tmp_path):
        """Test updating task priority."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_data = [
            {
                "id": "TASK-1",
                "title": "Code review",
                "priority": "medium",
                "status": "pending"
            }
        ]
        with open(tasks_file, 'w') as f:
            yaml.dump(tasks_data, f)
        
        paths = {"tasks": str(tasks_file)}
        result = update_task("update TASK-1 priority to high", paths)
        
        assert result["success"] is True
        assert "priority: medium → high" in result["message"]
        
        with open(tasks_file) as f:
            tasks = yaml.safe_load(f)
        assert tasks[0]["priority"] == "high"
    
    def test_update_due_date(self, tmp_path):
        """Test updating task due date."""
        tasks_file = tmp_path / "tasks.yaml"
        original_date = "2025-06-09"
        tasks_data = [
            {
                "id": "TASK-1",
                "title": "Submit report",
                "priority": "high",
                "status": "pending",
                "due_date": original_date
            }
        ]
        with open(tasks_file, 'w') as f:
            yaml.dump(tasks_data, f)
        
        paths = {"tasks": str(tasks_file)}
        result = update_task("change TASK-1 due date to tomorrow", paths)
        
        assert result["success"] is True
        tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
        assert f"due_date: {original_date} → {tomorrow}" in result["message"]
        
        with open(tasks_file) as f:
            tasks = yaml.safe_load(f)
        assert tasks[0]["due_date"] == tomorrow
    
    def test_update_hours_estimate(self, tmp_path):
        """Test updating task hours estimate."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_data = [
            {
                "id": "TASK-1",
                "title": "Feature implementation",
                "priority": "high",
                "status": "pending"
            }
        ]
        with open(tasks_file, 'w') as f:
            yaml.dump(tasks_data, f)
        
        paths = {"tasks": str(tasks_file)}
        result = update_task("update TASK-1 estimate to 8 hours", paths)
        
        assert result["success"] is True
        assert "estimate_hours: not set → 8.0" in result["message"]
        
        with open(tasks_file) as f:
            tasks = yaml.safe_load(f)
        assert tasks[0]["estimate_hours"] == 8.0
    
    def test_add_tags(self, tmp_path):
        """Test adding tags to existing tags."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_data = [
            {
                "id": "TASK-1",
                "title": "Research task",
                "priority": "medium",
                "status": "pending",
                "tags": ["research"]
            }
        ]
        with open(tasks_file, 'w') as f:
            yaml.dump(tasks_data, f)
        
        paths = {"tasks": str(tasks_file)}
        result = update_task("add tags urgent, important to TASK-1", paths)
        
        assert result["success"] is True
        
        with open(tasks_file) as f:
            tasks = yaml.safe_load(f)
        assert "research" in tasks[0]["tags"]
        assert "urgent" in tasks[0]["tags"]
        assert "important" in tasks[0]["tags"]
    
    def test_replace_tags(self, tmp_path):
        """Test replacing all tags."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_data = [
            {
                "id": "TASK-1",
                "title": "Old task",
                "priority": "low",
                "status": "pending",
                "tags": ["old", "outdated"]
            }
        ]
        with open(tasks_file, 'w') as f:
            yaml.dump(tasks_data, f)
        
        paths = {"tasks": str(tasks_file)}
        result = update_task("update TASK-1 tags to new, fresh", paths)
        
        assert result["success"] is True
        
        with open(tasks_file) as f:
            tasks = yaml.safe_load(f)
        assert "old" not in tasks[0]["tags"]
        assert "new" in tasks[0]["tags"]
        assert "fresh" in tasks[0]["tags"]
    
    def test_rename_task(self, tmp_path):
        """Test renaming a task."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_data = [
            {
                "id": "TASK-1",
                "title": "Old title",
                "priority": "medium",
                "status": "pending"
            }
        ]
        with open(tasks_file, 'w') as f:
            yaml.dump(tasks_data, f)
        
        paths = {"tasks": str(tasks_file)}
        result = update_task("rename TASK-1 to New improved title", paths)
        
        assert result["success"] is True
        assert "title: Old title → New improved title" in result["message"]
        
        with open(tasks_file) as f:
            tasks = yaml.safe_load(f)
        assert tasks[0]["title"] == "New improved title"
    
    def test_multiple_updates(self, tmp_path):
        """Test multiple updates in one query."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_data = [
            {
                "id": "TASK-1",
                "title": "Complex task",
                "priority": "low",
                "status": "pending",
                "tags": []
            }
        ]
        with open(tasks_file, 'w') as f:
            yaml.dump(tasks_data, f)
        
        paths = {"tasks": str(tasks_file)}
        result = update_task("update TASK-1 status to in_progress, priority to high", paths)
        
        assert result["success"] is True
        assert "status: pending → in_progress" in result["message"]
        assert "priority: low → high" in result["message"]
        
        with open(tasks_file) as f:
            tasks = yaml.safe_load(f)
        assert tasks[0]["status"] == "in_progress"
        assert tasks[0]["priority"] == "high"
    
    def test_mark_task_completed(self, tmp_path):
        """Test marking task as completed."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_data = [
            {
                "id": "TASK-1",
                "title": "Finish project",
                "priority": "high",
                "status": "in_progress"
            }
        ]
        with open(tasks_file, 'w') as f:
            yaml.dump(tasks_data, f)
        
        paths = {"tasks": str(tasks_file)}
        result = update_task("mark TASK-1 as completed", paths)
        
        assert result["success"] is True
        assert "status: in_progress → completed" in result["message"]
        
        with open(tasks_file) as f:
            tasks = yaml.safe_load(f)
        assert tasks[0]["status"] == "completed"
    
    def test_update_nonexistent_task(self, tmp_path):
        """Test updating a task that doesn't exist."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_data = [
            {"id": "TASK-1", "title": "Only task"}
        ]
        with open(tasks_file, 'w') as f:
            yaml.dump(tasks_data, f)
        
        paths = {"tasks": str(tasks_file)}
        result = update_task("update TASK-99 status to completed", paths)
        
        assert "error" in result
        assert "not found" in result["error"]
    
    def test_no_valid_updates(self, tmp_path):
        """Test when no valid updates are found in query."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_data = [
            {"id": "TASK-1", "title": "Some task"}
        ]
        with open(tasks_file, 'w') as f:
            yaml.dump(tasks_data, f)
        
        paths = {"tasks": str(tasks_file)}
        result = update_task("TASK-1 needs attention", paths)
        
        assert "error" in result
        assert "No valid updates found" in result["error"]