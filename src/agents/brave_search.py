"""Brave Search agent for web searches."""
from typing import Any, Optional
from pydantic import BaseModel
from pydantic_ai.models.openai import OpenAIModel

from src.agents.base import BaseAgent
from src.core.constants import AgentType, SYSTEM_PROMPTS
from src.mcp import get_mcp_manager
from src.utils.logging import log_info, log_error


class BraveSearchAgent(BaseAgent):
    """Agent for performing web searches using Brave Search API."""
    
    def __init__(self, model: OpenAIModel):
        """Initialize the Brave Search agent.
        
        Args:
            model: OpenAI model to use
        """
        # Get MCP manager and server
        mcp_manager = get_mcp_manager()
        self.brave_server = mcp_manager.get_server("brave")
        
        super().__init__(
            name=AgentType.BRAVE_SEARCH,
            model=model,
            system_prompt=SYSTEM_PROMPTS[AgentType.BRAVE_SEARCH],
            mcp_servers=[self.brave_server]
        )
        
        log_info("Brave Search agent initialized")