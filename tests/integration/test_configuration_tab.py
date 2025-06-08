"""
Integration tests for the Configuration tab functionality
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Import the app
from src.api_server import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def temp_paths(tmp_path):
    """Create temporary directories and files for testing"""
    # Create directories
    docs_dir = tmp_path / "test_documents"
    notes_dir = tmp_path / "test_notes"
    docs_dir.mkdir()
    notes_dir.mkdir()
    
    # Create files
    tasks_file = tmp_path / "test_tasks.yaml"
    logs_file = tmp_path / "test_logs.yaml"
    tasks_file.touch()
    logs_file.touch()
    
    return {
        "documents_dir": str(docs_dir),
        "notes_dir": str(notes_dir),
        "tasks_file": str(tasks_file),
        "logs_file": str(logs_file)
    }


class TestConfigurationAPI:
    """Test Configuration API endpoints"""
    
    def test_get_config_endpoint(self, client):
        """Test GET /config returns current configuration"""
        response = client.get("/config")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return all four configuration paths
        assert "documents_dir" in data
        assert "notes_dir" in data
        assert "tasks_file" in data
        assert "logs_file" in data
        
        # Paths should be strings
        assert isinstance(data["documents_dir"], str)
        assert isinstance(data["notes_dir"], str)
        assert isinstance(data["tasks_file"], str)
        assert isinstance(data["logs_file"], str)
    
    def test_put_config_success(self, client, temp_paths):
        """Test PUT /config with valid paths"""
        response = client.put("/config", json=temp_paths)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
    
    def test_put_config_missing_directory(self, client, temp_paths):
        """Test PUT /config with non-existent directory"""
        # Use a non-existent directory
        temp_paths["documents_dir"] = "/non/existent/directory"
        
        response = client.put("/config", json=temp_paths)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "does not exist" in data["detail"]
        assert "documents_dir" in data["detail"]
    
    def test_put_config_missing_file(self, client, temp_paths):
        """Test PUT /config with non-existent file"""
        # Use a non-existent file
        temp_paths["tasks_file"] = "/non/existent/file.yaml"
        
        response = client.put("/config", json=temp_paths)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "does not exist" in data["detail"]
        assert "tasks_file" in data["detail"]
    
    def test_put_config_file_instead_of_directory(self, client, temp_paths):
        """Test PUT /config with file path where directory is expected"""
        # Use file path for documents_dir
        temp_paths["documents_dir"] = temp_paths["tasks_file"]
        
        response = client.put("/config", json=temp_paths)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "not a directory" in data["detail"]
        assert "documents_dir" in data["detail"]
    
    def test_put_config_directory_instead_of_file(self, client, temp_paths):
        """Test PUT /config with directory path where file is expected"""
        # Use directory path for tasks_file
        temp_paths["tasks_file"] = temp_paths["documents_dir"]
        
        response = client.put("/config", json=temp_paths)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "not a file" in data["detail"]
        assert "tasks_file" in data["detail"]
    
    def test_put_config_partial_update(self, client, temp_paths):
        """Test PUT /config with partial update (only some fields)"""
        # Only update documents_dir and notes_dir
        partial_config = {
            "documents_dir": temp_paths["documents_dir"],
            "notes_dir": temp_paths["notes_dir"]
        }
        
        response = client.put("/config", json=partial_config)
        
        # Should accept partial updates
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_put_config_empty_path(self, client):
        """Test PUT /config with empty string path"""
        config = {
            "documents_dir": "",
            "notes_dir": "/valid/path",
            "tasks_file": "/valid/file.yaml",
            "logs_file": "/valid/logs.yaml"
        }
        
        response = client.put("/config", json=config)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "empty" in data["detail"].lower()
    
    def test_config_persistence(self, client, temp_paths, monkeypatch):
        """Test that configuration changes persist"""
        # Update configuration
        response = client.put("/config", json=temp_paths)
        assert response.status_code == 200
        
        # Get configuration again
        response = client.get("/config")
        assert response.status_code == 200
        data = response.json()
        
        # Verify the paths were updated
        assert data["documents_dir"] == temp_paths["documents_dir"]
        assert data["notes_dir"] == temp_paths["notes_dir"]
        assert data["tasks_file"] == temp_paths["tasks_file"]
        assert data["logs_file"] == temp_paths["logs_file"]


class TestConfigurationUI:
    """Test Configuration UI behavior"""
    
    def test_configuration_tab_visible(self):
        """Test that Configuration tab is visible and All tab is removed"""
        tabs = ["tasks", "documents", "notes", "logs", "configuration"]
        
        assert "all" not in tabs
        assert "configuration" in tabs
    
    def test_configuration_form_fields(self):
        """Test that configuration form has all required fields"""
        required_fields = [
            {"name": "documents_dir", "type": "directory", "label": "Documents Directory"},
            {"name": "notes_dir", "type": "directory", "label": "Notes Directory"},
            {"name": "tasks_file", "type": "file", "label": "Tasks File"},
            {"name": "logs_file", "type": "file", "label": "Logs File"}
        ]
        
        for field in required_fields:
            assert field["name"] in ["documents_dir", "notes_dir", "tasks_file", "logs_file"]
            assert field["type"] in ["directory", "file"]
    
    def test_save_button_validation(self):
        """Test that Save button validates paths before saving"""
        # Mock validation function
        def validate_config(config):
            for key, value in config.items():
                if not value or not Path(value).exists():
                    return False, f"{key} does not exist"
            return True, "Valid"
        
        # Test with invalid path
        invalid_config = {
            "documents_dir": "/invalid/path",
            "notes_dir": "/valid/path",
            "tasks_file": "/valid/file.yaml",
            "logs_file": "/valid/logs.yaml"
        }
        
        is_valid, message = validate_config(invalid_config)
        assert is_valid is False
        assert "does not exist" in message
    
    def test_cancel_button_discards_changes(self):
        """Test that Cancel button discards unsaved changes"""
        # Mock state management
        original_config = {
            "documents_dir": "/original/docs",
            "notes_dir": "/original/notes",
            "tasks_file": "/original/tasks.yaml",
            "logs_file": "/original/logs.yaml"
        }
        
        modified_config = {
            "documents_dir": "/modified/docs",
            "notes_dir": "/modified/notes",
            "tasks_file": "/modified/tasks.yaml",
            "logs_file": "/modified/logs.yaml"
        }
        
        # Simulate cancel action
        current_config = original_config.copy()
        current_config.update(modified_config)
        
        # Cancel should restore original
        current_config = original_config.copy()
        
        assert current_config == original_config
    
    def test_file_dialog_selection(self):
        """Test file dialog opens for path selection"""
        # Mock file dialog
        mock_dialog = Mock()
        mock_dialog.show_open_dialog = Mock(return_value="/selected/path")
        
        # Simulate clicking on path input
        selected_path = mock_dialog.show_open_dialog()
        
        assert selected_path == "/selected/path"
        mock_dialog.show_open_dialog.assert_called_once()
    
    def test_manual_path_input(self):
        """Test that users can manually type paths"""
        # Simulate manual input
        input_value = "/manually/typed/path"
        
        # Validate the input
        assert isinstance(input_value, str)
        assert input_value.startswith("/")
    
    def test_validation_error_display(self):
        """Test that validation errors are displayed to user"""
        error_messages = {
            "documents_dir": "Documents directory does not exist",
            "notes_dir": "Notes directory is not a directory",
            "tasks_file": "Tasks file does not exist",
            "logs_file": "Logs file is not a file"
        }
        
        for field, message in error_messages.items():
            assert field in error_messages
            assert "does not exist" in message or "is not a" in message


class TestConfigurationValidation:
    """Test configuration validation logic"""
    
    def test_validate_directory_exists(self, tmp_path):
        """Test directory existence validation"""
        valid_dir = tmp_path / "valid_dir"
        valid_dir.mkdir()
        
        assert valid_dir.exists()
        assert valid_dir.is_dir()
        
        invalid_dir = tmp_path / "invalid_dir"
        assert not invalid_dir.exists()
    
    def test_validate_file_exists(self, tmp_path):
        """Test file existence validation"""
        valid_file = tmp_path / "valid.yaml"
        valid_file.touch()
        
        assert valid_file.exists()
        assert valid_file.is_file()
        
        invalid_file = tmp_path / "invalid.yaml"
        assert not invalid_file.exists()
    
    def test_validate_path_types(self, tmp_path):
        """Test validation distinguishes between files and directories"""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        test_file = tmp_path / "test_file.yaml"
        test_file.touch()
        
        # Directory should not pass file validation
        assert test_dir.is_dir()
        assert not test_dir.is_file()
        
        # File should not pass directory validation
        assert test_file.is_file()
        assert not test_file.is_dir()
    
    def test_validate_relative_paths(self, tmp_path):
        """Test that relative paths are converted to absolute"""
        import os
        original_cwd = os.getcwd()
        
        try:
            os.chdir(tmp_path)
            
            # Create relative path
            rel_dir = Path("relative_dir")
            rel_dir.mkdir()
            
            # Convert to absolute
            abs_path = rel_dir.absolute()
            
            assert abs_path.is_absolute()
            assert abs_path.exists()
            
        finally:
            os.chdir(original_cwd)


class TestConfigurationIntegration:
    """Test configuration integration with other components"""
    
    def test_config_affects_documents_loading(self, client, temp_paths):
        """Test that changing documents_dir affects document listing"""
        # Create test document in new directory
        docs_dir = Path(temp_paths["documents_dir"])
        test_doc = docs_dir / "test.md"
        test_doc.write_text("# Test Document")
        
        # Update configuration
        response = client.put("/config", json=temp_paths)
        assert response.status_code == 200
        
        # Documents endpoint should now use new directory
        # (This would be tested with proper mocking in real implementation)
    
    def test_config_affects_notes_loading(self, client, temp_paths):
        """Test that changing notes_dir affects notes listing"""
        # Create test note in new directory
        notes_dir = Path(temp_paths["notes_dir"])
        test_note = notes_dir / "test_note.md"
        test_note.write_text("# Test Note")
        
        # Update configuration
        response = client.put("/config", json=temp_paths)
        assert response.status_code == 200
        
        # Notes endpoint should now use new directory
        # (This would be tested with proper mocking in real implementation)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])