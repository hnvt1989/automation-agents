"""Enhanced logging utilities for the application."""
import logging
import sys
from typing import Optional, Union
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
from rich.console import Console

from src.core.config import get_settings


# Console for rich output
console = Console()


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str = "automation_agents",
    level: Optional[str] = None,
    log_file: Optional[Union[str, Path]] = None,
    use_rich: bool = True
) -> logging.Logger:
    """Set up a logger with file and console handlers.
    
    Args:
        name: Logger name
        level: Log level (defaults to settings.log_level)
        log_file: Path to log file (defaults to logs/{name}.log)
        use_rich: Whether to use rich handler for console output
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Get settings
    settings = get_settings()
    
    # Create logs directory if it doesn't exist
    logs_dir = settings.project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Set log level
    log_level = level or settings.log_level
    logger.setLevel(getattr(logging, log_level))
    
    # File handler with rotation
    if log_file is None:
        log_file = logs_dir / f"{name}.log"
    else:
        log_file = Path(log_file)
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    if use_rich:
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            rich_tracebacks=True
        )
        console_handler.setFormatter(logging.Formatter('%(message)s'))
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
    
    logger.addHandler(console_handler)
    
    return logger


# Create default logger
logger = setup_logger()


def log_debug(message: str, **kwargs):
    """Log debug message."""
    logger.debug(message, **kwargs)


def log_info(message: str, **kwargs):
    """Log info message."""
    logger.info(message, **kwargs)


def log_warning(message: str, **kwargs):
    """Log warning message."""
    logger.warning(message, **kwargs)


def log_error(message: str, exc_info: bool = False, **kwargs):
    """Log error message."""
    logger.error(message, exc_info=exc_info, **kwargs)


def log_critical(message: str, exc_info: bool = True, **kwargs):
    """Log critical message."""
    logger.critical(message, exc_info=exc_info, **kwargs)


def log_exception(message: str = "An exception occurred"):
    """Log exception with traceback."""
    logger.exception(message)


class LogContext:
    """Context manager for temporary log level changes."""
    
    def __init__(self, level: str, logger_name: str = "automation_agents"):
        self.level = level
        self.logger = logging.getLogger(logger_name)
        self.original_level = None
    
    def __enter__(self):
        self.original_level = self.logger.level
        self.logger.setLevel(getattr(logging, self.level))
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.original_level)


def log_function_call(func):
    """Decorator to log function calls."""
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        log_debug(f"Calling function: {func_name}")
        try:
            result = func(*args, **kwargs)
            log_debug(f"Function {func_name} completed successfully")
            return result
        except Exception as e:
            log_error(f"Function {func_name} failed: {str(e)}", exc_info=True)
            raise
    return wrapper


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module."""
    return setup_logger(name)