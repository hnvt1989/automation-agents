"""Base agent class for all agents in the system."""
from typing import Any, Dict, Optional
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel


class BaseAgent:
    """Base class for all agents providing common functionality."""
    
    def __init__(
        self,
        name: str,
        model: OpenAIModel,
        system_prompt: str,
        deps_type: Optional[Any] = None,
        result_type: Optional[Any] = None,
        mcp_servers: Optional[list] = None,
        **kwargs
    ):
        """Initialize the base agent.
        
        Args:
            name: Name of the agent
            model: OpenAI model to use
            system_prompt: System prompt for the agent
            deps_type: Dependencies type for the agent
            result_type: Result type for the agent
            mcp_servers: List of MCP servers for the agent
            **kwargs: Additional arguments for the Agent
        """
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        
        # Create the underlying pydantic-ai agent
        agent_kwargs = {
            "model": model,
            "system_prompt": system_prompt,
        }
        
        if deps_type is not None:
            agent_kwargs["deps_type"] = deps_type
        if result_type is not None:
            agent_kwargs["result_type"] = result_type
        if mcp_servers is not None:
            agent_kwargs["mcp_servers"] = mcp_servers
            
        agent_kwargs.update(kwargs)
        
        self.agent = Agent(**agent_kwargs)
    
    async def run(self, prompt: str, deps: Optional[Any] = None, **kwargs) -> Any:
        """Run the agent with the given prompt.
        
        Args:
            prompt: The prompt to run
            deps: Dependencies for the agent
            **kwargs: Additional arguments
            
        Returns:
            The agent's response
        """
        return await self.agent.run(prompt, deps=deps, **kwargs)
    
    async def run_stream(self, prompt: str, deps: Optional[Any] = None, **kwargs):
        """Run the agent in streaming mode.
        
        Args:
            prompt: The prompt to run
            deps: Dependencies for the agent
            **kwargs: Additional arguments
            
        Yields:
            Streaming responses from the agent
        """
        async with self.agent.run_stream(prompt, deps=deps, **kwargs) as stream:
            async for delta in stream:
                yield delta
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"<{self.__class__.__name__}(name='{self.name}')>"