"""Tests for the LLM-based planner parser."""

import pytest
from unittest.mock import Mock, AsyncMock
from src.agents.planner_parser import PlannerParser, PlannerRequest
from datetime import date, timedelta
import json


@pytest.fixture
def test_model():
    """Create a test model."""
    from pydantic_ai.models.test import TestModel
    return TestModel()


@pytest.fixture
def parser(test_model):
    """Create a parser instance with test model."""
    return PlannerParser(test_model)


@pytest.mark.asyncio
async def test_parse_add_task(parser):
    """Test parsing add task command."""
    # Mock the agent response
    parser.agent.run = AsyncMock(return_value=Mock(
        data='{"action": "add_task", "data": {"title": "job search", "priority": "high", "tags": ["personal"]}}'
    ))
    
    result = await parser.parse("add task 'job search' with tag 'personal' and high priority")
    
    assert result["action"] == "add_task"
    assert result["data"]["title"] == "job search"
    assert result["data"]["priority"] == "high"
    assert "personal" in result["data"]["tags"]


@pytest.mark.asyncio
async def test_parse_update_task(parser):
    """Test parsing update task command."""
    parser.agent.run = AsyncMock(return_value=Mock(
        data='{"action": "update_task", "data": {"identifier": "job search", "updates": {"status": "in_progress"}}}'
    ))
    
    result = await parser.parse("change status of job search to in progress")
    
    assert result["action"] == "update_task"
    assert result["data"]["identifier"] == "job search"
    assert result["data"]["updates"]["status"] == "in_progress"


@pytest.mark.asyncio
async def test_parse_add_log(parser):
    """Test parsing add log command."""
    parser.agent.run = AsyncMock(return_value=Mock(
        data='{"action": "add_log", "data": {"description": "research automated test analysis", "hours": 2}}'
    ))
    
    result = await parser.parse("add a daily log 'research automated test analysis' took 2 hours")
    
    assert result["action"] == "add_log"
    assert result["data"]["description"] == "research automated test analysis"
    assert result["data"]["hours"] == 2


@pytest.mark.asyncio
async def test_parse_add_meeting(parser):
    """Test parsing add meeting command."""
    parser.agent.run = AsyncMock(return_value=Mock(
        data='{"action": "add_meeting", "data": {"title": "team sync", "date": "tomorrow", "time": "10:00"}}'
    ))
    
    result = await parser.parse("schedule meeting team sync tomorrow at 10am")
    
    assert result["action"] == "add_meeting"
    assert result["data"]["title"] == "team sync"
    # Date should be processed to ISO format
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert result["data"]["date"] == tomorrow
    assert result["data"]["time"] == "10:00"


@pytest.mark.asyncio
async def test_parse_invalid_json(parser):
    """Test handling of invalid JSON response."""
    parser.agent.run = AsyncMock(return_value=Mock(
        data='invalid json'
    ))
    
    result = await parser.parse("some command")
    
    assert result["action"] == "error"
    assert "Failed to understand" in result["data"]["message"]


@pytest.mark.asyncio
async def test_parse_missing_fields(parser):
    """Test handling of response missing required fields."""
    parser.agent.run = AsyncMock(return_value=Mock(
        data='{"invalid": "response"}'
    ))
    
    result = await parser.parse("some command")
    
    assert result["action"] == "error"
    assert "Invalid response" in result["data"]["message"]


def test_parse_date_today(parser):
    """Test date parsing for 'today'."""
    result = parser._parse_date("today")
    assert result == date.today()


def test_parse_date_tomorrow(parser):
    """Test date parsing for 'tomorrow'."""
    result = parser._parse_date("tomorrow")
    assert result == date.today() + timedelta(days=1)


def test_parse_date_next_week(parser):
    """Test date parsing for 'next week'."""
    result = parser._parse_date("next week")
    assert result == date.today() + timedelta(weeks=1)


def test_parse_time_with_am_pm(parser):
    """Test time parsing with AM/PM."""
    assert parser._parse_time("10am") == "10:00"
    assert parser._parse_time("2:30pm") == "14:30"
    assert parser._parse_time("12pm") == "12:00"
    assert parser._parse_time("12am") == "00:00"


def test_parse_time_named(parser):
    """Test parsing named times."""
    assert parser._parse_time("morning") == "09:00"
    assert parser._parse_time("afternoon") == "14:00"
    assert parser._parse_time("evening") == "18:00"


def test_parse_time_already_formatted(parser):
    """Test parsing already formatted times."""
    assert parser._parse_time("10:30") == "10:30"
    assert parser._parse_time("14:00") == "14:00"