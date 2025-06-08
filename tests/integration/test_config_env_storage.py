"""
Test configuration environment file storage functionality
"""
import pytest
import os
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from dotenv import set_key, load_dotenv

from src.api_server import app, save_config_to_env, load_config_from_env


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def temp_env_file(tmp_path):
    """Create a temporary environment file"""
    env_file = tmp_path / "test.env"
    env_file.touch()
    
    # Write some initial content
    with open(env_file, 'w') as f:
        f.write("# Test environment file\n")
        f.write("LLM_API_KEY=test_key\n")
    
    return env_file


class TestEnvironmentFileStorage:
    """Test saving and loading configuration from environment file"""
    
    def test_save_config_to_env(self, temp_env_file):
        """Test saving configuration to environment file"""
        config = {
            "documents_dir": "/test/documents",
            "notes_dir": "/test/notes",
            "tasks_file": "/test/tasks.yaml",
            "logs_file": "/test/logs.yaml"
        }
        
        with patch('src.api_server.ENV_FILE', temp_env_file):
            save_config_to_env(config)
        
        # Read the file and check contents
        with open(temp_env_file, 'r') as f:
            content = f.read()
        
        assert "DOCUMENTS_DIR=" in content and "/test/documents" in content
        assert "NOTES_DIR=" in content and "/test/notes" in content
        assert "TASKS_FILE=" in content and "/test/tasks.yaml" in content
        assert "LOGS_FILE=" in content and "/test/logs.yaml" in content
        # Original content should be preserved
        assert "LLM_API_KEY=test_key" in content
    
    def test_load_config_from_env(self, temp_env_file, monkeypatch):
        """Test loading configuration from environment file"""
        # Clear any existing env vars
        for key in ["DOCUMENTS_DIR", "NOTES_DIR", "TASKS_FILE", "LOGS_FILE"]:
            monkeypatch.delenv(key, raising=False)
        
        # Write config to env file
        set_key(str(temp_env_file), "DOCUMENTS_DIR", "/env/documents")
        set_key(str(temp_env_file), "NOTES_DIR", "/env/notes")
        set_key(str(temp_env_file), "TASKS_FILE", "/env/tasks.yaml")
        set_key(str(temp_env_file), "LOGS_FILE", "/env/logs.yaml")
        
        with patch('src.api_server.ENV_FILE', temp_env_file):
            config = load_config_from_env()
        
        assert config["documents_dir"] == "/env/documents"
        assert config["notes_dir"] == "/env/notes"
        assert config["tasks_file"] == "/env/tasks.yaml"
        assert config["logs_file"] == "/env/logs.yaml"
    
    def test_load_config_with_defaults(self, temp_env_file, monkeypatch):
        """Test loading configuration uses defaults when env vars not set"""
        # Clear any existing env vars
        for key in ["DOCUMENTS_DIR", "NOTES_DIR", "TASKS_FILE", "LOGS_FILE"]:
            monkeypatch.delenv(key, raising=False)
        
        # Empty env file
        with open(temp_env_file, 'w') as f:
            f.write("")
        
        with patch('src.api_server.ENV_FILE', temp_env_file):
            config = load_config_from_env()
        
        # Should use default values
        assert "va_notes" in config["documents_dir"]
        assert "meeting_notes" in config["notes_dir"]
        assert "tasks.yaml" in config["tasks_file"]
        assert "daily_logs.yaml" in config["logs_file"]
    
    def test_put_config_saves_to_env(self, client, temp_env_file, tmp_path):
        """Test PUT /config endpoint saves to environment file"""
        # Create test directories and files
        docs_dir = tmp_path / "docs"
        notes_dir = tmp_path / "notes"
        docs_dir.mkdir()
        notes_dir.mkdir()
        tasks_file = tmp_path / "tasks.yaml"
        logs_file = tmp_path / "logs.yaml"
        tasks_file.touch()
        logs_file.touch()
        
        config_data = {
            "documents_dir": str(docs_dir),
            "notes_dir": str(notes_dir),
            "tasks_file": str(tasks_file),
            "logs_file": str(logs_file)
        }
        
        with patch('src.api_server.ENV_FILE', temp_env_file):
            response = client.put("/config", json=config_data)
        
        assert response.status_code == 200
        
        # Check environment file was updated
        with open(temp_env_file, 'r') as f:
            content = f.read()
        
        # Paths should be saved as absolute paths
        assert "DOCUMENTS_DIR=" in content and str(docs_dir.absolute()) in content
        assert "NOTES_DIR=" in content and str(notes_dir.absolute()) in content
        assert "TASKS_FILE=" in content and str(tasks_file.absolute()) in content
        assert "LOGS_FILE=" in content and str(logs_file.absolute()) in content
    
    def test_env_file_created_if_missing(self, tmp_path):
        """Test that environment file is created if it doesn't exist"""
        env_file = tmp_path / "new.env"
        assert not env_file.exists()
        
        config = {
            "documents_dir": "/test/docs",
            "notes_dir": "/test/notes",
            "tasks_file": "/test/tasks.yaml",
            "logs_file": "/test/logs.yaml"
        }
        
        with patch('src.api_server.ENV_FILE', env_file):
            save_config_to_env(config)
        
        assert env_file.exists()
        
        with open(env_file, 'r') as f:
            content = f.read()
        
        assert "DOCUMENTS_DIR=" in content and "/test/docs" in content
    
    def test_config_persistence_across_restarts(self, client, temp_env_file, tmp_path, monkeypatch):
        """Test configuration persists across server restarts"""
        # Clear any existing env vars
        for key in ["DOCUMENTS_DIR", "NOTES_DIR", "TASKS_FILE", "LOGS_FILE"]:
            monkeypatch.delenv(key, raising=False)
        
        # Create test paths
        docs_dir = tmp_path / "persistent_docs"
        docs_dir.mkdir()
        
        config_data = {
            "documents_dir": str(docs_dir)
        }
        
        with patch('src.api_server.ENV_FILE', temp_env_file):
            # Save configuration
            response = client.put("/config", json=config_data)
            assert response.status_code == 200
            
            # Simulate restart by reloading config
            from src.api_server import config_storage
            config_storage.update(load_config_from_env())
            
            # Get configuration
            response = client.get("/config")
            assert response.status_code == 200
            data = response.json()
            
            assert data["documents_dir"] == str(docs_dir.absolute())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])