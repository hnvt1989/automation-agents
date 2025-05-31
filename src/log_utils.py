from rich.console import Console

console = Console()

def log_info(message: str) -> None:
    console.print(message, style="bold cyan")

def log_warning(message: str) -> None:
    console.print(message, style="bold yellow")

def log_error(message: str) -> None:
    console.print(message, style="bold red")
