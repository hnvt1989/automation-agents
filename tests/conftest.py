"""Pytest configuration and fixtures."""
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Add src to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import Settings
from src.mcp.manager import MCPServerManager


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    test_settings = Settings(
        llm_api_key="test-api-key",
        openai_api_key="test-openai-key",
        github_token="test-github-token",
        brave_search_key="test-brave-key",
        slack_bot_token="test-slack-bot-token",
        slack_app_token="test-slack-app-token",
        project_root=project_root,
        debug=True,
        log_level="DEBUG"
    )
    
    # Mock the get_settings function
    monkeypatch.setattr("src.core.config.get_settings", lambda: test_settings)
    
    return test_settings


@pytest.fixture
def mock_mcp_manager():
    """Mock MCP server manager."""
    manager = Mock(spec=MCPServerManager)
    manager.is_initialized.return_value = True
    manager.get_server.return_value = Mock()
    manager.get_all_servers.return_value = {
        "brave": Mock(),
        "filesystem": Mock(),
        "github": Mock(),
        "slack": Mock()
    }
    
    return manager


@pytest.fixture
async def async_mock_mcp_manager():
    """Async mock MCP server manager."""
    manager = AsyncMock(spec=MCPServerManager)
    manager.is_initialized.return_value = True
    manager.get_server.return_value = AsyncMock()
    manager.initialize = AsyncMock()
    manager.shutdown = AsyncMock()
    
    return manager


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def sample_env_file(temp_dir):
    """Create a sample .env file for testing."""
    env_content = """
MODEL_CHOICE=gpt-4o-mini
BASE_URL=https://api.openai.com/v1
LLM_API_KEY=test-key
OPENAI_API_KEY=test-openai-key
GITHUB_TOKEN=test-github-token
BRAVE_SEARCH_KEY=test-brave-key
SLACK_BOT_TOKEN=test-slack-bot-token
SLACK_APP_TOKEN=test-slack-app-token
DEBUG=true
LOG_LEVEL=DEBUG
"""
    
    env_file = temp_dir / "test.env"
    env_file.write_text(env_content.strip())
    
    return env_file


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset configuration singletons
    import src.core.config
    src.core.config._settings = None
    src.core.config._mcp_config = None
    
    # Reset MCP manager singleton
    import src.mcp.manager
    src.mcp.manager._mcp_manager = None
    
    # Reset ChromaDB client singleton
    import src.storage.chromadb_client
    src.storage.chromadb_client._chromadb_client = None
    
    yield
    
    # Clean up after test
    src.core.config._settings = None
    src.core.config._mcp_config = None
    src.mcp.manager._mcp_manager = None
    src.storage.chromadb_client._chromadb_client = None