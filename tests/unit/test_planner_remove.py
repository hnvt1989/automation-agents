"""Tests for the planner agent's removal functions."""

import pytest
from datetime import datetime, timedelta
import yaml
from src.agents.planner import remove_task, remove_meeting, remove_daily_log


class TestRemoveTask:
    """Test the remove_task functionality."""
    
    def test_remove_existing_task(self, tmp_path):
        """Test removing an existing task."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_data = [
            {"id": "TASK-1", "title": "First task", "priority": "high", "status": "pending"},
            {"id": "TASK-2", "title": "Second task", "priority": "medium", "status": "pending"},
            {"id": "TASK-3", "title": "Third task", "priority": "low", "status": "pending"}
        ]
        with open(tasks_file, 'w') as f:
            yaml.dump(tasks_data, f)
        
        paths = {"tasks": str(tasks_file)}
        result = remove_task("TASK-2", paths)
        
        assert result["success"] is True
        assert "TASK-2" in result["message"]
        
        # Verify the task was removed
        with open(tasks_file) as f:
            tasks = yaml.safe_load(f)
        assert len(tasks) == 2
        assert all(task["id"] != "TASK-2" for task in tasks)
        assert any(task["id"] == "TASK-1" for task in tasks)
        assert any(task["id"] == "TASK-3" for task in tasks)
    
    def test_remove_nonexistent_task(self, tmp_path):
        """Test removing a task that doesn't exist."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_data = [
            {"id": "TASK-1", "title": "First task", "priority": "high", "status": "pending"}
        ]
        with open(tasks_file, 'w') as f:
            yaml.dump(tasks_data, f)
        
        paths = {"tasks": str(tasks_file)}
        result = remove_task("TASK-99", paths)
        
        assert "error" in result
        assert "not found" in result["error"]
        
        # Verify no tasks were removed
        with open(tasks_file) as f:
            tasks = yaml.safe_load(f)
        assert len(tasks) == 1
    
    def test_remove_from_empty_file(self, tmp_path):
        """Test removing from an empty tasks file."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_file.write_text("[]")
        
        paths = {"tasks": str(tasks_file)}
        result = remove_task("TASK-1", paths)
        
        assert "error" in result
        assert "not found" in result["error"]


class TestRemoveMeeting:
    """Test the remove_meeting functionality."""
    
    def test_remove_meeting_by_date_and_time(self, tmp_path):
        """Test removing a meeting by date and time."""
        meetings_file = tmp_path / "meetings.yaml"
        tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
        meetings_data = [
            {"date": tomorrow, "time": "10:00", "event": "Team standup"},
            {"date": tomorrow, "time": "14:00", "event": "Client call"},
            {"date": tomorrow, "time": "16:00", "event": "Review meeting"}
        ]
        with open(meetings_file, 'w') as f:
            yaml.dump(meetings_data, f)
        
        paths = {"meets": str(meetings_file)}
        result = remove_meeting("tomorrow at 2pm", paths)
        
        assert result["success"] is True
        assert "Client call" in result["message"]
        
        # Verify the meeting was removed
        with open(meetings_file) as f:
            meetings = yaml.safe_load(f)
        assert len(meetings) == 2
        assert all(meeting["time"] != "14:00" for meeting in meetings)
    
    def test_remove_meeting_by_date_only(self, tmp_path):
        """Test removing a meeting by date only (single meeting)."""
        meetings_file = tmp_path / "meetings.yaml"
        tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
        meetings_data = [
            {"date": tomorrow, "time": "10:00", "event": "Team standup"}
        ]
        with open(meetings_file, 'w') as f:
            yaml.dump(meetings_data, f)
        
        paths = {"meets": str(meetings_file)}
        result = remove_meeting("tomorrow standup", paths)
        
        assert result["success"] is True
        assert "Team standup" in result["message"]
        
        # Verify the meeting was removed
        with open(meetings_file) as f:
            meetings = yaml.safe_load(f)
        assert len(meetings) == 0
    
    def test_remove_meeting_multiple_matches(self, tmp_path):
        """Test error when multiple meetings match."""
        meetings_file = tmp_path / "meetings.yaml"
        tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
        meetings_data = [
            {"date": tomorrow, "time": "10:00", "event": "Team standup"},
            {"date": tomorrow, "time": "14:00", "event": "Another standup"}
        ]
        with open(meetings_file, 'w') as f:
            yaml.dump(meetings_data, f)
        
        paths = {"meets": str(meetings_file)}
        result = remove_meeting("tomorrow", paths)
        
        assert "error" in result
        assert "Multiple meetings found" in result["error"]
        assert "10:00" in result["error"]
        assert "14:00" in result["error"]
    
    def test_remove_meeting_no_match(self, tmp_path):
        """Test error when no meetings match."""
        meetings_file = tmp_path / "meetings.yaml"
        tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
        meetings_data = [
            {"date": tomorrow, "time": "10:00", "event": "Team standup"}
        ]
        with open(meetings_file, 'w') as f:
            yaml.dump(meetings_data, f)
        
        paths = {"meets": str(meetings_file)}
        result = remove_meeting("next week", paths)
        
        assert "error" in result
        assert "No meetings found matching" in result["error"]
    
    def test_remove_from_empty_meetings(self, tmp_path):
        """Test removing from empty meetings file."""
        meetings_file = tmp_path / "meetings.yaml"
        meetings_file.write_text("[]")
        
        paths = {"meets": str(meetings_file)}
        result = remove_meeting("tomorrow", paths)
        
        assert "error" in result
        assert "No meetings found" in result["error"]


class TestRemoveDailyLog:
    """Test the remove_daily_log functionality."""
    
    def test_remove_specific_task_log(self, tmp_path):
        """Test removing a specific task log entry."""
        logs_file = tmp_path / "daily_logs.yaml"
        today = datetime.now().date().isoformat()
        logs_data = {
            today: [
                {"task_id": "TASK-1", "description": "First work", "actual_hours": 2},
                {"task_id": "TASK-2", "description": "Second work", "actual_hours": 3},
                {"task_id": "TASK-3", "description": "Third work", "actual_hours": 1}
            ]
        }
        with open(logs_file, 'w') as f:
            yaml.dump(logs_data, f)
        
        paths = {"logs": str(logs_file)}
        result = remove_daily_log("today", "TASK-2", paths)
        
        assert result["success"] is True
        assert "TASK-2" in result["message"]
        
        # Verify the log was removed
        with open(logs_file) as f:
            logs = yaml.safe_load(f)
        # Convert date keys to strings for consistency
        logs = {str(k): v for k, v in logs.items()}
        assert len(logs[today]) == 2
        assert all(log["task_id"] != "TASK-2" for log in logs[today])
    
    def test_remove_all_logs_for_date(self, tmp_path):
        """Test removing all logs for a specific date."""
        logs_file = tmp_path / "daily_logs.yaml"
        today = datetime.now().date().isoformat()
        yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
        logs_data = {
            yesterday: [
                {"task_id": "TASK-1", "description": "Yesterday work", "actual_hours": 4}
            ],
            today: [
                {"task_id": "TASK-2", "description": "Today work", "actual_hours": 3}
            ]
        }
        with open(logs_file, 'w') as f:
            yaml.dump(logs_data, f)
        
        paths = {"logs": str(logs_file)}
        result = remove_daily_log("yesterday", paths=paths)
        
        assert result["success"] is True
        assert "all logs" in result["message"]
        assert yesterday in result["message"]
        
        # Verify the date was removed
        with open(logs_file) as f:
            logs = yaml.safe_load(f)
        # Convert date keys to strings for consistency
        logs = {str(k): v for k, v in logs.items()}
        assert yesterday not in logs
        assert today in logs
    
    def test_remove_log_no_logs_for_date(self, tmp_path):
        """Test removing logs for a date with no entries."""
        logs_file = tmp_path / "daily_logs.yaml"
        today = datetime.now().date().isoformat()
        logs_data = {
            today: [
                {"task_id": "TASK-1", "description": "Today work", "actual_hours": 3}
            ]
        }
        with open(logs_file, 'w') as f:
            yaml.dump(logs_data, f)
        
        paths = {"logs": str(logs_file)}
        result = remove_daily_log("yesterday", paths=paths)
        
        assert "error" in result
        assert "No logs found for date" in result["error"]
    
    def test_remove_nonexistent_task_log(self, tmp_path):
        """Test removing a task log that doesn't exist."""
        logs_file = tmp_path / "daily_logs.yaml"
        today = datetime.now().date().isoformat()
        logs_data = {
            today: [
                {"task_id": "TASK-1", "description": "First work", "actual_hours": 2}
            ]
        }
        with open(logs_file, 'w') as f:
            yaml.dump(logs_data, f)
        
        paths = {"logs": str(logs_file)}
        result = remove_daily_log("today", "TASK-99", paths)
        
        assert "error" in result
        assert "No log found for task" in result["error"]
        assert "TASK-99" in result["error"]
    
    def test_remove_last_log_removes_date(self, tmp_path):
        """Test that removing the last log for a date removes the date entry."""
        logs_file = tmp_path / "daily_logs.yaml"
        today = datetime.now().date().isoformat()
        logs_data = {
            today: [
                {"task_id": "TASK-1", "description": "Only work", "actual_hours": 2}
            ]
        }
        with open(logs_file, 'w') as f:
            yaml.dump(logs_data, f)
        
        paths = {"logs": str(logs_file)}
        result = remove_daily_log("today", "TASK-1", paths)
        
        assert result["success"] is True
        
        # Verify the date entry was removed
        with open(logs_file) as f:
            logs = yaml.safe_load(f)
        # Convert date keys to strings for consistency
        logs = {str(k): v for k, v in logs.items()} if logs else {}
        assert today not in logs