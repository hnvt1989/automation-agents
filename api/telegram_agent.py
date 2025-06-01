"""
Simplified agent implementation for Telegram bot.
This is a lightweight version without MCP servers for serverless deployment.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Re-export the core functions
from telegram_agent_core import (
    get_telegram_model,
    create_telegram_agent,
    process_telegram_message,
    extract_date_from_query,
    is_planning_query,
    basic_planning_response
)

# Export all functions
__all__ = [
    'get_telegram_model',
    'create_telegram_agent',
    'process_telegram_message',
    'extract_date_from_query',
    'is_planning_query',
    'basic_planning_response'
]