"""LLM-based parser for planner commands."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
import json
from datetime import datetime, date, timedelta
import re

from src.utils.logging import log_info, log_error


class PlannerRequest(BaseModel):
    """Structured planner request parsed from natural language."""
    action: str = Field(description="The action to perform")
    data: Dict[str, Any] = Field(description="The data for the action")


PARSER_SYSTEM_PROMPT = """You are a natural language parser for a task management system. 
Parse user requests into structured JSON format.

Available actions:
- add_task: Add a new task
- update_task: Update an existing task
- remove_task: Remove a task
- add_meeting: Schedule a meeting
- remove_meeting: Cancel a meeting
- list_meetings: List meetings for a specific date
- add_log: Log work done
- remove_log: Remove a work log
- plan_day: Generate daily plan
- list_tasks: List all tasks
- find_task: Find tasks by partial title match
- search_tasks: Search tasks by keyword
- brainstorm_task: Generate brainstorm for a task using RAG and AI

Date parsing:
- "today" -> current date
- "tomorrow" -> next day
- "next week" -> 7 days from now
- "next Monday" -> next Monday
- "in X days" -> X days from now

Examples:

Input: "add task 'job search' with high priority"
Output: {"action": "add_task", "data": {"title": "job search", "priority": "high"}}

Input: "add task with id 106264 description 'Document test scenarios' priority high"
Output: {"action": "add_task", "data": {"id": "106264", "title": "Document test scenarios", "priority": "high"}}

Input: "add task 'research project' with tag 'work' and high priority"  
Output: {"action": "add_task", "data": {"title": "research project", "tags": ["work"], "priority": "high"}}

Input: "change status of job search to in progress"
Output: {"action": "update_task", "data": {"identifier": "job search", "updates": {"status": "in_progress"}}}

Input: "update TASK-1 priority to high"
Output: {"action": "update_task", "data": {"identifier": "TASK-1", "updates": {"priority": "high"}}}

Input: "add a daily log 'research automated test analysis' took 2 hours"
Output: {"action": "add_log", "data": {"description": "research automated test analysis", "hours": 2}}

Input: "log 3 hours on TASK-1 implementing the API"
Output: {"action": "add_log", "data": {"log_id": "TASK-1", "description": "implementing the API", "hours": 3}}

Input: "schedule meeting team standup tomorrow at 10am"
Output: {"action": "add_meeting", "data": {"title": "team standup", "date": "tomorrow", "time": "10:00"}}

Input: "do I have meetings tomorrow?"
Output: {"action": "list_meetings", "data": {"date": "tomorrow"}}

Input: "what meetings do I have today?"
Output: {"action": "list_meetings", "data": {"date": "today"}}

Input: "show me my meetings for next Monday"
Output: {"action": "list_meetings", "data": {"date": "next Monday"}}

Input: "check for meetings scheduled for tomorrow"
Output: {"action": "list_meetings", "data": {"date": "tomorrow"}}

Input: "get meetings for 6/11"
Output: {"action": "list_meetings", "data": {"date": "6/11"}}

Input: "get meetings for wednesday"
Output: {"action": "list_meetings", "data": {"date": "wednesday"}}

Input: "meetings on 12/25"
Output: {"action": "list_meetings", "data": {"date": "12/25"}}

Input: "meetings for June 11"
Output: {"action": "list_meetings", "data": {"date": "June 11"}}

Input: "remove task TASK-1"
Output: {"action": "remove_task", "data": {"identifier": "TASK-1"}}

Input: "plan for tomorrow"
Output: {"action": "plan_day", "data": {"date": "tomorrow"}}

Input: "mark task TASK-1 as completed"
Output: {"action": "update_task", "data": {"identifier": "TASK-1", "updates": {"status": "completed"}}}

Input: "add tags urgent, personal to job search task"
Output: {"action": "update_task", "data": {"identifier": "job search", "updates": {"add_tags": ["urgent", "personal"]}}}

Input: "list all tasks"
Output: {"action": "list_tasks", "data": {}}

Input: "find task with title including 'test scenarios'"
Output: {"action": "find_task", "data": {"title": "test scenarios"}}

Input: "search for tasks containing 'documentation'"
Output: {"action": "search_tasks", "data": {"query": "documentation"}}

Input: "brainstorm task 111025"
Output: {"action": "brainstorm_task", "data": {"task_id": "111025"}}

Input: "brainstorm task with title job search"
Output: {"action": "brainstorm_task", "data": {"task_title": "job search"}}

Input: "improve brainstorm for task ONBOARDING-1"
Output: {"action": "brainstorm_task", "data": {"task_id": "ONBOARDING-1", "force_regenerate": true}}

Always return valid JSON with "action" and "data" fields.
For update_task, use "identifier" for task ID or title, and "updates" for changes.
CRITICAL DATE HANDLING: You MUST preserve the EXACT natural language as given by the user. 
- If user says "6/11", output "6/11" (NOT "2025-06-11", "2025-06-16", or any ISO format)
- If user says "wednesday", output "wednesday" (NOT "2025-06-11")
- If user says "tomorrow", output "tomorrow" (NOT "2025-06-10")
- NEVER convert, calculate, or interpret dates - keep them exactly as typed
- WRONG: {"date": "2025-06-16"} for input "6/11"
- CORRECT: {"date": "6/11"} for input "6/11"
"""


class PlannerParser:
    """Parser for converting natural language to structured planner commands."""
    
    def __init__(self, model: OpenAIModel):
        """Initialize the parser with an OpenAI model."""
        self.agent = Agent(
            model,
            system_prompt=PARSER_SYSTEM_PROMPT,
            result_type=str
        )
    
    async def parse(self, query: str) -> Dict[str, Any]:
        """Parse a natural language query into a structured command.
        
        Args:
            query: Natural language query
            
        Returns:
            Dict with 'action' and 'data' fields
        """
        try:
            log_info(f"Parsing planner query: {query}")
            
            # Get the LLM to parse the query
            result = await self.agent.run(query)
            parsed_json = result.data
            
            # Parse the JSON response
            try:
                parsed = json.loads(parsed_json)
            except json.JSONDecodeError as e:
                log_error(f"Failed to parse LLM response as JSON: {parsed_json}")
                return {"action": "error", "data": {"message": "Failed to understand the request"}}
            
            # Validate the response structure
            if "action" not in parsed or "data" not in parsed:
                log_error(f"Invalid response structure: {parsed}")
                return {"action": "error", "data": {"message": "Invalid response from parser"}}
            
            # Fix incorrect date conversions by LLM
            self._fix_date_conversions(parsed, query)
            
            # Post-process dates if present (only for actions that need ISO dates)
            if parsed["action"] not in ["list_meetings"]:
                parsed["data"] = self._process_dates(parsed["data"])
            
            # Post-process times if present
            parsed["data"] = self._process_times(parsed["data"])
            
            log_info(f"Parsed result: {parsed}")
            return parsed
            
        except Exception as e:
            log_error(f"Error parsing query: {str(e)}")
            return {"action": "error", "data": {"message": str(e)}}
    
    def _fix_date_conversions(self, parsed: Dict[str, Any], original_query: str) -> None:
        """Fix incorrect date conversions by the LLM."""
        import re
        
        # Only fix list_meetings actions
        if parsed.get("action") != "list_meetings":
            return
            
        data = parsed.get("data", {})
        if "date" not in data:
            return
            
        llm_date = data["date"]
        
        # Extract date patterns from the original query
        date_patterns = [
            r'\b(\d{1,2})/(\d{1,2})\b',           # 6/11, 12/25
            r'\b(\d{1,2})-(\d{1,2})\b',           # 6-11, 12-25  
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',  # weekdays
            r'\b(today|tomorrow|yesterday)\b',     # relative dates
        ]
        
        found_dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, original_query.lower())
            found_dates.extend(matches)
        
        # If we found date patterns in the original query, check if LLM corrupted them
        if found_dates:
            # Check for MM/DD patterns
            mm_dd_match = re.search(r'\b(\d{1,2})/(\d{1,2})\b', original_query)
            if mm_dd_match:
                month, day = mm_dd_match.groups()
                original_date = f"{month}/{day}"
                
                # If LLM converted MM/DD to something else, revert it
                if llm_date != original_date and re.match(r'\d{4}-\d{2}-\d{2}', llm_date):
                    log_info(f"Fixing incorrect date conversion: '{original_date}' was converted to '{llm_date}', reverting to '{original_date}'")
                    data["date"] = original_date
                    return
            
            # Check for weekdays
            weekday_match = re.search(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', original_query.lower())
            if weekday_match:
                weekday = weekday_match.group(1)
                
                # If LLM converted weekday to ISO date, revert it
                if llm_date != weekday and re.match(r'\d{4}-\d{2}-\d{2}', llm_date):
                    log_info(f"Fixing incorrect date conversion: '{weekday}' was converted to '{llm_date}', reverting to '{weekday}'")
                    data["date"] = weekday
                    return
    
    def _process_dates(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert natural language dates to ISO format."""
        date_fields = ["date", "due_date", "deadline"]
        
        for field in date_fields:
            if field in data and isinstance(data[field], str):
                parsed_date = self._parse_date(data[field])
                if parsed_date:
                    data[field] = parsed_date.isoformat()
        
        return data
    
    def _process_times(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert natural language times to HH:MM format."""
        if "time" in data and isinstance(data["time"], str):
            parsed_time = self._parse_time(data["time"])
            if parsed_time:
                data["time"] = parsed_time
        
        return data
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse natural language date to date object."""
        date_str = date_str.lower().strip()
        today = date.today()
        
        if date_str == "today":
            return today
        elif date_str == "tomorrow":
            return today + timedelta(days=1)
        elif date_str == "yesterday":
            return today - timedelta(days=1)
        elif date_str == "next week":
            return today + timedelta(weeks=1)
        elif date_str == "next monday":
            days_ahead = 0 - today.weekday()  # Monday is 0
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        
        # Try "in X days" pattern
        days_match = re.match(r"in (\d+) days?", date_str)
        if days_match:
            return today + timedelta(days=int(days_match.group(1)))
        
        # Try ISO format
        try:
            return datetime.fromisoformat(date_str).date()
        except ValueError:
            pass
        
        # Try MM/DD/YYYY format
        try:
            return datetime.strptime(date_str, "%m/%d/%Y").date()
        except ValueError:
            pass
        
        # Default to next week if can't parse
        return today + timedelta(weeks=1)
    
    def _parse_time(self, time_str: str) -> Optional[str]:
        """Parse natural language time to HH:MM format."""
        time_str = time_str.lower().strip()
        
        # Handle already formatted times
        if re.match(r'^\d{1,2}:\d{2}$', time_str):
            return time_str
        
        # Handle times with am/pm
        match = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$', time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            ampm = match.group(3)
            
            if ampm == 'pm' and hour != 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
            
            return f"{hour:02d}:{minute:02d}"
        
        # Handle named times
        named_times = {
            "morning": "09:00",
            "noon": "12:00",
            "afternoon": "14:00",
            "evening": "18:00",
            "night": "20:00"
        }
        
        if time_str in named_times:
            return named_times[time_str]
        
        # Default to 10:00
        return "10:00"