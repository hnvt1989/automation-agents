"""
Integration tests for the Editor functionality (Add and Edit modes)
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
import yaml

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
    
    # Create subdirectories
    (data_dir / "va_notes").mkdir()
    (data_dir / "meeting_notes").mkdir()
    
    # Create test files
    tasks_file = data_dir / "tasks.yaml"
    tasks_data = [
        {
            "id": "TASK-1",
            "title": "Test Task",
            "status": "pending",
            "priority": "high",
            "due_date": "2025-06-10",
            "tags": ["test"],
            "estimate_hours": None
        }
    ]
    with open(tasks_file, 'w') as f:
        yaml.dump(tasks_data, f)
    
    logs_file = data_dir / "daily_logs.yaml"
    logs_data = {
        "2025-06-07": [
            {
                "log_id": "LOG-1",
                "description": "Test log entry",
                "actual_hours": 2
            }
        ]
    }
    with open(logs_file, 'w') as f:
        yaml.dump(logs_data, f)
    
    # Create a test document
    doc_file = data_dir / "va_notes" / "test_doc.md"
    doc_file.write_text("# Test Document\n\nTest content")
    
    # Create a test note
    note_file = data_dir / "meeting_notes" / "test_note.md"
    note_file.write_text("# Test Note\n\nNote content")
    
    yield data_dir
    
    # Cleanup
    shutil.rmtree(data_dir)


class TestEditMode:
    """Test editing existing items"""
    
    def test_edit_task(self, client, temp_data_dir, monkeypatch):
        """Test editing an existing task"""
        monkeypatch.setattr("src.api_server.TASKS_YAML_FILE", temp_data_dir / "tasks.yaml")
        
        # Update task
        response = client.put("/tasks/0", json={
            "name": "Updated Test Task",
            "title": "Updated Test Task",
            "status": "in_progress",
            "priority": "medium",
            "due_date": "2025-06-15"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify the update
        with open(temp_data_dir / "tasks.yaml", 'r') as f:
            tasks = yaml.safe_load(f)
        
        assert tasks[0]["title"] == "Updated Test Task"
        assert tasks[0]["status"] == "in_progress"
        assert tasks[0]["priority"] == "medium"
        assert tasks[0]["due_date"] == "2025-06-15"
    
    def test_edit_document_content(self, client, temp_data_dir, monkeypatch):
        """Test editing document content"""
        monkeypatch.setattr("src.api_server.VA_NOTES_DIR", temp_data_dir / "va_notes")
        
        # Update document content
        response = client.put("/documents/0", json={
            "name": "Test Doc",
            "description": "Updated description",
            "content": "# Updated Document\n\nNew content here"
        })
        
        assert response.status_code == 200
        
        # Verify content was updated
        doc_file = temp_data_dir / "va_notes" / "test_doc.md"
        content = doc_file.read_text()
        assert "# Updated Document" in content
        assert "New content here" in content
    
    def test_edit_note_content(self, client, temp_data_dir, monkeypatch):
        """Test editing note content"""
        monkeypatch.setattr("src.api_server.MEETING_NOTES_DIR", temp_data_dir / "meeting_notes")
        
        # Update note content
        response = client.put("/notes/0", json={
            "name": "Test Note",
            "content": "# Updated Note\n\nUpdated note content"
        })
        
        assert response.status_code == 200
        
        # Verify content was updated
        note_file = temp_data_dir / "meeting_notes" / "test_note.md"
        content = note_file.read_text()
        assert "# Updated Note" in content
        assert "Updated note content" in content
    
    def test_edit_log(self, client, temp_data_dir, monkeypatch):
        """Test editing a log entry"""
        monkeypatch.setattr("src.api_server.DAILY_LOGS_FILE", temp_data_dir / "daily_logs.yaml")
        
        # Update log
        response = client.put("/logs/0", json={
            "name": "Updated log description",
            "description": "Updated log description",
            "actual_hours": 4,
            "log_id": "LOG-1"
        })
        
        assert response.status_code == 200
        
        # Verify the update
        with open(temp_data_dir / "daily_logs.yaml", 'r') as f:
            logs = yaml.safe_load(f)
        
        assert logs["2025-06-07"][0]["description"] == "Updated log description"
        assert logs["2025-06-07"][0]["actual_hours"] == 4


class TestAddMode:
    """Test adding new items"""
    
    def test_add_task(self, client, temp_data_dir, monkeypatch):
        """Test adding a new task"""
        monkeypatch.setattr("src.api_server.TASKS_YAML_FILE", temp_data_dir / "tasks.yaml")
        
        # Add new task
        response = client.post("/tasks", json={
            "name": "New Task",
            "title": "New Task",
            "status": "pending",
            "priority": "high",
            "due_date": "2025-06-20",
            "tags": ["new", "test"]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["task"]["title"] == "New Task"
        
        # Verify the task was added
        with open(temp_data_dir / "tasks.yaml", 'r') as f:
            tasks = yaml.safe_load(f)
        
        assert len(tasks) == 2
        assert tasks[1]["title"] == "New Task"
        assert tasks[1]["id"] == "TASK-2"
    
    def test_add_document(self, client, temp_data_dir, monkeypatch):
        """Test adding a new document"""
        monkeypatch.setattr("src.api_server.VA_NOTES_DIR", temp_data_dir / "va_notes")
        
        # Add new document
        response = client.post("/documents", json={
            "name": "New Document",
            "description": "A new test document",
            "content": "# New Document\n\nThis is the content"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["filename"] == "new_document.md"
        
        # Verify file was created
        doc_file = temp_data_dir / "va_notes" / "new_document.md"
        assert doc_file.exists()
        content = doc_file.read_text()
        assert "# New Document" in content
        assert "This is the content" in content
    
    def test_add_note(self, client, temp_data_dir, monkeypatch):
        """Test adding a new note"""
        monkeypatch.setattr("src.api_server.MEETING_NOTES_DIR", temp_data_dir / "meeting_notes")
        
        # Add new note
        response = client.post("/notes", json={
            "name": "Meeting Notes",
            "description": "Team meeting notes",
            "content": "# Meeting Notes\n\n## Agenda\n- Item 1\n- Item 2"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["filename"] == "meeting_notes.md"
        
        # Verify file was created
        note_file = temp_data_dir / "meeting_notes" / "meeting_notes.md"
        assert note_file.exists()
        content = note_file.read_text()
        assert "# Meeting Notes" in content
        assert "## Agenda" in content
    
    def test_add_log(self, client, temp_data_dir, monkeypatch):
        """Test adding a new log entry"""
        monkeypatch.setattr("src.api_server.DAILY_LOGS_FILE", temp_data_dir / "daily_logs.yaml")
        
        # Add new log
        response = client.post("/logs", json={
            "name": "New work log",
            "description": "New work log",
            "date": "2025-06-08",
            "actual_hours": 3
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["log"]["description"] == "New work log"
        
        # Verify log was added
        with open(temp_data_dir / "daily_logs.yaml", 'r') as f:
            logs = yaml.safe_load(f)
        
        assert "2025-06-08" in logs
        assert len(logs["2025-06-08"]) == 1
        assert logs["2025-06-08"][0]["description"] == "New work log"
        assert logs["2025-06-08"][0]["actual_hours"] == 3


class TestEditorValidation:
    """Test validation and error handling"""
    
    def test_edit_nonexistent_task(self, client, temp_data_dir, monkeypatch):
        """Test editing a task that doesn't exist"""
        monkeypatch.setattr("src.api_server.TASKS_YAML_FILE", temp_data_dir / "tasks.yaml")
        
        response = client.put("/tasks/999", json={
            "name": "Nonexistent",
            "title": "Nonexistent"
        })
        
        assert response.status_code == 404
    
    def test_add_document_with_empty_name(self, client, temp_data_dir, monkeypatch):
        """Test adding a document without a name"""
        monkeypatch.setattr("src.api_server.VA_NOTES_DIR", temp_data_dir / "va_notes")
        
        response = client.post("/documents", json={
            "name": "",
            "content": "Some content"
        })
        
        # Should still create with a default name
        assert response.status_code == 200
    
    def test_field_mapping_for_logs(self, client, temp_data_dir, monkeypatch):
        """Test that log field mapping works correctly"""
        monkeypatch.setattr("src.api_server.DAILY_LOGS_FILE", temp_data_dir / "daily_logs.yaml")
        
        # The frontend sends 'name' but backend expects 'description'
        response = client.put("/logs/0", json={
            "name": "Frontend sends this as name",
            "description": "Frontend sends this as name",
            "actual_hours": 5
        })
        
        assert response.status_code == 200
        
        # Verify the mapping worked
        with open(temp_data_dir / "daily_logs.yaml", 'r') as f:
            logs = yaml.safe_load(f)
        
        assert logs["2025-06-07"][0]["description"] == "Frontend sends this as name"


class TestContentFetching:
    """Test fetching content for editing"""
    
    def test_fetch_document_content(self, client, temp_data_dir, monkeypatch):
        """Test fetching document content endpoint"""
        monkeypatch.setattr("src.api_server.VA_NOTES_DIR", temp_data_dir / "va_notes")
        
        response = client.get("/documents/0/content")
        
        assert response.status_code == 200
        data = response.json()
        assert "# Test Document" in data["content"]
        assert "Test content" in data["content"]
    
    def test_fetch_note_content(self, client, temp_data_dir, monkeypatch):
        """Test fetching note content endpoint"""
        monkeypatch.setattr("src.api_server.MEETING_NOTES_DIR", temp_data_dir / "meeting_notes")
        
        response = client.get("/notes/0/content")
        
        assert response.status_code == 200
        data = response.json()
        assert "# Test Note" in data["content"]
        assert "Note content" in data["content"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])