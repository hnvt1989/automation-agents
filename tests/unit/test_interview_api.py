import pytest
import yaml
from pathlib import Path
from fastapi.testclient import TestClient
from src.api_server import app
import tempfile
import os


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def temp_interviews_dir():
    """Create a temporary directory for test interviews"""
    with tempfile.TemporaryDirectory() as temp_dir:
        interviews_dir = Path(temp_dir) / "interviews"
        interviews_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a sample interview file
        sample_interview = {
            "id": "INTERVIEW-TEST-1",
            "priority": "high",
            "status": "scheduled",
            "title": "Test Interview",
            "notes": "Sample interview notes"
        }
        
        with open(interviews_dir / "test_interview.yaml", 'w') as f:
            yaml.dump(sample_interview, f)
        
        yield interviews_dir


@pytest.fixture
def mock_interviews_config(temp_interviews_dir, monkeypatch):
    """Mock the config to use temporary interviews directory"""
    mock_config = {
        "documents_dir": str(temp_interviews_dir.parent / "documents"),
        "notes_dir": str(temp_interviews_dir.parent / "notes"), 
        "tasks_file": str(temp_interviews_dir.parent / "tasks.yaml"),
        "logs_file": str(temp_interviews_dir.parent / "logs.yaml"),
        "interviews_dir": str(temp_interviews_dir)
    }
    
    # Patch the config_storage
    monkeypatch.setattr("src.api_server.config_storage", mock_config)
    return mock_config


class TestInterviewAPI:
    """Test cases for interview API endpoints"""
    
    def test_get_interviews_empty(self, client, mock_interviews_config):
        """Test getting interviews when directory is empty"""
        # Clear the interviews directory
        interviews_dir = Path(mock_interviews_config["interviews_dir"])
        for file in interviews_dir.glob("*.yaml"):
            file.unlink()
            
        response = client.get("/interviews")
        assert response.status_code == 200
        data = response.json()
        assert "interviews" in data
        assert data["interviews"] == []
    
    def test_get_interviews_with_data(self, client, mock_interviews_config):
        """Test getting interviews with existing data"""
        response = client.get("/interviews")
        assert response.status_code == 200
        data = response.json()
        assert "interviews" in data
        assert len(data["interviews"]) == 1
        
        interview = data["interviews"][0]
        assert interview["id"] == "INTERVIEW-TEST-1"
        assert interview["name"] == "Test Interview"
        assert interview["priority"] == "high"
        assert interview["status"] == "scheduled"
        assert "notes" in interview
    
    def test_get_interview_content(self, client, mock_interviews_config):
        """Test getting content of a specific interview"""
        response = client.get("/interviews/test_interview/content")
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        # The content should be the YAML content as string
        content = data["content"]
        assert "INTERVIEW-TEST-1" in content
        assert "Test Interview" in content
    
    def test_get_interview_content_not_found(self, client, mock_interviews_config):
        """Test getting content of non-existent interview"""
        response = client.get("/interviews/nonexistent/content")
        assert response.status_code == 404
    
    def test_create_interview(self, client, mock_interviews_config):
        """Test creating a new interview"""
        new_interview = {
            "name": "New Interview",
            "description": "A new interview description",
            "priority": "medium",
            "status": "pending",
            "content": "id: INTERVIEW-NEW-1\npriority: medium\nstatus: pending\ntitle: New Interview\nnotes: |\n  New interview notes"
        }
        
        response = client.post("/interviews", json=new_interview)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "interview" in data
        
        # Verify the file was created
        interviews_dir = Path(mock_interviews_config["interviews_dir"])
        new_file = interviews_dir / "new_interview.yaml"
        assert new_file.exists()
    
    def test_update_interview(self, client, mock_interviews_config):
        """Test updating an existing interview"""
        update_data = {
            "name": "Updated Interview",
            "priority": "low",
            "status": "completed",
            "content": "id: INTERVIEW-TEST-1\npriority: low\nstatus: completed\ntitle: Updated Interview\nnotes: |\n  Updated notes"
        }
        
        response = client.put("/interviews/test_interview", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify the file was updated
        interviews_dir = Path(mock_interviews_config["interviews_dir"])
        updated_file = interviews_dir / "test_interview.yaml"
        with open(updated_file, 'r') as f:
            content = f.read()
            assert "Updated Interview" in content
            assert "completed" in content
    
    def test_update_interview_not_found(self, client, mock_interviews_config):
        """Test updating non-existent interview"""
        update_data = {
            "name": "Updated Interview",
            "content": "Some content"
        }
        
        response = client.put("/interviews/nonexistent", json=update_data)
        assert response.status_code == 404
    
    def test_delete_interview(self, client, mock_interviews_config):
        """Test deleting an interview"""
        response = client.delete("/interviews/test_interview")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify the file was deleted
        interviews_dir = Path(mock_interviews_config["interviews_dir"])
        deleted_file = interviews_dir / "test_interview.yaml"
        assert not deleted_file.exists()
    
    def test_delete_interview_not_found(self, client, mock_interviews_config):
        """Test deleting non-existent interview"""
        response = client.delete("/interviews/nonexistent")
        assert response.status_code == 404


@pytest.mark.integration
class TestInterviewIntegration:
    """Integration tests for interview functionality"""
    
    def test_interview_workflow(self, client, mock_interviews_config):
        """Test complete workflow: create, read, update, delete"""
        # Create
        new_interview = {
            "name": "Workflow Test Interview",
            "description": "Test workflow",
            "priority": "high",
            "status": "scheduled",
            "content": "id: INTERVIEW-WORKFLOW-1\npriority: high\nstatus: scheduled\ntitle: Workflow Test Interview\nnotes: Initial notes"
        }
        
        create_response = client.post("/interviews", json=new_interview)
        assert create_response.status_code == 200
        
        # Read all interviews
        list_response = client.get("/interviews")
        assert list_response.status_code == 200
        interviews = list_response.json()["interviews"]
        workflow_interview = next((i for i in interviews if "Workflow Test" in i["name"]), None)
        assert workflow_interview is not None
        
        # Read specific content
        content_response = client.get("/interviews/workflow_test_interview/content")
        assert content_response.status_code == 200
        assert "Workflow Test Interview" in content_response.json()["content"]
        
        # Update
        update_data = {
            "priority": "medium",
            "status": "in_progress",
            "content": "id: INTERVIEW-WORKFLOW-1\npriority: medium\nstatus: in_progress\ntitle: Workflow Test Interview\nnotes: Updated notes"
        }
        
        update_response = client.put("/interviews/workflow_test_interview", json=update_data)
        assert update_response.status_code == 200
        
        # Verify update
        updated_content_response = client.get("/interviews/workflow_test_interview/content")
        assert "in_progress" in updated_content_response.json()["content"]
        
        # Delete
        delete_response = client.delete("/interviews/workflow_test_interview")
        assert delete_response.status_code == 200
        
        # Verify deletion
        final_content_response = client.get("/interviews/workflow_test_interview/content")
        assert final_content_response.status_code == 404