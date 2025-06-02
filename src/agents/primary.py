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
                from src.agents.planner import (
                    insert_task, insert_meeting, insert_daily_log,
                    remove_task, remove_meeting, remove_daily_log, 
                    update_task, plan_day
                )
                import re
                from datetime import datetime, date, timedelta
                
                task_lower = task.lower().strip()
                
                # Check if it's a task insertion
                if any(keyword in task_lower for keyword in ['add task', 'new task', 'create task', 'task:']):
                    # Extract the task description
                    task_text = task
                    # Try different prefix patterns
                    prefixes = ['add task:', 'new task:', 'create task:', 'task:', 'add task', 'new task', 'create task']
                    for prefix in prefixes:
                        if prefix in task_lower:
                            idx = task_lower.find(prefix) + len(prefix)
                            task_text = task[idx:].strip()
                            # Remove any leading quotes or colons
                            task_text = task_text.lstrip(':').strip().strip('"\'')
                            break
                    
                    result = insert_task(task_text)
                    if result.get("success"):
                        return f"Task added successfully: {result['task']['title']} (ID: {result['task']['id']}, Due: {result['task']['due_date']})"
                    else:
                        return f"Failed to add task: {result.get('error', 'Unknown error')}"
                
                # Check if it's a meeting insertion
                elif any(keyword in task_lower for keyword in ['add meeting', 'add meetings', 'schedule meeting', 'new meeting', 'meeting:', 'schedule:']):
                    # Extract the meeting description
                    meeting_text = task
                    for prefix in ['add meetings', 'add meeting:', 'schedule meeting:', 'new meeting:', 'meeting:', 'schedule:', 'add meeting']:
                        if prefix in task_lower:
                            meeting_text = task[task_lower.find(prefix) + len(prefix):].strip()
                            break
                    
                    result = insert_meeting(meeting_text)
                    if result.get("success"):
                        meeting = result['meeting']
                        return f"Meeting scheduled: {meeting['event']} on {meeting['date']} at {meeting['time']}"
                    else:
                        return f"Failed to schedule meeting: {result.get('error', 'Unknown error')}"
                
                # Check if it's a daily log insertion
                elif any(keyword in task_lower for keyword in ['log work', 'add log', 'work log', 'add a daily log', 'add daily log', 'spent', 'worked on']):
                    # Check if this is a pattern like "add a daily log 'description' took X hours"
                    # Handle both quoted and unquoted descriptions
                    daily_log_pattern = re.search(r"add\s+(?:a\s+)?daily\s+log\s+(?:['\"]([^'\"]+)['\"]|(.+?))\s+(?:took|spent|for)\s+(\d+(?:\.\d+)?)\s*hours?", task_lower)
                    
                    if daily_log_pattern:
                        # This is a new daily log without a task ID
                        # Group 1 is for quoted text, group 2 is for unquoted text
                        description = (daily_log_pattern.group(1) if daily_log_pattern.group(1) else daily_log_pattern.group(2)).strip()
                        hours = float(daily_log_pattern.group(3))
                        
                        # We need to create a task first, then log work
                        # Extract just the description for the task title
                        task_result = insert_task(description)
                        if task_result.get("success"):
                            task_id = task_result['task']['id']
                            # Now log the work with clean description
                            result = insert_daily_log(description, task_id, hours)
                            if result.get("success"):
                                return f"Created task '{description}' ({task_id}) and logged {hours} hours of work"
                            else:
                                return f"Task created but failed to log work: {result.get('error', 'Unknown error')}"
                        else:
                            return f"Failed to create task: {task_result.get('error', 'Unknown error')}"
                    else:
                        # Original pattern - expects a task ID
                        task_id_match = re.search(r'\b([A-Z]+-\d+)\b', task)
                        if not task_id_match:
                            return "Could not find task ID. Please specify a task ID like 'TASK-1' or 'ONBOARDING-1'"
                        
                        task_id = task_id_match.group(1)
                        
                        hours_match = re.search(r'(\d+(?:\.\d+)?)\s*hours?', task_lower)
                        if not hours_match:
                            return "Could not find hours. Please specify hours like '3 hours' or '2.5 hours'"
                        
                        hours = float(hours_match.group(1))
                        
                        # Extract description - remove the task ID and hours from the text
                        description = task
                        # Remove task ID
                        description = re.sub(r'\b' + task_id + r'\b', '', description)
                        # Remove hours
                        description = re.sub(r'\b\d+(?:\.\d+)?\s*hours?\b', '', description)
                        # Remove common prefixes
                        for prefix in ['log work', 'add log', 'work log', 'spent', 'worked on']:
                            if prefix in description.lower():
                                idx = description.lower().find(prefix)
                                description = description[:idx] + description[idx + len(prefix):]
                        # Clean up
                        description = re.sub(r'\s+', ' ', description).strip()
                        description = description.strip(':').strip()
                        
                        # Use the cleaned description
                        result = insert_daily_log(description, task_id, hours)
                        if result.get("success"):
                            return f"Work logged: {hours} hours on {task_id} for date {result['date']}"
                        else:
                            return f"Failed to log work: {result.get('error', 'Unknown error')}"
                
                # Check if it's a task update request
                elif any(keyword in task_lower for keyword in ['update', 'change', 'modify', 'set', 'mark']) and \
                     not any(keyword in task_lower for keyword in ['add', 'new', 'create', 'schedule']):
                    # This is likely an update request
                    result = update_task(task)
                    if result.get("success"):
                        return result["message"]
                    else:
                        return f"Failed to update task: {result.get('error', 'Unknown error')}"
                
                # Check if it's a removal request
                elif any(keyword in task_lower for keyword in ['remove task', 'delete task', 'cancel task']):
                    task_id_match = re.search(r'\b([A-Z]+-\d+)\b', task)
                    if not task_id_match:
                        return "Could not find task ID. Please specify a task ID like 'TASK-1'"
                    
                    task_id = task_id_match.group(1)
                    result = remove_task(task_id)
                    return result.get("message", result.get("error", "Unknown result"))
                
                elif any(keyword in task_lower for keyword in ['remove meeting', 'delete meeting', 'cancel meeting']):
                    meeting_query = task
                    for prefix in ['remove meeting:', 'delete meeting:', 'cancel meeting:', 'remove meeting', 'delete meeting', 'cancel meeting']:
                        if prefix in task_lower:
                            idx = task_lower.find(prefix) + len(prefix)
                            meeting_query = task[idx:].strip()
                            if meeting_query.startswith(':'):
                                meeting_query = meeting_query[1:].strip()
                            break
                    
                    result = remove_meeting(meeting_query)
                    return result.get("message", result.get("error", "Unknown result"))
                
                elif any(keyword in task_lower for keyword in ['remove log', 'delete log']):
                    task_id_match = re.search(r'\b([A-Z]+-\d+)\b', task)
                    task_id = task_id_match.group(1) if task_id_match else None
                    
                    result = remove_daily_log(task, task_id)
                    return result.get("message", result.get("error", "Unknown result"))
                
                # Check if it's a planning request
                elif any(keyword in task_lower for keyword in ['plan', 'schedule', 'agenda', 'what to do', 'what should i do']):
                    # Extract date from the query
                    target_date = date.today()  # default
                    
                    if "tomorrow" in task_lower:
                        target_date = date.today() + timedelta(days=1)
                    elif "yesterday" in task_lower:
                        target_date = date.today() - timedelta(days=1)
                    elif "next week" in task_lower:
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
                    return "I couldn't understand what planning action you want. Try 'add task:', 'schedule meeting:', or 'log work:'"
                    
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