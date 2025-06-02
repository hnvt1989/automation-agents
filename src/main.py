"""Main application entry point."""
import asyncio
import sys
from typing import Optional, Dict, Any
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import get_settings
from src.core.exceptions import AutomationAgentError, MCPServerError
from src.mcp import get_mcp_manager
from src.utils.logging import log_info, log_error, log_exception, setup_logger
from src.agents.primary import PrimaryAgent
from src.agents.brave_search import BraveSearchAgent
from src.agents.filesystem import FilesystemAgent
from src.agents.planner import plan_day
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel


console = Console()


class AutomationAgentsCLI:
    """Main CLI application for automation agents."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.settings = get_settings()
        self.mcp_manager = get_mcp_manager()
        self.agents: Dict[str, Any] = {}
        self.model: Optional[OpenAIModel] = None
        
        # Setup logging
        setup_logger("automation_agents", self.settings.log_level)
    
    def get_model(self) -> OpenAIModel:
        """Get the configured OpenAI model."""
        if self.model is None:
            provider = OpenAIProvider(
                base_url=self.settings.base_url,
                api_key=self.settings.llm_api_key
            )
            self.model = OpenAIModel(
                self.settings.model_choice,
                provider=provider
            )
            log_info(f"Using {self.settings.model_choice} model with base URL: {self.settings.base_url}")
        
        return self.model
    
    async def initialize(self):
        """Initialize MCP servers and agents."""
        console.print("[yellow]Initializing automation agents...[/yellow]")
        
        try:
            # Initialize MCP servers
            await self.mcp_manager.initialize()
            
            # Initialize agents
            model = self.get_model()
            
            # Create individual agents
            self.agents["brave_search"] = BraveSearchAgent(model).agent
            self.agents["filesystem"] = FilesystemAgent(model).agent
            
            # Create primary agent with access to other agents
            self.primary_agent = PrimaryAgent(model, self.agents)
            
            console.print("[green]✓ Automation agents initialized successfully![/green]")
            
        except MCPServerError as e:
            console.print(f"[red]Failed to initialize MCP servers: {str(e)}[/red]")
            raise
        except Exception as e:
            console.print(f"[red]Failed to initialize: {str(e)}[/red]")
            raise
    
    async def shutdown(self):
        """Shutdown MCP servers and cleanup."""
        console.print("\n[yellow]Shutting down...[/yellow]")
        
        try:
            await self.mcp_manager.shutdown()
            console.print("[green]✓ Shutdown complete[/green]")
        except Exception as e:
            log_error(f"Error during shutdown: {str(e)}")
    
    def display_welcome(self):
        """Display welcome message."""
        welcome_text = Text.from_markup(
            "[bold blue]Automation Agents CLI[/bold blue]\n"
            "[dim]AI-powered automation assistant[/dim]"
        )
        
        console.print(Panel(
            welcome_text,
            border_style="blue",
            padding=(1, 2)
        ))
        
        console.print("\n[dim]Available commands:[/dim]")
        console.print("  • Type your query to interact with the AI assistant")
        console.print("  • Type 'plan' to use the planning assistant")
        console.print("  • Type 'help' for more information")
        console.print("  • Type 'exit' or 'quit' to leave\n")
    
    async def handle_query(self, query: str) -> None:
        """Handle a user query.
        
        Args:
            query: The user's query
        """
        query = query.strip()
        
        # Check for special commands
        if query.lower() in ["exit", "quit", "q"]:
            return False
        
        if query.lower() == "help":
            self.display_help()
            return True
        
        if query.lower().startswith("plan"):
            # Extract date from query if present
            date_query = query[4:].strip() if len(query) > 4 else "today"
            await self.handle_planning(date_query)
            return True
        
        # Process regular query with primary agent
        try:
            console.print("\n[dim]Processing your request...[/dim]")
            
            result = await self.primary_agent.run(query)
            
            # Display result
            console.print("\n[bold]Response:[/bold]")
            if hasattr(result, 'data'):
                console.print(Markdown(str(result.data)))
            else:
                console.print(Markdown(str(result)))
            
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]")
            log_exception("Error processing query")
        
        return True
    
    async def handle_planning(self, date_query: str) -> None:
        """Handle planning requests.
        
        Args:
            date_query: Date specification for planning
        """
        try:
            console.print(f"\n[dim]Creating plan for: {date_query}[/dim]")
            
            # Convert date query to actual date
            from datetime import datetime, date, timedelta
            import re
            
            date_query_lower = date_query.lower().strip()
            
            if date_query_lower == "today":
                target_date = date.today()
            elif date_query_lower == "tomorrow":
                target_date = date.today() + timedelta(days=1)
            elif date_query_lower == "yesterday":
                target_date = date.today() - timedelta(days=1)
            else:
                # Try to parse as ISO date
                try:
                    target_date = datetime.fromisoformat(date_query).date()
                except:
                    target_date = date.today()
            
            # Create payload for plan_day
            payload = {
                'paths': {
                    'tasks': 'data/tasks.yaml',
                    'logs': 'data/daily_logs.yaml',
                    'meets': 'data/meetings.yaml'
                },
                'target_date': target_date.isoformat(),
                'work_hours': {'start': '09:00', 'end': '17:00'}
            }
            
            result_dict = plan_day(payload)
            
            if "error" in result_dict:
                raise Exception(result_dict["error"])
            
            # Combine the markdown sections
            result = f"{result_dict.get('yesterday_markdown', '')}\n\n{result_dict.get('tomorrow_markdown', '')}"
            
            console.print("\n[bold]Your Plan:[/bold]")
            console.print(Markdown(result))
            
        except Exception as e:
            console.print(f"\n[red]Error creating plan: {str(e)}[/red]")
            log_exception("Error in planning")
    
    def display_help(self):
        """Display help information."""
        help_text = """
# Automation Agents Help

## Available Commands:
- **General queries**: Just type your question or request
- **plan [date]**: Create a plan for a specific date
  - Examples: 'plan today', 'plan tomorrow', 'plan 2024-03-15'
- **help**: Show this help message
- **exit/quit**: Exit the application

## Available Agents:
1. **Primary Agent**: Orchestrates tasks and delegates to specialized agents
2. **Brave Search**: Performs web searches
3. **Filesystem**: Handles file operations
4. **GitHub**: Manages GitHub repositories and issues
5. **Slack**: Sends messages to Slack
6. **Analyzer**: Performs data analysis and code review
7. **RAG**: Searches indexed knowledge bases

## Examples:
- "Search for the latest Python trends"
- "Create a file with today's meeting notes"
- "What's in my project directory?"
- "plan tomorrow"
"""
        console.print(Markdown(help_text))
    
    async def run(self):
        """Run the interactive CLI."""
        self.display_welcome()
        
        try:
            await self.initialize()
            
            # Main interaction loop
            while True:
                try:
                    query = Prompt.ask("\n[bold blue]You[/bold blue]")
                    
                    if not query.strip():
                        continue
                    
                    should_continue = await self.handle_query(query)
                    if not should_continue:
                        break
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]Use 'exit' to quit[/yellow]")
                    continue
                except Exception as e:
                    console.print(f"\n[red]Unexpected error: {str(e)}[/red]")
                    log_exception("Unexpected error in main loop")
        
        finally:
            await self.shutdown()


async def main():
    """Main entry point."""
    cli = AutomationAgentsCLI()
    await cli.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {str(e)}[/red]")
        log_exception("Fatal error")
        sys.exit(1)