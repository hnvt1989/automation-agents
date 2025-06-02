"""Primary orchestration agent."""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

from src.agents.base import BaseAgent
from src.core.constants import AgentType, SYSTEM_PROMPTS
from src.utils.logging import log_info, log_error


class PrimaryAgentDeps(BaseModel):
    """Dependencies for the primary agent."""
    agents: Dict[str, Any] = Field(default_factory=dict)
    query: str = ""
    debug: bool = False
    
    class Config:
        arbitrary_types_allowed = True


class PrimaryAgent(BaseAgent):
    """Primary orchestration agent that coordinates other agents."""
    
    def __init__(self, model: OpenAIModel, agents: Dict[str, Any]):
        """Initialize the primary agent.
        
        Args:
            model: OpenAI model to use
            agents: Dictionary of available agents
        """
        super().__init__(
            name=AgentType.PRIMARY,
            model=model,
            system_prompt=SYSTEM_PROMPTS[AgentType.PRIMARY],
            deps_type=PrimaryAgentDeps
        )
        
        self.agents = agents
        self._register_tools()
    
    def _register_tools(self):
        """Register tools for the primary agent."""
        
        @self.agent.tool
        async def delegate_to_brave_search(ctx: RunContext[PrimaryAgentDeps], query: str) -> str:
            """Delegate a search query to the Brave Search agent."""
            log_info(f"Delegating to Brave Search agent: {query}")
            try:
                brave_agent = ctx.deps.agents.get("brave_search")
                if not brave_agent:
                    return "Brave Search agent not available"
                
                result = await brave_agent.run(query)
                return str(result.data)
            except Exception as e:
                log_error(f"Error in Brave Search delegation: {str(e)}")
                return f"Error: {str(e)}"
        
        @self.agent.tool
        async def delegate_to_filesystem(ctx: RunContext[PrimaryAgentDeps], task: str) -> str:
            """Delegate a filesystem task to the Filesystem agent."""
            log_info(f"Delegating to Filesystem agent: {task}")
            try:
                fs_agent = ctx.deps.agents.get("filesystem")
                if not fs_agent:
                    return "Filesystem agent not available"
                
                result = await fs_agent.run(task)
                return str(result.data)
            except Exception as e:
                log_error(f"Error in Filesystem delegation: {str(e)}")
                return f"Error: {str(e)}"
        
        @self.agent.tool
        async def delegate_to_github(ctx: RunContext[PrimaryAgentDeps], task: str) -> str:
            """Delegate a GitHub task to the GitHub agent."""
            log_info(f"Delegating to GitHub agent: {task}")
            try:
                github_agent = ctx.deps.agents.get("github")
                if not github_agent:
                    return "GitHub agent not available"
                
                result = await github_agent.run(task)
                return str(result.data)
            except Exception as e:
                log_error(f"Error in GitHub delegation: {str(e)}")
                return f"Error: {str(e)}"
        
        @self.agent.tool
        async def delegate_to_slack(ctx: RunContext[PrimaryAgentDeps], task: str) -> str:
            """Delegate a Slack task to the Slack agent."""
            log_info(f"Delegating to Slack agent: {task}")
            try:
                slack_agent = ctx.deps.agents.get("slack")
                if not slack_agent:
                    return "Slack agent not available"
                
                result = await slack_agent.run(task)
                return str(result.data)
            except Exception as e:
                log_error(f"Error in Slack delegation: {str(e)}")
                return f"Error: {str(e)}"
        
        @self.agent.tool
        async def delegate_to_analyzer(ctx: RunContext[PrimaryAgentDeps], task: str) -> str:
            """Delegate an analysis task to the Analyzer agent."""
            log_info(f"Delegating to Analyzer agent: {task}")
            try:
                analyzer_agent = ctx.deps.agents.get("analyzer")
                if not analyzer_agent:
                    return "Analyzer agent not available"
                
                result = await analyzer_agent.run(task)
                return str(result.data)
            except Exception as e:
                log_error(f"Error in Analyzer delegation: {str(e)}")
                return f"Error: {str(e)}"
        
        @self.agent.tool
        async def delegate_to_rag(ctx: RunContext[PrimaryAgentDeps], query: str) -> str:
            """Delegate a knowledge base query to the RAG agent."""
            log_info(f"Delegating to RAG agent: {query}")
            try:
                rag_agent = ctx.deps.agents.get("rag")
                if not rag_agent:
                    return "RAG agent not available"
                
                result = await rag_agent.run(query)
                return str(result.data)
            except Exception as e:
                log_error(f"Error in RAG delegation: {str(e)}")
                return f"Error: {str(e)}"
    
    async def run(self, prompt: str, **kwargs) -> Any:
        """Run the primary agent.
        
        Args:
            prompt: The user prompt
            **kwargs: Additional arguments
            
        Returns:
            The agent's response
        """
        deps = PrimaryAgentDeps(
            agents=self.agents,
            query=prompt,
            debug=kwargs.get("debug", False)
        )
        
        return await super().run(prompt, deps=deps, **kwargs)