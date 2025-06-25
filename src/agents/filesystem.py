"""Filesystem agent for handling file operations."""
import os
from pathlib import Path
from typing import Optional, Any, Dict, List
from datetime import datetime
import uuid

from pydantic import BaseModel, Field
from pydantic_ai import RunContext
from pydantic_ai.models.openai import OpenAIModel

from .base import BaseAgent
from src.core.constants import AgentType, SYSTEM_PROMPTS
from src.mcp.manager import get_mcp_manager
from src.utils.logging import log_info, log_warning, log_error
from src.processors.calendar import parse_calendar_from_image, save_parsed_events_yaml
from src.processors.image import extract_text_from_image, parse_conversation_from_text


class FilesystemAgentDeps(BaseModel):
    """Dependencies for the filesystem agent."""
    
    class Config:
        arbitrary_types_allowed = True


class FilesystemAgent(BaseAgent):
    """Agent for performing filesystem operations."""
    
    def __init__(self, model: OpenAIModel):
        """Initialize the Filesystem agent.
        
        Args:
            model: OpenAI model to use
        """
        # Get MCP manager and server
        mcp_manager = get_mcp_manager()
        self.filesystem_server = mcp_manager.get_server("filesystem")
        
        # Update system prompt to include image analysis capabilities
        enhanced_prompt = SYSTEM_PROMPTS[AgentType.FILESYSTEM] + """
You can analyze calendar screenshots using the analyze_calendar_image tool and save the extracted events to YAML files.
You can analyze conversation screenshots using the analyze_conversation_image tool."""
        
        super().__init__(
            name=AgentType.FILESYSTEM,
            model=model,
            system_prompt=enhanced_prompt,
            deps_type=FilesystemAgentDeps,
            mcp_servers=[self.filesystem_server]
        )
        
        self._register_tools()
        log_info("Filesystem agent initialized")
    
    def _register_tools(self):
        """Register additional tools for the filesystem agent."""
        
        @self.agent.tool
        async def analyze_calendar_image(
            ctx: RunContext[FilesystemAgentDeps],
            image_path: str,
            output_yaml_path: str = "data/meetings.yaml"
        ) -> str:
            """Analyze a calendar screenshot and extract events to a YAML file.
            
            Args:
                image_path: Path to the calendar image
                output_yaml_path: Path where to save the extracted events
                
            Returns:
                Status message
            """
            log_info(f"Analyzing calendar image: {image_path}")
            
            try:
                # Check if image exists
                image_file = Path(image_path)
                if not image_file.exists():
                    return f"Image file not found: {image_path}"
                
                if not image_file.is_file():
                    return f"Path is not a file: {image_path}"
                
                # Use the calendar processor to extract events
                events = await parse_calendar_from_image(str(image_file))
                
                if not events:
                    return f"No calendar events found in image: {image_path}"
                
                # Save events to YAML
                save_parsed_events_yaml(events, output_yaml_path)
                
                # Format summary of events
                event_summary = []
                for event in events[:5]:  # Show first 5 events
                    event_str = f"- {event['date']} {event['time']}: {event['event']}"
                    event_summary.append(event_str)
                
                if len(events) > 5:
                    event_summary.append(f"... and {len(events) - 5} more events")
                
                summary = "\n".join(event_summary)
                
                log_info(f"Successfully extracted {len(events)} events from {image_path}")
                return f"Successfully analyzed calendar image and saved {len(events)} events to {output_yaml_path}:\n\n{summary}"
                
            except Exception as e:
                log_error(f"Error analyzing calendar image: {str(e)}")
                return f"Error analyzing calendar image: {str(e)}"
        
        @self.agent.tool
        async def analyze_conversation_image(
            ctx: RunContext[FilesystemAgentDeps],
            image_path: str
        ) -> str:
            """Analyze a conversation screenshot.
            
            Args:
                image_path: Path to the conversation image
                
            Returns:
                Status message with conversation summary
            """
            log_info(f"Analyzing conversation image: {image_path}")
            
            try:
                # Check if image exists
                image_file = Path(image_path)
                if not image_file.exists():
                    return f"Image file not found: {image_path}"
                
                if not image_file.is_file():
                    return f"Path is not a file: {image_path}"
                
                # Extract text from image first
                text = await extract_text_from_image(str(image_file), "file")
                if not text:
                    return f"No text found in image: {image_path}"
                
                # Parse conversations
                conversation_log = await parse_conversation_from_text(text, str(image_file))
                
                if not conversation_log or not conversation_log.messages:
                    return f"No conversations found in image: {image_path}"
                
                # Format summary
                summary_lines = [
                    f"Platform: {conversation_log.platform}",
                    f"Channel: {conversation_log.channel or 'N/A'}",
                    f"Messages: {len(conversation_log.messages)}",
                    "",
                    "First few messages:"
                ]
                
                for msg in conversation_log.messages[:5]:
                    timestamp = msg.timestamp or "No timestamp"
                    summary_lines.append(f"- [{timestamp}] {msg.speaker}: {msg.content[:100]}...")
                
                if len(conversation_log.messages) > 5:
                    summary_lines.append(f"... and {len(conversation_log.messages) - 5} more messages")
                
                summary = "\n".join(summary_lines)
                
                log_info(f"Successfully analyzed conversation with {len(conversation_log.messages)} messages")
                return f"Successfully analyzed conversation image:\n\n{summary}"
                
            except Exception as e:
                log_error(f"Error analyzing conversation image: {str(e)}")
                return f"Error analyzing conversation image: {str(e)}"
    
    async def run(self, prompt: str, deps: Optional[Any] = None, **kwargs) -> Any:
        """Run the filesystem agent.
        
        Args:
            prompt: The user prompt
            deps: Optional dependencies
            **kwargs: Additional arguments
            
        Returns:
            The agent's response
        """
        if deps is None:
            deps = FilesystemAgentDeps()
        
        return await super().run(prompt, deps=deps, **kwargs)