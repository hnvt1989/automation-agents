"""Simple main application entry point without MCP servers."""
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
from src.utils.logging import log_info, log_error, log_exception, setup_logger
from src.agents.planner import plan_day
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel


console = Console()


class SimpleAutomationAgentsCLI:
    """Simple CLI application for automation agents without MCP servers."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.settings = get_settings()
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
    
    def display_welcome(self):
        """Display welcome message."""
        welcome_text = Text.from_markup(
            "[bold blue]Automation Agents CLI[/bold blue] (Simple Mode)\n"
            "[dim]AI-powered automation assistant[/dim]"
        )
        
        console.print(Panel(
            welcome_text,
            border_style="blue",
            padding=(1, 2)
        ))
        
        console.print("\n[dim]Available commands:[/dim]")
        console.print("  • Type 'plan [date]' to use the planning assistant")
        console.print("  • Type 'help' for more information")
        console.print("  • Type 'exit' or 'quit' to leave\n")
    
    async def handle_query(self, query: str) -> bool:
        """Handle a user query.
        
        Args:
            query: The user's query
            
        Returns:
            Whether to continue the loop
        """
        query = query.strip()
        
        # Check for special commands
        if query.lower() in ["exit", "quit", "q"]:
            return False
        
        if query.lower() == "help":
            self.display_help()
            return True
        
        if query.lower().startswith("plan") or query.lower() == "planner":
            # Extract date from query if present
            if query.lower() == "planner":
                # Default to today for bare "planner" command
                date_query = "today"
            else:
                date_query = query[4:].strip() if len(query) > 4 else "today"
            await self.handle_planning(date_query)
            return True
        
        # For now, just echo back
        console.print(f"\n[yellow]Simple mode doesn't support general queries yet.[/yellow]")
        console.print("Try 'plan today' or 'plan tomorrow' instead.")
        
        return True
    
    async def handle_planning(self, date_query: str) -> None:
        """Handle planning requests.
        
        Args:
            date_query: Date specification for planning
        """
        try:
            console.print(f"\n[dim]Creating plan for: {date_query}[/dim]")
            
            # Parse the date query
            from datetime import date, datetime, timedelta
            target_date = date.today()
            
            if date_query.lower() == "today":
                target_date = date.today()
            elif date_query.lower() == "tomorrow":
                target_date = date.today() + timedelta(days=1)
            elif date_query.lower() == "yesterday":
                target_date = date.today() - timedelta(days=1)
            else:
                # Try to parse specific date formats
                try:
                    target_date = datetime.fromisoformat(date_query).date()
                except ValueError:
                    try:
                        # Try other common formats
                        target_date = datetime.strptime(date_query, "%Y-%m-%d").date()
                    except ValueError:
                        log_error(f"Could not parse date '{date_query}', using today")
                        target_date = date.today()
            
            # Create payload for plan_day function
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
# Automation Agents Help (Simple Mode)

## Available Commands:
- **plan [date]**: Create a plan for a specific date
  - Examples: 'plan today', 'plan tomorrow', 'plan 2024-03-15'
- **help**: Show this help message
- **exit/quit**: Exit the application

## Note:
This is the simple mode without MCP servers. Only planning functionality is available.

## Examples:
- "plan today"
- "plan tomorrow"
- "plan next monday"
"""
        console.print(Markdown(help_text))
    
    async def run(self):
        """Run the interactive CLI."""
        self.display_welcome()
        
        try:
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
            console.print("\n[yellow]Goodbye![/yellow]")


async def main():
    """Main entry point."""
    cli = SimpleAutomationAgentsCLI()
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