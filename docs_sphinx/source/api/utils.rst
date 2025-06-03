Utilities
=========

The utilities module provides common functionality including logging, helper functions, and shared utilities used across the automation agents system.

Logging (:mod:`src.utils.logging`)
----------------------------------

The logging module provides structured logging functionality with multiple output formats and levels.

.. automodule:: src.utils.logging
   :members:
   :undoc-members:
   :show-inheritance:

**Key Features:**

- Structured logging with JSON and text formats
- Multiple log levels with color coding
- File rotation and archival
- Performance metrics logging
- Exception tracking with stack traces

**Usage Example:**

.. code-block:: python

   from src.utils.logging import (
       setup_logger, log_info, log_error, log_warning, 
       log_debug, log_exception
   )

   # Setup logging
   setup_logger("my_component", "INFO")

   # Basic logging
   log_info("Application started")
   log_warning("Configuration file not found, using defaults")
   log_error("Failed to connect to external service")

   # Exception logging with context
   try:
       # Some operation that might fail
       result = risky_operation()
   except Exception as e:
       log_exception("Failed to perform risky operation", extra_context={
           "operation_id": "op_123",
           "user_id": "user_456"
       })

Log Utilities (:mod:`src.utils.log_utils`)
------------------------------------------

Additional logging utilities for specialized logging needs.

.. automodule:: src.utils.log_utils
   :members:
   :undoc-members:
   :show-inheritance:

**Performance Logging:**

.. code-block:: python

   from src.utils.log_utils import log_performance, LogTimer

   # Method 1: Decorator for automatic timing
   @log_performance
   async def expensive_operation():
       # Some time-consuming operation
       await asyncio.sleep(2)
       return "result"

   # Method 2: Context manager for timing blocks
   async def complex_operation():
       with LogTimer("database_query"):
           # Database operation
           pass
       
       with LogTimer("api_call"):
           # External API call
           pass

**Structured Logging:**

.. code-block:: python

   from src.utils.log_utils import StructuredLogger

   logger = StructuredLogger("automation_agent")

   # Log with structured data
   logger.log_event("user_action", {
       "user_id": "user_123",
       "action": "search_query",
       "query": "python best practices",
       "timestamp": "2024-03-15T10:30:00Z",
       "session_id": "session_456"
   })

   # Log agent interactions
   logger.log_agent_call("rag_agent", {
       "query": "authentication methods",
       "results_count": 5,
       "response_time_ms": 234
   })

**Error Tracking:**

.. code-block:: python

   from src.utils.log_utils import ErrorTracker

   error_tracker = ErrorTracker()

   try:
       # Some operation
       result = operation()
   except Exception as e:
       error_tracker.track_error(e, context={
           "component": "rag_agent",
           "operation": "document_search",
           "user_query": "find auth docs"
       })

   # Get error statistics
   stats = error_tracker.get_error_stats()
   print(f"Total errors: {stats['total_errors']}")
   print(f"Most common error: {stats['most_common_error']}")

Logging Configuration
--------------------

**Logger Setup:**

.. code-block:: python

   import logging
   from pathlib import Path

   def setup_application_logging(
       app_name: str = "automation_agents",
       log_level: str = "INFO",
       log_dir: str = "logs",
       enable_file_logging: bool = True,
       enable_console_logging: bool = True,
       max_file_size: int = 10 * 1024 * 1024,  # 10MB
       backup_count: int = 5
   ):
       """Setup comprehensive application logging."""
       
       # Create logs directory
       log_path = Path(log_dir)
       log_path.mkdir(parents=True, exist_ok=True)
       
       # Configure root logger
       root_logger = logging.getLogger()
       root_logger.setLevel(getattr(logging, log_level.upper()))
       
       # Remove existing handlers
       for handler in root_logger.handlers[:]:
           root_logger.removeHandler(handler)
       
       # Setup formatters
       detailed_formatter = logging.Formatter(
           '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
       )
       
       simple_formatter = logging.Formatter(
           '%(asctime)s - %(levelname)s - %(message)s'
       )
       
       # Console handler
       if enable_console_logging:
           console_handler = logging.StreamHandler()
           console_handler.setFormatter(simple_formatter)
           root_logger.addHandler(console_handler)
       
       # File handler with rotation
       if enable_file_logging:
           from logging.handlers import RotatingFileHandler
           
           file_handler = RotatingFileHandler(
               log_path / f"{app_name}.log",
               maxBytes=max_file_size,
               backupCount=backup_count
           )
           file_handler.setFormatter(detailed_formatter)
           root_logger.addHandler(file_handler)
           
           # Separate error log
           error_handler = RotatingFileHandler(
               log_path / f"{app_name}_errors.log",
               maxBytes=max_file_size,
               backupCount=backup_count
           )
           error_handler.setLevel(logging.ERROR)
           error_handler.setFormatter(detailed_formatter)
           root_logger.addHandler(error_handler)

**JSON Logging:**

.. code-block:: python

   import json
   import logging
   from datetime import datetime

   class JSONFormatter(logging.Formatter):
       """JSON formatter for structured logging."""
       
       def format(self, record):
           log_entry = {
               'timestamp': datetime.utcnow().isoformat(),
               'level': record.levelname,
               'logger': record.name,
               'message': record.getMessage(),
               'module': record.module,
               'function': record.funcName,
               'line': record.lineno
           }
           
           # Add exception info if present
           if record.exc_info:
               log_entry['exception'] = self.formatException(record.exc_info)
           
           # Add custom fields
           if hasattr(record, 'user_id'):
               log_entry['user_id'] = record.user_id
           if hasattr(record, 'session_id'):
               log_entry['session_id'] = record.session_id
           if hasattr(record, 'agent_name'):
               log_entry['agent_name'] = record.agent_name
           
           return json.dumps(log_entry)

   # Usage
   handler = logging.StreamHandler()
   handler.setFormatter(JSONFormatter())
   logger = logging.getLogger("json_logger")
   logger.addHandler(handler)

**Performance Monitoring:**

.. code-block:: python

   import time
   import functools
   from typing import Any, Callable

   def monitor_performance(operation_name: str = None):
       """Decorator to monitor function performance."""
       
       def decorator(func: Callable) -> Callable:
           @functools.wraps(func)
           async def async_wrapper(*args, **kwargs) -> Any:
               start_time = time.time()
               operation = operation_name or f"{func.__module__}.{func.__name__}"
               
               try:
                   result = await func(*args, **kwargs)
                   duration = time.time() - start_time
                   
                   log_info(f"Operation completed: {operation}", extra={
                       'operation': operation,
                       'duration_ms': round(duration * 1000, 2),
                       'success': True
                   })
                   
                   return result
                   
               except Exception as e:
                   duration = time.time() - start_time
                   
                   log_error(f"Operation failed: {operation}", extra={
                       'operation': operation,
                       'duration_ms': round(duration * 1000, 2),
                       'success': False,
                       'error': str(e)
                   })
                   
                   raise
           
           @functools.wraps(func)
           def sync_wrapper(*args, **kwargs) -> Any:
               # Similar implementation for sync functions
               pass
           
           return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
       
       return decorator

**Context Logging:**

.. code-block:: python

   import contextvars
   from typing import Dict, Any

   # Context variables for logging
   current_user = contextvars.ContextVar('current_user', default=None)
   current_session = contextvars.ContextVar('current_session', default=None)
   current_agent = contextvars.ContextVar('current_agent', default=None)

   class ContextualLogger:
       """Logger that automatically includes context information."""
       
       def __init__(self, name: str):
           self.logger = logging.getLogger(name)
       
       def _get_context(self) -> Dict[str, Any]:
           """Get current context information."""
           context = {}
           
           if current_user.get():
               context['user_id'] = current_user.get()
           if current_session.get():
               context['session_id'] = current_session.get()
           if current_agent.get():
               context['agent_name'] = current_agent.get()
           
           return context
       
       def info(self, message: str, **kwargs):
           """Log info message with context."""
           extra = self._get_context()
           extra.update(kwargs)
           self.logger.info(message, extra=extra)
       
       def error(self, message: str, **kwargs):
           """Log error message with context."""
           extra = self._get_context()
           extra.update(kwargs)
           self.logger.error(message, extra=extra)

   # Usage
   logger = ContextualLogger("agent_operations")

   # Set context
   current_user.set("user_123")
   current_session.set("session_456")
   current_agent.set("rag_agent")

   # Log with automatic context
   logger.info("User performed search", query="python best practices")

Helper Functions
---------------

**Common Utility Functions:**

.. code-block:: python

   from typing import Any, Dict, List, Optional
   import hashlib
   import json
   from datetime import datetime, date

   def generate_id(content: str) -> str:
       """Generate unique ID from content."""
       return hashlib.md5(content.encode()).hexdigest()

   def safe_json_dumps(obj: Any) -> str:
       """Safely serialize object to JSON."""
       try:
           return json.dumps(obj, default=str, ensure_ascii=False)
       except Exception:
           return str(obj)

   def safe_json_loads(json_str: str) -> Any:
       """Safely deserialize JSON string."""
       try:
           return json.loads(json_str)
       except Exception:
           return None

   def format_timestamp(dt: datetime = None) -> str:
       """Format datetime as ISO string."""
       if dt is None:
           dt = datetime.now()
       return dt.isoformat()

   def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
       """Parse ISO timestamp string."""
       try:
           return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
       except Exception:
           return None

   def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
       """Split list into chunks."""
       return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

   def deep_merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
       """Deep merge two dictionaries."""
       result = dict1.copy()
       
       for key, value in dict2.items():
           if key in result and isinstance(result[key], dict) and isinstance(value, dict):
               result[key] = deep_merge_dicts(result[key], value)
           else:
               result[key] = value
       
       return result

**Validation Utilities:**

.. code-block:: python

   import re
   from pathlib import Path

   def is_valid_email(email: str) -> bool:
       """Validate email address format."""
       pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
       return re.match(pattern, email) is not None

   def is_valid_url(url: str) -> bool:
       """Validate URL format."""
       pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
       return re.match(pattern, url) is not None

   def is_safe_filename(filename: str) -> bool:
       """Check if filename is safe for filesystem."""
       dangerous_chars = '<>:"/\\|?*'
       return not any(char in filename for char in dangerous_chars)

   def sanitize_filename(filename: str) -> str:
       """Sanitize filename for filesystem safety."""
       # Replace dangerous characters with underscores
       dangerous_chars = '<>:"/\\|?*'
       for char in dangerous_chars:
           filename = filename.replace(char, '_')
       
       # Remove leading/trailing whitespace and dots
       filename = filename.strip(' .')
       
       # Ensure filename is not empty
       if not filename:
           filename = 'unnamed_file'
       
       return filename

**File Utilities:**

.. code-block:: python

   import shutil
   from pathlib import Path
   from typing import Union

   def ensure_directory(path: Union[str, Path]) -> Path:
       """Ensure directory exists, create if necessary."""
       path = Path(path)
       path.mkdir(parents=True, exist_ok=True)
       return path

   def safe_file_read(file_path: Union[str, Path], encoding: str = 'utf-8') -> Optional[str]:
       """Safely read file contents."""
       try:
           with open(file_path, 'r', encoding=encoding) as f:
               return f.read()
       except Exception as e:
           log_error(f"Failed to read file {file_path}: {e}")
           return None

   def safe_file_write(file_path: Union[str, Path], content: str, encoding: str = 'utf-8') -> bool:
       """Safely write content to file."""
       try:
           path = Path(file_path)
           path.parent.mkdir(parents=True, exist_ok=True)
           
           with open(path, 'w', encoding=encoding) as f:
               f.write(content)
           return True
       except Exception as e:
           log_error(f"Failed to write file {file_path}: {e}")
           return False

   def get_file_size(file_path: Union[str, Path]) -> int:
       """Get file size in bytes."""
       try:
           return Path(file_path).stat().st_size
       except Exception:
           return 0

   def backup_file(file_path: Union[str, Path], backup_suffix: str = '.bak') -> Optional[Path]:
       """Create backup of file."""
       try:
           source = Path(file_path)
           backup = source.with_suffix(source.suffix + backup_suffix)
           shutil.copy2(source, backup)
           return backup
       except Exception as e:
           log_error(f"Failed to backup file {file_path}: {e}")
           return None

Error Handling Utilities
------------------------

**Exception Utilities:**

.. code-block:: python

   import traceback
   from typing import Type, Union

   def format_exception(exc: Exception) -> Dict[str, Any]:
       """Format exception for logging."""
       return {
           'type': exc.__class__.__name__,
           'message': str(exc),
           'traceback': traceback.format_exc(),
           'args': exc.args
       }

   def safe_execute(func: Callable, *args, default=None, **kwargs) -> Any:
       """Safely execute function with default fallback."""
       try:
           return func(*args, **kwargs)
       except Exception as e:
           log_warning(f"Safe execution failed for {func.__name__}: {e}")
           return default

   async def safe_execute_async(func: Callable, *args, default=None, **kwargs) -> Any:
       """Safely execute async function with default fallback."""
       try:
           return await func(*args, **kwargs)
       except Exception as e:
           log_warning(f"Safe async execution failed for {func.__name__}: {e}")
           return default

**Retry Utilities:**

.. code-block:: python

   import asyncio
   import random
   from typing import Callable, Any, Type

   async def retry_async(
       func: Callable,
       max_attempts: int = 3,
       delay: float = 1.0,
       backoff_factor: float = 2.0,
       exceptions: tuple = (Exception,),
       jitter: bool = True
   ) -> Any:
       """Retry async function with exponential backoff."""
       
       for attempt in range(max_attempts):
           try:
               return await func()
           except exceptions as e:
               if attempt == max_attempts - 1:
                   raise
               
               wait_time = delay * (backoff_factor ** attempt)
               if jitter:
                   wait_time *= (0.5 + random.random() * 0.5)
               
               log_warning(f"Attempt {attempt + 1} failed, retrying in {wait_time:.2f}s: {e}")
               await asyncio.sleep(wait_time)

   def retry_sync(
       func: Callable,
       max_attempts: int = 3,
       delay: float = 1.0,
       backoff_factor: float = 2.0,
       exceptions: tuple = (Exception,)
   ) -> Any:
       """Retry sync function with exponential backoff."""
       
       import time
       
       for attempt in range(max_attempts):
           try:
               return func()
           except exceptions as e:
               if attempt == max_attempts - 1:
                   raise
               
               wait_time = delay * (backoff_factor ** attempt)
               log_warning(f"Attempt {attempt + 1} failed, retrying in {wait_time:.2f}s: {e}")
               time.sleep(wait_time)