"""Primary orchestration agent."""
from typing import Dict, Any, Optional, List
from datetime import date, timedelta
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
        async def crawl_and_index_website(
            ctx: RunContext[PrimaryAgentDeps], 
            url: str,
            sitemap_url: str = None
        ) -> str:
            """Crawl and index a website's content for search and retrieval.
            
            Use this to:
            - Scrape website content and add it to the knowledge base
            - Index documentation sites for later search
            - Process multiple pages from a sitemap
            """
            log_info(f"Crawling and indexing website: {url}")
            try:
                from src.processors.crawler import run_crawler
                from src.storage.chromadb_client import get_chromadb_client
                from src.storage.collection_manager import CollectionManager
                
                # Get ChromaDB client and collection manager
                chromadb_client = get_chromadb_client()
                collection_manager = CollectionManager(chromadb_client)
                
                # Get or create the websites collection
                try:
                    websites_collection = chromadb_client.get_collection("automation_agents_websites")
                except Exception:
                    # Create collection if it doesn't exist
                    websites_collection = chromadb_client.create_collection("automation_agents_websites")
                
                # Prepare URLs to crawl
                urls_to_crawl = [url]
                
                # Run the crawler
                await run_crawler(
                    urls_to_crawl=urls_to_crawl,
                    chroma_collection=websites_collection,
                    max_concurrent_crawls=3,
                    sitemap_url=sitemap_url
                )
                
                return f"Successfully crawled and indexed {url}. Content is now available for search through the RAG agent."
                
            except Exception as e:
                log_error(f"Error crawling website {url}: {str(e)}")
                return f"Error crawling website: {str(e)}"
        
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
                
                elif action == "list_meetings":
                    # Parse the date
                    date_str = data.get("date", "today")
                    target_date = self._parse_date(date_str)
                    
                    # Load meetings
                    meetings_path = ops.paths.get("meets", "data/meetings.yaml")
                    try:
                        with open(meetings_path, "r", encoding="utf-8") as f:
                            import yaml
                            meetings = yaml.safe_load(f) or []
                    except Exception as e:
                        return f"Error loading meetings: {str(e)}"
                    
                    # Filter meetings for target date
                    from src.agents.planner import _get_target_date_meetings
                    target_meetings = _get_target_date_meetings(meetings, target_date)
                    
                    if target_meetings:
                        meeting_list = "\n".join(f"- {meeting}" for meeting in target_meetings)
                        today_date = date.today()
                        tomorrow_date = today_date + timedelta(days=1)
                        date_display = "today" if target_date == today_date else "tomorrow" if target_date == tomorrow_date else str(target_date)
                        return f"Meetings for {date_display}:\n\n{meeting_list}"
                    else:
                        today_date = date.today()
                        tomorrow_date = today_date + timedelta(days=1)
                        date_display = "today" if target_date == today_date else "tomorrow" if target_date == tomorrow_date else str(target_date)
                        return f"No meetings scheduled for {date_display}."
                
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
                
                elif action == "list_tasks" or action == "get_tasks":
                    # List all tasks
                    from src.agents.planner_ops import load_yaml
                    try:
                        tasks = load_yaml('data/tasks.yaml') or []
                        if not tasks:
                            return "No tasks found."
                        
                        task_list = []
                        for task in tasks:
                            status = task.get('status', 'pending')
                            priority = task.get('priority', 'medium')
                            title = task.get('title', 'Untitled')
                            task_id = task.get('id', 'Unknown')
                            task_list.append(f"- {task_id}: {title} ({status}, {priority} priority)")
                        
                        return f"Current tasks:\n" + "\n".join(task_list)
                    except Exception as e:
                        return f"Error loading tasks: {str(e)}"
                
                elif action == "find_task" or action == "search_tasks":
                    # Enhanced task search with LLM option
                    from src.agents.planner_ops import load_yaml
                    try:
                        tasks = load_yaml('data/tasks.yaml') or []
                        search_query = data.get('title', data.get('query', '')).lower()
                        
                        if not search_query:
                            return "No search query provided."
                        
                        # Determine if we should use LLM for complex queries
                        use_llm = self._should_use_llm_search(search_query)
                        
                        if use_llm:
                            # Use LLM for sophisticated search
                            matches = await self._llm_search_tasks(tasks, search_query)
                        else:
                            # Use traditional keyword search
                            matches = self._keyword_search_tasks(tasks, search_query)
                        
                        if matches:
                            search_type = "LLM-powered" if use_llm else "keyword"
                            return f"Tasks matching '{search_query}' ({search_type} search):\n" + "\n".join(matches)
                        else:
                            return f"No tasks found matching '{search_query}'"
                    except Exception as e:
                        return f"Error searching tasks: {str(e)}"
                
                elif action == "brainstorm_task":
                    # Handle task brainstorming
                    try:
                        from src.agents.planner import brainstorm_task
                        
                        # Construct query for brainstorm function
                        if "task_id" in data:
                            query = f"brainstorm task id {data['task_id']}"
                        elif "task_title" in data:
                            query = f"brainstorm task title {data['task_title']}"
                        else:
                            return "No task ID or title provided for brainstorming"
                        
                        # Check if force regenerate is requested
                        if data.get("force_regenerate", False):
                            query = f"improve {query}"
                        
                        result = await brainstorm_task(query)
                        
                        if result.get('success'):
                            content = result.get('content', '')
                            individual_file = result.get('individual_file')
                            newly_generated = result.get('newly_generated', False)
                            
                            response = content
                            if individual_file:
                                response += f"\n\n📝 **Brainstorm saved to:** `{individual_file}`"
                            if newly_generated:
                                response += "\n\n✨ **New brainstorm generated using RAG and AI analysis**"
                            else:
                                response += "\n\n📄 **Loaded existing brainstorm**"
                            
                            return response
                        else:
                            return f"Failed to generate brainstorm: {result.get('error')}"
                    
                    except Exception as e:
                        return f"Error generating brainstorm: {str(e)}"
                
                else:
                    return f"Unknown action: {action}"
                    
            except Exception as e:
                log_error(f"Error in planner task: {str(e)}")
                return f"Error: {str(e)}"
    
    def _parse_date(self, date_str: str) -> date:
        """Parse a date string like 'today', 'tomorrow', etc. into a date object."""
        today = date.today()
        
        if date_str.lower() in ["today"]:
            return today
        elif date_str.lower() in ["tomorrow"]:
            return today + timedelta(days=1)
        elif date_str.lower() in ["yesterday"]:
            return today - timedelta(days=1)
        else:
            # Try to parse as ISO date
            try:
                from datetime import datetime
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                # Default to today if we can't parse
                return today
    
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

    async def run_stream(self, prompt: str, **kwargs):
        """Run the primary agent in streaming mode."""
        deps = PrimaryAgentDeps(
            agents=self.agents,
            query=prompt,
            debug=kwargs.get("debug", False)
        )

        async for delta in super().run_stream(prompt, deps=deps, **kwargs):
            yield delta
    
    def _should_use_llm_search(self, query: str) -> bool:
        """Determine if we should use LLM for search based on query complexity."""
        # Use LLM for complex queries that involve:
        # - Natural language questions
        # - Comparisons or conditions
        # - Multiple criteria
        # - Fuzzy matching needs
        
        llm_indicators = [
            "how many", "count", "list all", "show me", "find tasks that",
            "tasks with", "highest", "lowest", "most", "least", "urgent",
            "overdue", "due soon", "completed", "in progress", "pending",
            "similar to", "like", "related to", "about", "containing"
        ]
        
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in llm_indicators)
    
    def _keyword_search_tasks(self, tasks: List[Dict], search_query: str) -> List[str]:
        """Enhanced keyword search across all task fields."""
        matches = []
        
        for task in tasks:
            # Get all searchable fields
            title = task.get('title', '').lower()
            description = task.get('description', '').lower()  # If tasks have description
            priority = task.get('priority', '').lower()
            status = task.get('status', '').lower()
            tags = task.get('tags', [])
            task_id = str(task.get('id', '')).lower()
            
            # Check if query matches any field
            title_match = search_query in title
            desc_match = search_query in description
            priority_match = search_query in priority
            status_match = search_query in status
            id_match = search_query in task_id
            tag_match = any(search_query in str(tag).lower() for tag in tags)
            
            if any([title_match, desc_match, priority_match, status_match, id_match, tag_match]):
                # Format the task for display
                status_display = task.get('status', 'pending')
                priority_display = task.get('priority', 'medium')
                task_id_display = task.get('id', 'Unknown')
                tags_str = f" [tags: {', '.join(str(tag) for tag in tags)}]" if tags else ""
                
                match_info = []
                if title_match:
                    match_info.append("title")
                if desc_match:
                    match_info.append("description")
                if priority_match:
                    match_info.append("priority")
                if status_match:
                    match_info.append("status")
                if id_match:
                    match_info.append("ID")
                if tag_match:
                    match_info.append("tags")
                
                match_fields = f" (matched: {', '.join(match_info)})" if match_info else ""
                matches.append(f"- {task_id_display}: {task.get('title', 'Untitled')} ({status_display}, {priority_display} priority){tags_str}{match_fields}")
        
        return matches
    
    async def _llm_search_tasks(self, tasks: List[Dict], search_query: str) -> List[str]:
        """Use LLM to perform sophisticated task search."""
        try:
            # Prepare task data for LLM
            task_summaries = []
            for i, task in enumerate(tasks):
                summary = f"{i}: {task.get('id', 'Unknown')} - {task.get('title', 'Untitled')} "
                summary += f"(status: {task.get('status', 'pending')}, priority: {task.get('priority', 'medium')}"
                
                if task.get('tags'):
                    summary += f", tags: {', '.join(str(tag) for tag in task.get('tags', []))}"
                
                if task.get('due_date'):
                    summary += f", due: {task.get('due_date')}"
                
                if task.get('description'):
                    summary += f", description: {task.get('description')}"
                
                summary += ")"
                task_summaries.append(summary)
            
            # Create LLM prompt for search
            prompt = f"""Given this list of tasks:

{chr(10).join(task_summaries)}

User query: "{search_query}"

Please identify which tasks match the user's query. Consider:
- Semantic meaning, not just exact keywords
- Task content, priority, status, tags, and context
- Natural language understanding

Return ONLY the task indices (numbers) that match, separated by commas. For example: "1,3,5" or "0" or "none" if no matches.

Task indices:"""

            # Use LLM to find matches
            from pydantic_ai import Agent
            search_agent = Agent(
                self.model,
                system_prompt="You are a task search assistant. You help find tasks based on natural language queries by understanding semantic meaning and context."
            )
            
            result = await search_agent.run(prompt)
            indices_text = str(result.data).strip().lower()
            
            # Parse the result
            matches = []
            if indices_text and indices_text != "none":
                try:
                    # Extract indices
                    indices = [int(x.strip()) for x in indices_text.split(',') if x.strip().isdigit()]
                    
                    for idx in indices:
                        if 0 <= idx < len(tasks):
                            task = tasks[idx]
                            status_display = task.get('status', 'pending')
                            priority_display = task.get('priority', 'medium')
                            task_id_display = task.get('id', 'Unknown')
                            tags = task.get('tags', [])
                            tags_str = f" [tags: {', '.join(str(tag) for tag in tags)}]" if tags else ""
                            
                            matches.append(f"- {task_id_display}: {task.get('title', 'Untitled')} ({status_display}, {priority_display} priority){tags_str}")
                
                except (ValueError, IndexError) as e:
                    # Fall back to keyword search if LLM parsing fails
                    log_error(f"LLM search result parsing failed: {str(e)}, falling back to keyword search")
                    return self._keyword_search_tasks(tasks, search_query)
            
            return matches
            
        except Exception as e:
            log_error(f"LLM search failed: {str(e)}, falling back to keyword search")
            # Fall back to keyword search if LLM fails
            return self._keyword_search_tasks(tasks, search_query)