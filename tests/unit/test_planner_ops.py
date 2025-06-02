"""Tests for planner operations."""

import pytest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime, timedelta
from src.agents.planner_ops import PlannerOperations, generate_task_id, find_task
import yaml


@pytest.fixture
def planner_ops():
    """Create a PlannerOperations instance."""
    return PlannerOperations()


@pytest.fixture
def sample_tasks():
    """Sample tasks data."""
    return [
        {
            "id": "TASK-1",
            "title": "Complete project",
            "priority": "high",
            "status": "in_progress",
            "tags": ["work"],
            "due_date": "2025-06-10"
        },
        {
            "id": "TASK-2",
            "title": "Job search",
            "priority": "medium",
            "status": "pending",
            "tags": ["personal"],
            "due_date": "2025-06-15"
        }
    ]


@pytest.fixture
def sample_meetings():
    """Sample meetings data."""
    return [
        {
            "date": "2025-06-03",
            "time": "10:00",
            "event": "Team standup"
        },
        {
            "date": "2025-06-04",
            "time": "14:00",
            "event": "Client meeting"
        }
    ]


@pytest.fixture
def sample_logs():
    """Sample logs data."""
    return {
        "2025-06-02": [
            {
                "task_id": "TASK-1",
                "description": "Working on API",
                "actual_hours": 3
            }
        ]
    }


def test_generate_task_id_empty_list():
    """Test generating task ID for empty task list."""
    assert generate_task_id([]) == "TASK-1"


def test_generate_task_id_with_existing():
    """Test generating task ID with existing tasks."""
    tasks = [{"id": "TASK-1"}, {"id": "TASK-2"}]
    assert generate_task_id(tasks) == "TASK-3"


def test_find_task_by_id(sample_tasks):
    """Test finding task by ID."""
    task = find_task(sample_tasks, "TASK-1")
    assert task is not None
    assert task["title"] == "Complete project"


def test_find_task_by_title(sample_tasks):
    """Test finding task by exact title."""
    task = find_task(sample_tasks, "job search")
    assert task is not None
    assert task["id"] == "TASK-2"


def test_find_task_by_partial_title(sample_tasks):
    """Test finding task by partial title match."""
    task = find_task(sample_tasks, "search")
    assert task is not None
    assert task["id"] == "TASK-2"


def test_find_task_not_found(sample_tasks):
    """Test finding non-existent task."""
    task = find_task(sample_tasks, "nonexistent")
    assert task is None


@patch('src.agents.planner_ops.load_yaml')
@patch('src.agents.planner_ops.save_yaml')
def test_add_task(mock_save, mock_load, planner_ops):
    """Test adding a new task."""
    mock_load.return_value = []
    
    result = planner_ops.add_task({
        "title": "New task",
        "priority": "high",
        "tags": ["urgent"]
    })
    
    assert result["success"] is True
    assert result["task"]["id"] == "TASK-1"
    assert result["task"]["title"] == "New task"
    assert result["task"]["priority"] == "high"
    assert "urgent" in result["task"]["tags"]
    
    # Verify save was called
    mock_save.assert_called_once()


@patch('src.agents.planner_ops.load_yaml')
@patch('src.agents.planner_ops.save_yaml')
def test_update_task(mock_save, mock_load, planner_ops, sample_tasks):
    """Test updating an existing task."""
    mock_load.return_value = sample_tasks
    
    result = planner_ops.update_task("TASK-1", {"status": "completed"})
    
    assert result["success"] is True
    assert "status: in_progress → completed" in result["message"]
    
    # Verify the task was updated
    mock_save.assert_called_once()
    saved_tasks = mock_save.call_args[0][1]
    assert saved_tasks[0]["status"] == "completed"


@patch('src.agents.planner_ops.load_yaml')
@patch('src.agents.planner_ops.save_yaml')
def test_update_task_add_tags(mock_save, mock_load, planner_ops, sample_tasks):
    """Test adding tags to a task."""
    mock_load.return_value = sample_tasks
    
    result = planner_ops.update_task("TASK-1", {"add_tags": ["urgent", "important"]})
    
    assert result["success"] is True
    assert "added tags: urgent, important" in result["message"]
    
    # Verify tags were added
    saved_tasks = mock_save.call_args[0][1]
    assert "urgent" in saved_tasks[0]["tags"]
    assert "important" in saved_tasks[0]["tags"]
    assert "work" in saved_tasks[0]["tags"]  # Original tag preserved


@patch('src.agents.planner_ops.load_yaml')
@patch('src.agents.planner_ops.save_yaml')
def test_remove_task(mock_save, mock_load, planner_ops, sample_tasks):
    """Test removing a task."""
    mock_load.return_value = sample_tasks
    
    result = planner_ops.remove_task("TASK-1")
    
    assert result["success"] is True
    assert "Removed task 'Complete project'" in result["message"]
    
    # Verify task was removed
    saved_tasks = mock_save.call_args[0][1]
    assert len(saved_tasks) == 1
    assert saved_tasks[0]["id"] == "TASK-2"


@patch('src.agents.planner_ops.load_yaml')
@patch('src.agents.planner_ops.save_yaml')
def test_add_meeting(mock_save, mock_load, planner_ops):
    """Test adding a meeting."""
    mock_load.return_value = []
    
    result = planner_ops.add_meeting({
        "title": "Team sync",
        "date": "2025-06-05",
        "time": "10:00"
    })
    
    assert result["success"] is True
    assert result["meeting"]["event"] == "Team sync"
    assert result["meeting"]["date"] == "2025-06-05"
    assert result["meeting"]["time"] == "10:00"
    
    mock_save.assert_called_once()


@patch('src.agents.planner_ops.load_yaml')
@patch('src.agents.planner_ops.save_yaml')
def test_remove_meeting(mock_save, mock_load, planner_ops, sample_meetings):
    """Test removing a meeting."""
    mock_load.return_value = sample_meetings
    
    result = planner_ops.remove_meeting("2025-06-03", "10:00", "standup")
    
    assert result["success"] is True
    assert "Removed meeting: Team standup" in result["message"]
    
    # Verify meeting was removed
    saved_meetings = mock_save.call_args[0][1]
    assert len(saved_meetings) == 1
    assert saved_meetings[0]["event"] == "Client meeting"


@patch('src.agents.planner_ops.load_yaml')
@patch('src.agents.planner_ops.save_yaml')
def test_add_log(mock_save, mock_load, planner_ops):
    """Test adding a work log."""
    mock_load.return_value = {}
    
    result = planner_ops.add_log({
        "task_id": "TASK-1",
        "description": "Fixed bug",
        "hours": 2.5
    })
    
    assert result["success"] is True
    assert result["log"]["task_id"] == "TASK-1"
    assert result["log"]["description"] == "Fixed bug"
    assert result["log"]["actual_hours"] == 2.5
    
    mock_save.assert_called_once()


@patch('src.agents.planner_ops.load_yaml')
@patch('src.agents.planner_ops.save_yaml')
def test_create_task_and_log(mock_save, mock_load, planner_ops):
    """Test creating a task and logging work in one operation."""
    # First call for tasks, second for logs
    mock_load.side_effect = [[], {}]
    
    result = planner_ops.create_task_and_log("Research automation", 3)
    
    assert result["success"] is True
    assert "Created task 'Research automation'" in result["message"]
    assert "logged 3 hours" in result["message"]
    assert result["task"]["title"] == "Research automation"
    assert result["log"]["actual_hours"] == 3
    
    # Should have saved twice (tasks and logs)
    assert mock_save.call_count == 2


@patch('src.agents.planner_ops.os.path.exists')
def test_load_yaml_file_not_found(mock_exists, planner_ops):
    """Test loading non-existent YAML file."""
    mock_exists.return_value = False
    
    with pytest.raises(FileNotFoundError):
        from src.agents.planner_ops import load_yaml
        load_yaml("nonexistent.yaml")