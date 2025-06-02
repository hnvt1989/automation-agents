"""Filesystem operations agent."""
from typing import Any, Optional
from pydantic import BaseModel
from pydantic_ai.models.openai import OpenAIModel

from src.agents.base import BaseAgent
from src.core.constants import AgentType, SYSTEM_PROMPTS
from src.mcp import get_mcp_manager
from src.utils.logging import log_info, log_error


class FilesystemAgent(BaseAgent):
    """Agent for performing filesystem operations."""
    
    def __init__(self, model: OpenAIModel):
        """Initialize the Filesystem agent.
        
        Args:
            model: OpenAI model to use
        """
        # Get MCP manager and server
        mcp_manager = get_mcp_manager()
        self.filesystem_server = mcp_manager.get_server("filesystem")
        
        super().__init__(
            name=AgentType.FILESYSTEM,
            model=model,
            system_prompt=SYSTEM_PROMPTS[AgentType.FILESYSTEM],
            mcp_servers=[self.filesystem_server]
        )
        
        log_info("Filesystem agent initialized")