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
        
        @self.agent.tool
        async def handle_planner_task(ctx: RunContext[PrimaryAgentDeps], task: str) -> str:
            """Handle planning, task management, and meeting scheduling tasks.
            
            Use this for:
            - Adding/removing tasks
            - Scheduling/canceling meetings  
            - Logging work done
            - Daily planning
            """
            log_info(f"Handling planner task: {task}")
            try:
                from src.agents.planner_parser import PlannerParser
                from src.agents.planner_ops import PlannerOperations
                from src.agents.planner import plan_day
                
                # Initialize the parser and operations
                parser = PlannerParser(self.model)
                ops = PlannerOperations()
                
                # Parse the natural language query
                parsed = await parser.parse(task)
                
                if parsed["action"] == "error":
                    return f"Failed to understand request: {parsed['data'].get('message', 'Unknown error')}"
                
                action = parsed["action"]
                data = parsed["data"]
                
                # Handle different actions
                if action == "add_task":
                    result = ops.add_task(data)
                    if result["success"]:
                        task_info = result["task"]
                        return f"Task added successfully: {task_info['title']} (ID: {task_info['id']}, Due: {task_info['due_date']})"
                    else:
                        return f"Failed to add task: {result['error']}"
                
                elif action == "update_task":
                    identifier = data.get("identifier")
                    updates = data.get("updates", {})
                    result = ops.update_task(identifier, updates)
                    if result["success"]:
                        return result["message"]
                    else:
                        return f"Failed to update task: {result['error']}"
                
                elif action == "remove_task":
                    identifier = data.get("identifier")
                    result = ops.remove_task(identifier)
                    if result["success"]:
                        return result["message"]
                    else:
                        return f"Failed to remove task: {result['error']}"
                
                elif action == "add_meeting":
                    result = ops.add_meeting(data)
                    if result["success"]:
                        meeting = result["meeting"]
                        return f"Meeting scheduled: {meeting['event']} on {meeting['date']} at {meeting['time']}"
                    else:
                        return f"Failed to schedule meeting: {result['error']}"
                
                elif action == "remove_meeting":
                    result = ops.remove_meeting(
                        data.get("date"),
                        data.get("time"),
                        data.get("title")
                    )
                    if result["success"]:
                        return result["message"]
                    else:
                        return f"Failed to remove meeting: {result['error']}"
                
                elif action == "add_log":
                    # Check if we need to create a task first
                    if "task_id" not in data and "description" in data:
                        # Create task and log in one operation
                        result = ops.create_task_and_log(
                            data["description"],
                            data.get("hours", 0)
                        )
                    else:
                        # Regular log with existing task
                        result = ops.add_log(data)
                    
                    if result["success"]:
                        if "task" in result:
                            # Created task and logged
                            return result["message"]
                        else:
                            # Just logged
                            return f"Work logged: {data.get('hours', 0)} hours on {data.get('task_id', 'task')}"
                    else:
                        return f"Failed to log work: {result['error']}"
                
                elif action == "plan_day":
                    # For plan_day, we still use the original function
                    from datetime import date, timedelta
                    
                    target_date = date.today()
                    if "date" in data:
                        date_str = data["date"].lower()
                        if "tomorrow" in date_str:
                            target_date = date.today() + timedelta(days=1)
                        elif "yesterday" in date_str:
                            target_date = date.today() - timedelta(days=1)
                        elif "next week" in date_str:
                            target_date = date.today() + timedelta(weeks=1)
                    
                    payload = {
                        'paths': {
                            'tasks': 'data/tasks.yaml',
                            'logs': 'data/daily_logs.yaml',
                            'meets': 'data/meetings.yaml'
                        },
                        'target_date': target_date.isoformat(),
                        'work_hours': {'start': '09:00', 'end': '17:00'}
                    }
                    
                    result = plan_day(payload)
                    if "error" in result:
                        return f"Error creating plan: {result['error']}"
                    
                    return f"{result.get('yesterday_markdown', '')}\n\n{result.get('tomorrow_markdown', '')}"
                
                else:
                    return f"Unknown action: {action}"
                    
            except Exception as e:
                log_error(f"Error in planner task: {str(e)}")
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