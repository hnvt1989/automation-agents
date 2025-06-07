"""
Test to verify log deletion works correctly with proper indexing
"""
import pytest
import tempfile
import yaml
from pathlib import Path
from fastapi.testclient import TestClient
from src.api_server import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture  
def temp_logs_file(tmp_path, monkeypatch):
    """Create a temporary logs file with test data"""
    logs_file = tmp_path / "daily_logs.yaml"
    
    # Create test data with multiple dates to test sorting
    test_data = {
        "2025-06-05": [
            {"log_id": "LOG-A", "description": "Old log A", "actual_hours": 1},
            {"log_id": "LOG-B", "description": "Old log B", "actual_hours": 2}
        ],
        "2025-06-08": [
            {"log_id": "LOG-C", "description": "Recent log C", "actual_hours": 3}
        ],
        "2025-06-10": [
            {"log_id": "LOG-D", "description": "Newest log D", "actual_hours": 4},
            {"log_id": "LOG-E", "description": "Newest log E", "actual_hours": 5}
        ]
    }
    
    with open(logs_file, 'w') as f:
        yaml.dump(test_data, f)
    
    # Patch the logs file path
    monkeypatch.setattr("src.api_server.DAILY_LOGS_FILE", logs_file)
    
    return logs_file


def test_log_deletion_order(client, temp_logs_file):
    """Test that logs are deleted in the correct order matching the display"""
    
    # First, get the logs to see the order
    response = client.get("/logs")
    assert response.status_code == 200
    logs = response.json()["logs"]
    
    # Verify the order is newest first
    assert len(logs) == 5
    assert "LOG-D" in logs[0]["description"] or "LOG-E" in logs[0]["description"]  # Newest date first
    assert "LOG-D" in logs[1]["description"] or "LOG-E" in logs[1]["description"]  # Newest date first
    assert "LOG-C" in logs[2]["description"]  # Middle date
    assert "LOG-A" in logs[3]["description"] or "LOG-B" in logs[3]["description"]  # Oldest date last
    assert "LOG-A" in logs[4]["description"] or "LOG-B" in logs[4]["description"]  # Oldest date last
    
    # Delete the first log (should be one from 2025-06-10)
    response = client.delete("/logs/0")
    assert response.status_code == 200
    deleted_log = response.json()["deleted_log"]
    assert deleted_log["log_id"] in ["LOG-D", "LOG-E"]
    
    # Verify the correct log was deleted
    response = client.get("/logs")
    remaining_logs = response.json()["logs"]
    assert len(remaining_logs) == 4
    
    # The deleted log should not be in the list
    remaining_ids = [log["log_id"] for log in remaining_logs]
    assert deleted_log["log_id"] not in remaining_ids


def test_delete_middle_log(client, temp_logs_file):
    """Test deleting a log from the middle of the list"""
    
    # Get initial logs
    response = client.get("/logs")
    initial_logs = response.json()["logs"]
    
    # Delete index 2 (should be LOG-C)
    response = client.delete("/logs/2")
    assert response.status_code == 200
    deleted_log = response.json()["deleted_log"]
    assert deleted_log["log_id"] == "LOG-C"
    
    # Verify correct deletion
    response = client.get("/logs")
    remaining_logs = response.json()["logs"] 
    assert len(remaining_logs) == 4
    assert all(log["log_id"] != "LOG-C" for log in remaining_logs)


def test_delete_last_log(client, temp_logs_file):
    """Test deleting the last log in the list"""
    
    # Get initial count
    response = client.get("/logs")
    initial_count = len(response.json()["logs"])
    
    # Delete the last log
    response = client.delete(f"/logs/{initial_count - 1}")
    assert response.status_code == 200
    
    # Should have one less log
    response = client.get("/logs")
    assert len(response.json()["logs"]) == initial_count - 1


def test_update_log_with_correct_index(client, temp_logs_file):
    """Test that updating logs also uses the correct index"""
    
    # Update the first log
    update_data = {
        "name": "Updated description",
        "actual_hours": 10
    }
    
    response = client.put("/logs/0", json=update_data)
    assert response.status_code == 200
    
    # Verify the correct log was updated
    response = client.get("/logs")
    logs = response.json()["logs"]
    
    # First log should have the updated description
    assert logs[0]["name"] == "Updated description"
    assert logs[0]["actual_hours"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])