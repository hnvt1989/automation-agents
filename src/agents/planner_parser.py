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
- add_log: Log work done
- remove_log: Remove a work log
- plan_day: Generate daily plan

Date parsing:
- "today" -> current date
- "tomorrow" -> next day
- "next week" -> 7 days from now
- "next Monday" -> next Monday
- "in X days" -> X days from now

Examples:

Input: "add task 'job search' with high priority"
Output: {"action": "add_task", "data": {"title": "job search", "priority": "high"}}

Input: "change status of job search to in progress"
Output: {"action": "update_task", "data": {"identifier": "job search", "updates": {"status": "in_progress"}}}

Input: "update TASK-1 priority to high"
Output: {"action": "update_task", "data": {"identifier": "TASK-1", "updates": {"priority": "high"}}}

Input: "add a daily log 'research automated test analysis' took 2 hours"
Output: {"action": "add_log", "data": {"description": "research automated test analysis", "hours": 2}}

Input: "log 3 hours on TASK-1 implementing the API"
Output: {"action": "add_log", "data": {"task_id": "TASK-1", "description": "implementing the API", "hours": 3}}

Input: "schedule meeting team standup tomorrow at 10am"
Output: {"action": "add_meeting", "data": {"title": "team standup", "date": "tomorrow", "time": "10:00"}}

Input: "remove task TASK-1"
Output: {"action": "remove_task", "data": {"identifier": "TASK-1"}}

Input: "plan for tomorrow"
Output: {"action": "plan_day", "data": {"date": "tomorrow"}}

Input: "mark task TASK-1 as completed"
Output: {"action": "update_task", "data": {"identifier": "TASK-1", "updates": {"status": "completed"}}}

Input: "add tags urgent, personal to job search task"
Output: {"action": "update_task", "data": {"identifier": "job search", "updates": {"add_tags": ["urgent", "personal"]}}}

Always return valid JSON with "action" and "data" fields.
For update_task, use "identifier" for task ID or title, and "updates" for changes.
For dates, preserve the natural language (e.g., "tomorrow") - we'll parse it later.
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
            
            # Post-process dates if present
            parsed["data"] = self._process_dates(parsed["data"])
            
            # Post-process times if present
            parsed["data"] = self._process_times(parsed["data"])
            
            log_info(f"Parsed result: {parsed}")
            return parsed
            
        except Exception as e:
            log_error(f"Error parsing query: {str(e)}")
            return {"action": "error", "data": {"message": str(e)}}
    
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