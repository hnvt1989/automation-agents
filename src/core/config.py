"""Configuration management for the application."""
import os
from typing import Optional, Dict, Any
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings
from pydantic import Field, validator
from dotenv import load_dotenv
from pathlib import Path


# Load environment variables
env_path = Path(__file__).parent.parent.parent / "local.env"
if env_path.exists():
    load_dotenv(env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Model configuration
    model_choice: str = Field(default="gpt-4o-mini", env="MODEL_CHOICE")
    base_url: str = Field(default="https://api.openai.com/v1", env="BASE_URL")
    llm_api_key: str = Field(default="no-api-key-provided", env="LLM_API_KEY")
    
    # API Keys
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    github_token: Optional[str] = Field(default=None, env="GITHUB_TOKEN")
    brave_search_key: Optional[str] = Field(default=None, env="BRAVE_SEARCH_KEY")
    slack_bot_token: Optional[str] = Field(default=None, env="SLACK_BOT_TOKEN")
    slack_app_token: Optional[str] = Field(default=None, env="SLACK_APP_TOKEN")
    
    # Paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    mcp_tools_path: Path = Field(default_factory=lambda: Path.home() / ".config" / "mcp-tools")
    
    # ChromaDB settings
    chroma_persist_directory: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent / "chroma_db"
    )
    
    # Neo4j settings for knowledge graph
    neo4j_uri: Optional[str] = Field(
        default=None,
        env="NEO4J_URI",
        description="Neo4j connection URI (e.g., bolt://localhost:7687)"
    )
    neo4j_user: str = Field(
        default="neo4j",
        env="NEO4J_USER",
        description="Neo4j username"
    )
    neo4j_password: Optional[str] = Field(
        default=None,
        env="NEO4J_PASSWORD",
        description="Neo4j password"
    )
    
    # Application settings
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()
    
    @validator("llm_api_key")
    def validate_api_key(cls, v):
        """Ensure API key is provided."""
        if v == "no-api-key-provided":
            raise ValueError("LLM_API_KEY must be set in environment variables")
        return v
    
    class Config:
        """Pydantic config."""
        env_file = "local.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from environment


class MCPServerConfig(BaseSettings):
    """Configuration for MCP servers."""
    
    brave_search: Dict[str, Any] = Field(
        default_factory=lambda: {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY", "")}
        }
    )
    
    filesystem: Dict[str, Any] = Field(
        default_factory=lambda: {
            "command": "npx",
            "args": [
                "-y", 
                "@modelcontextprotocol/server-filesystem",
                os.getenv("LOCAL_FILE_DIR", "/tmp"),
                os.getenv("LOCAL_FILE_DIR_KNOWLEDGE_BASE", "/tmp")
            ]
        }
    )
    
    github: Dict[str, Any] = Field(
        default_factory=lambda: {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_TOKEN", "")}
        }
    )
    
    slack: Dict[str, Any] = Field(
        default_factory=lambda: {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-slack"],
            "env": {
                "SLACK_BOT_TOKEN": os.getenv("SLACK_BOT_TOKEN", ""),
                "SLACK_TEAM_ID": os.getenv("SLACK_TEAM_ID", "")
            }
        }
    )


# Singleton instance
_settings: Optional[Settings] = None
_mcp_config: Optional[MCPServerConfig] = None


def get_settings() -> Settings:
    """Get the application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_mcp_config() -> MCPServerConfig:
    """Get the MCP server configuration singleton."""
    global _mcp_config
    if _mcp_config is None:
        _mcp_config = MCPServerConfig()
    return _mcp_config