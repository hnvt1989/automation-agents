"""Enhanced planner agent with Supabase backend support."""

from typing import Optional, Dict, Any
from pydantic import BaseModel
from pydantic_ai import Agent
from datetime import datetime, timedelta
import os

from src.storage.supabase_ops import SupabaseOperations
from src.utils.logging import log_info, log_error, log_warning
from src.core.config import get_model


class PlannerRequest(BaseModel):
    """Model for planner request parameters."""
    action: str  # create_task, update_task, remove_task, create_log, etc.
    data: Dict[str, Any]


class PlannerSupabaseAgent:
    """Planner agent that uses Supabase for storage."""
    
    def __init__(self):
        """Initialize the planner agent with Supabase operations."""
        self.ops = SupabaseOperations()
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """Create the planner agent."""
        agent = Agent(
            model=get_model(),
            system_prompt="""You are a task planning assistant with Supabase database backend.
            
Your capabilities:
- Create, update, and remove tasks in Supabase
- Log work entries with time tracking
- Query and filter tasks by various criteria
- Manage task dependencies and relationships

When responding:
- Be concise and action-oriented
- Confirm successful operations
- Provide helpful error messages if operations fail
- Suggest next steps when appropriate

Database schema:
- Tasks: id, title, description, status, priority, due_date, tags, estimate_hours, todo
- Logs: id, log_date, log_id, description, actual_hours, task_id

All data is stored in Supabase for real-time sync and scalability.""",
            deps_type=PlannerRequest,
        )
        
        @agent.tool
        def create_task(ctx, title: str, priority: str = "medium", due_date: Optional[str] = None, 
                       description: Optional[str] = None, tags: Optional[list] = None) -> str:
            """Create a new task in Supabase."""
            task_data = {
                "title": title,
                "priority": priority,
                "due_date": due_date or (datetime.now().date() + timedelta(weeks=1)).isoformat(),
                "description": description,
                "tags": tags or []
            }
            
            result = self.ops.add_task(task_data)
            
            if result["success"]:
                task = result["task"]
                return f"✅ Created task '{task['title']}' (ID: {task['id']}) with {priority} priority, due {task['due_date']}"
            else:
                return f"❌ Failed to create task: {result['error']}"
        
        @agent.tool
        def update_task(ctx, identifier: str, **updates) -> str:
            """Update an existing task in Supabase."""
            result = self.ops.update_task(identifier, updates)
            
            if result["success"]:
                task = result["task"]
                changes = result.get("changes", [])
                return f"✅ Updated task '{task['title']}': {', '.join(changes)}"
            else:
                return f"❌ Failed to update task: {result['error']}"
        
        @agent.tool
        def remove_task(ctx, identifier: str) -> str:
            """Remove a task from Supabase."""
            result = self.ops.remove_task(identifier)
            
            if result["success"]:
                return f"✅ {result['message']}"
            else:
                return f"❌ Failed to remove task: {result['error']}"
        
        @agent.tool
        def list_tasks(ctx, status: Optional[str] = None, priority: Optional[str] = None) -> str:
            """List tasks from Supabase with optional filters."""
            all_tasks = self.ops.get_all_tasks()
            
            # Apply filters
            tasks = all_tasks
            if status:
                tasks = [t for t in tasks if t.get("status") == status]
            if priority:
                tasks = [t for t in tasks if t.get("priority") == priority]
            
            if not tasks:
                return "No tasks found matching the criteria."
            
            # Group by status
            by_status = {}
            for task in tasks:
                status = task.get("status", "unknown")
                if status not in by_status:
                    by_status[status] = []
                by_status[status].append(task)
            
            output = []
            for status, status_tasks in by_status.items():
                output.append(f"\n**{status.upper()}** ({len(status_tasks)} tasks):")
                for task in status_tasks:
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.get("priority"), "⚪")
                    output.append(f"{priority_emoji} [{task['id']}] {task['title']} (due: {task.get('due_date', 'N/A')})")
            
            return "\n".join(output)
        
        @agent.tool
        def create_log(ctx, description: str, hours: float, date: Optional[str] = None, task_id: Optional[str] = None) -> str:
            """Create a work log entry in Supabase."""
            log_data = {
                "description": description,
                "hours": hours,
                "date": date or datetime.now().date().isoformat(),
                "task_id": task_id
            }
            
            result = self.ops.add_log(log_data)
            
            if result["success"]:
                log = result["log"]
                return f"✅ Logged {hours} hours: '{description}' on {result['date']}"
            else:
                return f"❌ Failed to create log: {result['error']}"
        
        @agent.tool
        def list_logs(ctx, date: Optional[str] = None) -> str:
            """List work logs from Supabase."""
            if date:
                logs = self.ops.get_logs_by_date(date)
                header = f"Work logs for {date}:"
            else:
                logs = self.ops.get_all_logs()
                header = "Recent work logs:"
            
            if not logs:
                return "No logs found."
            
            output = [header]
            total_hours = 0
            
            for log in logs[:20]:  # Show max 20 logs
                hours = log.get("actual_hours", 0)
                total_hours += hours
                output.append(f"• {log['log_date']} - {log['description'][:60]}... ({hours}h)")
            
            output.append(f"\nTotal: {total_hours} hours")
            
            return "\n".join(output)
        
        @agent.tool
        def create_task_and_log(ctx, description: str, hours: float) -> str:
            """Create a task and immediately log work against it."""
            result = self.ops.create_task_and_log(description, hours)
            
            if result["success"]:
                return f"✅ {result['message']}"
            else:
                return f"❌ Failed: {result['error']}"
        
        return agent
    
    async def handle_request(self, request: str) -> str:
        """Handle a planning request."""
        try:
            # Check if Supabase is configured
            if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
                return "❌ Supabase not configured. Please set SUPABASE_URL and SUPABASE_KEY in your environment."
            
            result = await self.agent.run(request)
            return result.data
        except Exception as e:
            log_error(f"Error in planner request: {str(e)}")
            return f"Error processing request: {str(e)}"