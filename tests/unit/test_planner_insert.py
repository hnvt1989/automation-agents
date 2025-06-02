"""Tests for the planner agent's natural language insertion functions."""

import pytest
from datetime import datetime, timedelta, date
import os
import tempfile
import yaml
from src.agents.planner import (
    insert_task, 
    insert_meeting, 
    insert_daily_log,
    _parse_natural_language_date,
    _parse_natural_language_time,
    _parse_priority,
    _generate_task_id
)


class TestNaturalLanguageDateParsing:
    """Test the natural language date parsing functionality."""
    
    def test_parse_today(self):
        """Test parsing 'today'."""
        result = _parse_natural_language_date("today")
        assert result == datetime.now().date()
    
    def test_parse_tomorrow(self):
        """Test parsing 'tomorrow'."""
        result = _parse_natural_language_date("tomorrow")
        assert result == datetime.now().date() + timedelta(days=1)
    
    def test_parse_yesterday(self):
        """Test parsing 'yesterday'."""
        result = _parse_natural_language_date("yesterday")
        assert result == datetime.now().date() - timedelta(days=1)
    
    def test_parse_iso_date(self):
        """Test parsing ISO date format."""
        result = _parse_natural_language_date("2024-12-25")
        assert result == date(2024, 12, 25)
    
    def test_parse_us_date(self):
        """Test parsing US date format."""
        result = _parse_natural_language_date("12/25/2024")
        assert result == date(2024, 12, 25)
    
    def test_parse_in_days(self):
        """Test parsing 'in X days' format."""
        result = _parse_natural_language_date("in 5 days")
        assert result == datetime.now().date() + timedelta(days=5)
    
    def test_parse_next_week(self):
        """Test parsing 'next week'."""
        result = _parse_natural_language_date("next week")
        assert result == datetime.now().date() + timedelta(weeks=1)
    
    def test_default_date(self):
        """Test default date when no pattern matches."""
        result = _parse_natural_language_date("some random text")
        # Should default to a week from now
        assert result == datetime.now().date() + timedelta(weeks=1)


class TestNaturalLanguageTimeParsing:
    """Test the natural language time parsing functionality."""
    
    def test_parse_24hr_time(self):
        """Test parsing 24-hour format."""
        assert _parse_natural_language_time("14:30") == "14:30"
        assert _parse_natural_language_time("09:00") == "09:00"
    
    def test_parse_12hr_time_with_ampm(self):
        """Test parsing 12-hour format with AM/PM."""
        assert _parse_natural_language_time("2:30 pm") == "14:30"
        assert _parse_natural_language_time("9:00 am") == "09:00"
        assert _parse_natural_language_time("12:00 pm") == "12:00"
        assert _parse_natural_language_time("12:00 am") == "00:00"
    
    def test_parse_12hr_time_without_minutes(self):
        """Test parsing 12-hour format without minutes."""
        assert _parse_natural_language_time("2 pm") == "14:00"
        assert _parse_natural_language_time("9 am") == "09:00"
    
    def test_parse_named_times(self):
        """Test parsing named time references."""
        assert _parse_natural_language_time("morning") == "09:00"
        assert _parse_natural_language_time("noon") == "12:00"
        assert _parse_natural_language_time("afternoon") == "14:00"
        assert _parse_natural_language_time("evening") == "18:00"
        assert _parse_natural_language_time("night") == "20:00"
    
    def test_no_time_found(self):
        """Test when no time pattern is found."""
        assert _parse_natural_language_time("no time here") is None


class TestPriorityParsing:
    """Test the priority parsing functionality."""
    
    def test_high_priority_keywords(self):
        """Test high priority keywords."""
        assert _parse_priority("urgent task") == "high"
        assert _parse_priority("critical bug fix") == "high"
        assert _parse_priority("important meeting") == "high"
        assert _parse_priority("high priority item") == "high"
        assert _parse_priority("fix this asap") == "high"
    
    def test_low_priority_keywords(self):
        """Test low priority keywords."""
        assert _parse_priority("low priority task") == "low"
        assert _parse_priority("do this whenever") == "low"
        assert _parse_priority("not urgent") == "low"
    
    def test_default_medium_priority(self):
        """Test default medium priority."""
        assert _parse_priority("regular task") == "medium"
        assert _parse_priority("some task") == "medium"


class TestTaskIdGeneration:
    """Test the task ID generation functionality."""
    
    def test_generate_first_id(self):
        """Test generating the first task ID."""
        tasks = []
        assert _generate_task_id(tasks) == "TASK-1"
    
    def test_generate_next_id(self):
        """Test generating the next task ID."""
        tasks = [
            {"id": "TASK-1"},
            {"id": "TASK-2"},
            {"id": "TASK-3"}
        ]
        assert _generate_task_id(tasks) == "TASK-4"
    
    def test_generate_with_custom_prefix(self):
        """Test generating task ID with custom prefix."""
        tasks = [{"id": "FEATURE-1"}]
        assert _generate_task_id(tasks, prefix="FEATURE") == "FEATURE-2"
    
    def test_generate_with_gaps(self):
        """Test generating task ID when there are gaps."""
        tasks = [
            {"id": "TASK-1"},
            {"id": "TASK-3"},
            {"id": "TASK-5"}
        ]
        assert _generate_task_id(tasks) == "TASK-2"


class TestInsertTask:
    """Test the insert_task functionality."""
    
    def test_insert_simple_task(self, tmp_path):
        """Test inserting a simple task."""
        # Create a temporary tasks file
        tasks_file = tmp_path / "tasks.yaml"
        tasks_file.write_text("[]")
        
        paths = {"tasks": str(tasks_file)}
        result = insert_task("finish the report", paths)
        
        assert result["success"] is True
        assert result["task"]["title"] == "finish the report"
        assert result["task"]["id"] == "TASK-1"
        assert result["task"]["priority"] == "medium"
        assert result["task"]["status"] == "pending"
        
        # Verify the file was updated
        with open(tasks_file) as f:
            tasks = yaml.safe_load(f)
        assert len(tasks) == 1
        assert tasks[0]["title"] == "finish the report"
    
    def test_insert_task_with_priority(self, tmp_path):
        """Test inserting a task with priority."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_file.write_text("[]")
        
        paths = {"tasks": str(tasks_file)}
        result = insert_task("urgent: fix the critical bug", paths)
        
        assert result["success"] is True
        assert result["task"]["priority"] == "high"
    
    def test_insert_task_with_hours(self, tmp_path):
        """Test inserting a task with estimated hours."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_file.write_text("[]")
        
        paths = {"tasks": str(tasks_file)}
        result = insert_task("implement feature will take 5 hours", paths)
        
        assert result["success"] is True
        assert result["task"]["estimate_hours"] == 5
    
    def test_insert_task_with_tags(self, tmp_path):
        """Test inserting a task with tags."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_file.write_text("[]")
        
        paths = {"tasks": str(tasks_file)}
        result = insert_task("update docs #documentation tag: frontend", paths)
        
        assert result["success"] is True
        assert "documentation" in result["task"]["tags"]
        assert "frontend" in result["task"]["tags"]
    
    def test_insert_task_with_date(self, tmp_path):
        """Test inserting a task with due date."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_file.write_text("[]")
        
        paths = {"tasks": str(tasks_file)}
        result = insert_task("submit report by tomorrow", paths)
        
        assert result["success"] is True
        expected_date = (datetime.now().date() + timedelta(days=1)).isoformat()
        assert result["task"]["due_date"] == expected_date


class TestInsertMeeting:
    """Test the insert_meeting functionality."""
    
    def test_insert_simple_meeting(self, tmp_path):
        """Test inserting a simple meeting."""
        meetings_file = tmp_path / "meetings.yaml"
        meetings_file.write_text("[]")
        
        paths = {"meets": str(meetings_file)}
        result = insert_meeting("team standup tomorrow at 10am", paths)
        
        assert result["success"] is True
        assert "team standup" in result["meeting"]["event"]
        assert result["meeting"]["time"] == "10:00"
        expected_date = (datetime.now().date() + timedelta(days=1)).isoformat()
        assert result["meeting"]["date"] == expected_date
        
        # Verify the file was updated
        with open(meetings_file) as f:
            meetings = yaml.safe_load(f)
        assert len(meetings) == 1
    
    def test_insert_meeting_no_time(self, tmp_path):
        """Test inserting a meeting without time (should default to 10:00)."""
        meetings_file = tmp_path / "meetings.yaml"
        meetings_file.write_text("[]")
        
        paths = {"meets": str(meetings_file)}
        result = insert_meeting("planning session next week", paths)
        
        assert result["success"] is True
        assert result["meeting"]["time"] == "10:00"  # Default time
        assert "planning session" in result["meeting"]["event"]
    
    def test_insert_meeting_with_afternoon(self, tmp_path):
        """Test inserting a meeting with named time."""
        meetings_file = tmp_path / "meetings.yaml"
        meetings_file.write_text("[]")
        
        paths = {"meets": str(meetings_file)}
        result = insert_meeting("client call this afternoon", paths)
        
        assert result["success"] is True
        assert result["meeting"]["time"] == "14:00"
        assert "client call" in result["meeting"]["event"]


class TestInsertDailyLog:
    """Test the insert_daily_log functionality."""
    
    def test_insert_simple_log(self, tmp_path):
        """Test inserting a simple daily log."""
        logs_file = tmp_path / "daily_logs.yaml"
        logs_file.write_text("{}")
        
        paths = {"logs": str(logs_file)}
        result = insert_daily_log("completed API implementation", "TASK-1", 3.5, paths)
        
        assert result["success"] is True
        assert result["log"]["task_id"] == "TASK-1"
        assert result["log"]["description"] == "completed API implementation"
        assert result["log"]["actual_hours"] == 3.5
        assert result["date"] == datetime.now().date().isoformat()
        
        # Verify the file was updated
        with open(logs_file) as f:
            logs = yaml.safe_load(f)
        assert datetime.now().date().isoformat() in logs
        assert len(logs[datetime.now().date().isoformat()]) == 1
    
    def test_insert_log_with_date(self, tmp_path):
        """Test inserting a log with specific date."""
        logs_file = tmp_path / "daily_logs.yaml"
        logs_file.write_text("{}")
        
        paths = {"logs": str(logs_file)}
        result = insert_daily_log("worked on feature yesterday", "TASK-2", 5, paths)
        
        assert result["success"] is True
        expected_date = (datetime.now().date() - timedelta(days=1)).isoformat()
        assert result["date"] == expected_date
    
    def test_append_to_existing_date(self, tmp_path):
        """Test appending log to existing date."""
        existing_date = datetime.now().date().isoformat()
        logs_file = tmp_path / "daily_logs.yaml"
        logs_file.write_text(f"""{existing_date}:
  - task_id: TASK-1
    description: First task
    actual_hours: 2
""")
        
        paths = {"logs": str(logs_file)}
        result = insert_daily_log("second task work", "TASK-2", 3, paths)
        
        assert result["success"] is True
        
        # Verify the file was updated
        with open(logs_file) as f:
            logs = yaml.safe_load(f)
        assert len(logs[existing_date]) == 2
        assert logs[existing_date][1]["task_id"] == "TASK-2"


class TestErrorHandling:
    """Test error handling in insertion functions."""
    
    def test_insert_task_file_not_found(self):
        """Test handling when tasks file doesn't exist."""
        paths = {"tasks": "/nonexistent/tasks.yaml"}
        result = insert_task("test task", paths)
        
        assert "error" in result
        assert "not found" in result["error"]
    
    def test_insert_task_invalid_yaml(self, tmp_path):
        """Test handling when YAML file is invalid."""
        tasks_file = tmp_path / "tasks.yaml"
        tasks_file.write_text("invalid: yaml: content:")  # Invalid YAML
        
        paths = {"tasks": str(tasks_file)}
        result = insert_task("test task", paths)
        
        assert "error" in result
    
    def test_insert_meeting_invalid_structure(self, tmp_path):
        """Test handling when meetings file has invalid structure."""
        meetings_file = tmp_path / "meetings.yaml"
        meetings_file.write_text("{}")  # Should be a list, not dict
        
        paths = {"meets": str(meetings_file)}
        result = insert_meeting("test meeting", paths)
        
        assert "error" in result
        assert "Invalid meetings file structure" in result["error"]