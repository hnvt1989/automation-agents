"""
Core functions for the Telegram bot agent.
Simplified version of agents.py without MCP dependencies.
"""
from __future__ import annotations
from typing import Optional
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel

# Load environment for local testing (Vercel will use its own env vars)
load_dotenv('local.env')


def get_telegram_model():
    """
    Get model configuration for Telegram bot.
    Simplified version without logging dependencies.
    """
    llm = os.getenv('MODEL_CHOICE', 'gpt-4o-mini')
    base_url = os.getenv('BASE_URL', 'https://api.openai.com/v1')
    api_key = os.getenv('LLM_API_KEY', 'no-api-key-provided')
    
    return OpenAIModel(llm, provider=OpenAIProvider(base_url=base_url, api_key=api_key))


def create_telegram_agent() -> Agent:
    """
    Create a simplified agent for Telegram without MCP servers.
    """
    system_prompt = """You are a helpful AI assistant accessible through Telegram. 
You can help with:
- General questions and conversations
- Basic planning and scheduling advice
- Text analysis and processing
- Information synthesis and explanations

You should:
- Be concise and clear in your responses
- Provide helpful and accurate information
- Be friendly and conversational
- Keep responses under 4000 characters for Telegram compatibility

Note: You don't have access to web search, file systems, or external integrations in this interface."""
    
    model = get_telegram_model()
    return Agent(model=model, system_prompt=system_prompt)


async def process_telegram_message(text: str) -> str:
    """
    Process a message from Telegram and return a response.
    
    Args:
        text: The user's message text
        
    Returns:
        The agent's response (limited to 4096 characters)
    """
    try:
        # Create agent instance
        agent = create_telegram_agent()
        
        # Check if this is a planning-related query
        if is_planning_query(text):
            # Extract date context and add it to the query
            date_context = extract_date_from_query(text)
            enhanced_query = f"{text}\n\n(Context: The user is asking about {date_context})"
            result = await agent.run(enhanced_query)
        else:
            # Regular query
            result = await agent.run(text)
        
        # Get the response and ensure it's within Telegram's limit
        response = result.data
        if len(response) > 4096:
            response = response[:4093] + "..."
            
        return response
        
    except Exception as e:
        # Return a user-friendly error message
        return f"I apologize, but I encountered an error processing your request. Please try again or rephrase your question."


def extract_date_from_query(query: str) -> str:
    """
    Extract date context from user queries.
    Copied from agents.py for consistency.
    
    Args:
        query: The user's query string
        
    Returns:
        A date string that can be parsed by the planner agent
    """
    query_lower = query.lower().strip()
    
    # Direct date references
    if "tomorrow" in query_lower:
        return "tomorrow"
    elif "yesterday" in query_lower:
        return "yesterday"
    elif "today" in query_lower:
        return "today"
    elif "next week" in query_lower:
        return "next week"
    elif "next monday" in query_lower:
        return "next monday"
    elif "this week" in query_lower:
        return "this week"
    elif "this monday" in query_lower:
        return "this monday"
    
    # Try to find ISO date patterns (YYYY-MM-DD)
    iso_date_pattern = r'\b(\d{4}-\d{2}-\d{2})\b'
    iso_match = re.search(iso_date_pattern, query)
    if iso_match:
        return iso_match.group(1)
    
    # Try to find other common date patterns
    # MM/DD/YYYY or MM-DD-YYYY
    us_date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b'
    us_match = re.search(us_date_pattern, query)
    if us_match:
        # Convert to ISO format if needed
        date_str = us_match.group(1)
        try:
            if '/' in date_str:
                parsed_date = datetime.strptime(date_str, '%m/%d/%Y')
            else:
                parsed_date = datetime.strptime(date_str, '%m-%d-%Y')
            return parsed_date.date().isoformat()
        except ValueError:
            pass
    
    # Default to today if no date context found
    return "today"


def is_planning_query(query: str) -> bool:
    """
    Determine if a query is related to planning/scheduling.
    
    Args:
        query: The user's query string
        
    Returns:
        True if the query appears to be planning-related
    """
    query_lower = query.lower()
    
    # Keywords that indicate planning queries
    planning_keywords = [
        'plan', 'schedule', 'calendar', 'meeting', 'appointment',
        'today', 'tomorrow', 'yesterday', 'week', 'monday', 'tuesday',
        'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
        'morning', 'afternoon', 'evening', 'night',
        'what should i', 'what do i have', 'when is', 'when should',
        'remind me', 'todo', 'task', 'deadline', 'due'
    ]
    
    return any(keyword in query_lower for keyword in planning_keywords)


def basic_planning_response(query: str, date_context: str) -> str:
    """
    Provide a basic planning response without full planner agent.
    This is a fallback for when we can't use the full planner.
    
    Args:
        query: The user's query
        date_context: The extracted date context
        
    Returns:
        A helpful planning-related response
    """
    return f"""I understand you're asking about planning for {date_context}.

While I don't have access to your calendar or specific schedule information through Telegram, I can help you:
- Think through your priorities
- Suggest time management strategies
- Help organize your tasks
- Provide general scheduling advice

What specific aspect of planning would you like help with?"""