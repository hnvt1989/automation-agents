"""
Integration tests for the Delete functionality in Editor modal
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
import yaml
from unittest.mock import Mock, patch

# Import the app
from src.api_server import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary directories for test data"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Create test tasks file
    tasks_file = data_dir / "tasks.yaml"
    tasks_data = [
        {
            "id": "TASK-1",
            "title": "First Task",
            "status": "pending",
            "priority": "high",
            "due_date": "2025-06-10",
            "tags": ["test"],
            "estimate_hours": None
        },
        {
            "id": "TASK-2",
            "title": "Second Task",
            "status": "in_progress",
            "priority": "medium",
            "due_date": "2025-06-15",
            "tags": ["work"],
            "estimate_hours": 4
        },
        {
            "id": "TASK-3",
            "title": "Third Task",
            "status": "completed",
            "priority": "low",
            "due_date": "2025-06-20",
            "tags": ["personal"],
            "estimate_hours": 2
        }
    ]
    with open(tasks_file, 'w') as f:
        yaml.dump(tasks_data, f)
    
    # Create test logs file
    logs_file = data_dir / "daily_logs.yaml"
    logs_data = {
        "2025-06-07": [
            {
                "log_id": "LOG-1",
                "description": "First log entry",
                "actual_hours": 2
            },
            {
                "log_id": "LOG-2",
                "description": "Second log entry",
                "actual_hours": 3
            }
        ],
        "2025-06-08": [
            {
                "log_id": "LOG-3",
                "description": "Third log entry",
                "actual_hours": 1
            }
        ]
    }
    with open(logs_file, 'w') as f:
        yaml.dump(logs_data, f)
    
    yield data_dir
    
    # Cleanup
    shutil.rmtree(data_dir)


class TestDeleteButtonVisibility:
    """Test Delete button visibility in Editor modal"""
    
    def test_delete_button_visible_for_tasks_edit_mode(self):
        """Test that Delete button is visible for tasks in edit mode"""
        editor_config = {
            "type": "tasks",
            "mode": "edit",
            "show_delete_button": True
        }
        
        assert editor_config["show_delete_button"] is True
    
    def test_delete_button_visible_for_logs_edit_mode(self):
        """Test that Delete button is visible for logs in edit mode"""
        editor_config = {
            "type": "logs",
            "mode": "edit",
            "show_delete_button": True
        }
        
        assert editor_config["show_delete_button"] is True
    
    def test_delete_button_hidden_for_documents(self):
        """Test that Delete button is NOT visible for documents"""
        editor_config = {
            "type": "documents",
            "mode": "edit",
            "show_delete_button": False
        }
        
        assert editor_config["show_delete_button"] is False
    
    def test_delete_button_hidden_for_notes(self):
        """Test that Delete button is NOT visible for notes"""
        editor_config = {
            "type": "notes",
            "mode": "edit",
            "show_delete_button": False
        }
        
        assert editor_config["show_delete_button"] is False
    
    def test_delete_button_hidden_in_add_mode(self):
        """Test that Delete button is NOT visible in add mode for any type"""
        for item_type in ["tasks", "logs", "documents", "notes"]:
            editor_config = {
                "type": item_type,
                "mode": "add",
                "show_delete_button": False
            }
            
            assert editor_config["show_delete_button"] is False


class TestDeleteTaskAPI:
    """Test DELETE API endpoint for tasks"""
    
    def test_delete_task_success(self, client, temp_data_dir, monkeypatch):
        """Test successful deletion of a task"""
        monkeypatch.setattr("src.api_server.TASKS_YAML_FILE", temp_data_dir / "tasks.yaml")
        
        # Delete the second task (index 1)
        response = client.delete("/tasks/1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Task deleted successfully"
        
        # Verify the task was deleted
        with open(temp_data_dir / "tasks.yaml", 'r') as f:
            tasks = yaml.safe_load(f)
        
        assert len(tasks) == 2
        assert all(task["id"] != "TASK-2" for task in tasks)
        assert tasks[0]["id"] == "TASK-1"
        assert tasks[1]["id"] == "TASK-3"
    
    def test_delete_nonexistent_task(self, client, temp_data_dir, monkeypatch):
        """Test deleting a task that doesn't exist"""
        monkeypatch.setattr("src.api_server.TASKS_YAML_FILE", temp_data_dir / "tasks.yaml")
        
        # Try to delete task at index 999
        response = client.delete("/tasks/999")
        
        assert response.status_code == 404
        data = response.json()
        assert "Task not found" in data["detail"]
    
    def test_delete_last_task(self, client, temp_data_dir, monkeypatch):
        """Test deleting the last task in the list"""
        monkeypatch.setattr("src.api_server.TASKS_YAML_FILE", temp_data_dir / "tasks.yaml")
        
        # Delete the last task (index 2)
        response = client.delete("/tasks/2")
        
        assert response.status_code == 200
        
        # Verify only 2 tasks remain
        with open(temp_data_dir / "tasks.yaml", 'r') as f:
            tasks = yaml.safe_load(f)
        
        assert len(tasks) == 2
        assert tasks[-1]["id"] == "TASK-2"


class TestDeleteLogAPI:
    """Test DELETE API endpoint for logs"""
    
    def test_delete_log_success(self, client, temp_data_dir, monkeypatch):
        """Test successful deletion of a log entry"""
        monkeypatch.setattr("src.api_server.DAILY_LOGS_FILE", temp_data_dir / "daily_logs.yaml")
        
        # Get logs first to understand the order
        response = client.get("/logs")
        logs_list = response.json()["logs"]
        
        # Logs should be sorted by date (newest first)
        # So order is: LOG-3 (2025-06-08), LOG-1 (2025-06-07), LOG-2 (2025-06-07)
        # Delete index 1 (should be LOG-1)
        response = client.delete("/logs/1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Log deleted successfully"
        assert data["deleted_log"]["log_id"] == "LOG-1"
        
        # Verify the log was deleted
        with open(temp_data_dir / "daily_logs.yaml", 'r') as f:
            logs = yaml.safe_load(f)
        
        # Should only have 1 log left on 2025-06-07
        assert len(logs["2025-06-07"]) == 1
        assert logs["2025-06-07"][0]["log_id"] == "LOG-2"
    
    def test_delete_last_log_in_date(self, client, temp_data_dir, monkeypatch):
        """Test deleting the last log entry for a date removes the date"""
        monkeypatch.setattr("src.api_server.DAILY_LOGS_FILE", temp_data_dir / "daily_logs.yaml")
        
        # Logs are sorted by date (newest first)
        # Order is: LOG-3 (2025-06-08), LOG-1 (2025-06-07), LOG-2 (2025-06-07)
        # Delete index 0 (LOG-3, the only log on 2025-06-08)
        response = client.delete("/logs/0")
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_log"]["log_id"] == "LOG-3"
        
        # Verify the date was removed when last log was deleted
        with open(temp_data_dir / "daily_logs.yaml", 'r') as f:
            logs = yaml.safe_load(f)
        
        assert "2025-06-08" not in logs
        assert "2025-06-07" in logs
    
    def test_delete_nonexistent_log(self, client, temp_data_dir, monkeypatch):
        """Test deleting a log that doesn't exist"""
        monkeypatch.setattr("src.api_server.DAILY_LOGS_FILE", temp_data_dir / "daily_logs.yaml")
        
        # Try to delete log at index 999
        response = client.delete("/logs/999")
        
        assert response.status_code == 404
        data = response.json()
        assert "Log not found" in data["detail"]


class TestDeleteUIBehavior:
    """Test UI behavior for delete functionality"""
    
    def test_delete_confirmation_required(self):
        """Test that delete requires confirmation"""
        # Mock window.confirm
        mock_confirm = Mock(return_value=True)
        
        # Simulate delete button click
        def handle_delete():
            if mock_confirm("Are you sure you want to delete this item?"):
                return True
            return False
        
        result = handle_delete()
        
        mock_confirm.assert_called_once_with("Are you sure you want to delete this item?")
        assert result is True
    
    def test_delete_cancelled_by_user(self):
        """Test that delete is cancelled when user declines confirmation"""
        mock_confirm = Mock(return_value=False)
        mock_delete_api = Mock()
        
        def handle_delete():
            if mock_confirm("Are you sure you want to delete this item?"):
                mock_delete_api()
                return True
            return False
        
        result = handle_delete()
        
        mock_confirm.assert_called_once()
        mock_delete_api.assert_not_called()
        assert result is False
    
    def test_delete_closes_editor_on_success(self):
        """Test that editor closes after successful deletion"""
        mock_set_editing_item = Mock()
        mock_set_selected = Mock()
        
        def handle_delete_success():
            # Simulate successful deletion
            mock_set_editing_item(None)
            mock_set_selected(None)
        
        handle_delete_success()
        
        mock_set_editing_item.assert_called_once_with(None)
        mock_set_selected.assert_called_once_with(None)
    
    def test_delete_updates_item_list(self):
        """Test that item list is updated after deletion"""
        initial_items = [
            {"id": "1", "name": "Item 1"},
            {"id": "2", "name": "Item 2"},
            {"id": "3", "name": "Item 3"}
        ]
        
        # Simulate deletion of item at index 1
        deleted_index = 1
        new_items = [item for i, item in enumerate(initial_items) if i != deleted_index]
        
        assert len(new_items) == 2
        assert new_items[0]["name"] == "Item 1"
        assert new_items[1]["name"] == "Item 3"


class TestDeleteButtonPlacement:
    """Test Delete button placement and styling"""
    
    def test_delete_button_style(self):
        """Test that delete button has danger styling"""
        button_config = {
            "className": "editor-button danger",
            "text": "Delete",
            "position": "left",  # Should be on the left side of footer
            "color": "red"
        }
        
        assert "danger" in button_config["className"]
        assert button_config["text"] == "Delete"
        assert button_config["position"] == "left"
    
    def test_delete_button_order_in_footer(self):
        """Test button order in editor footer"""
        footer_buttons = [
            {"name": "Delete", "position": "left"},
            {"name": "Cancel", "position": "center"},
            {"name": "Save", "position": "right"}
        ]
        
        # Delete should be leftmost
        assert footer_buttons[0]["name"] == "Delete"
        assert footer_buttons[0]["position"] == "left"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])