#!/usr/bin/env python3
"""Test calendar parsing through the primary agent."""
import asyncio
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
from src.core.config import get_settings
from src.agents.primary import PrimaryAgent
from src.agents.brave_search import BraveSearchAgent
from src.agents.filesystem import FilesystemAgent
from src.agents.rag import RAGAgent

async def test_calendar_parsing():
    """Test the calendar parsing functionality."""
    settings = get_settings()
    provider = OpenAIProvider(base_url=settings.base_url, api_key=settings.llm_api_key)
    model = OpenAIModel(settings.model_choice, provider=provider)
    
    # Initialize agents
    agents = {
        "brave_search": BraveSearchAgent(model),
        "filesystem": FilesystemAgent(model),
        "rag": RAGAgent(model),
    }
    
    primary_agent = PrimaryAgent(model, agents)
    
    # Test parsing calendar events
    queries = [
        "parse calendar events for this week",
        "parse calendar events for today",
        "parse calendar events for next week"
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        
        result = await primary_agent.run(query)
        print(result.data)

if __name__ == "__main__":
    asyncio.run(test_calendar_parsing())