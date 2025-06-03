Core Modules
============

This section documents the core modules that provide configuration, constants, and exception handling for the automation agents system.

Configuration (:mod:`src.core.config`)
---------------------------------------

The configuration module manages application settings and environment variables.

.. automodule:: src.core.config
   :members:
   :undoc-members:
   :show-inheritance:

**Key Classes:**

.. autoclass:: src.core.config.Settings
   :members:
   :undoc-members:
   :show-inheritance:

   **Configuration Fields:**

   - ``model_choice``: OpenAI model to use (default: gpt-4o-mini)
   - ``base_url``: API base URL (default: https://api.openai.com/v1)
   - ``llm_api_key``: OpenAI API key (required)
   - ``openai_api_key``: OpenAI API key for embeddings
   - ``github_token``: GitHub personal access token
   - ``brave_search_key``: Brave Search API key
   - ``slack_bot_token``: Slack bot token
   - ``slack_app_token``: Slack app token
   - ``debug``: Debug mode flag
   - ``log_level``: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

.. autoclass:: src.core.config.MCPServerConfig
   :members:
   :undoc-members:
   :show-inheritance:

**Usage Example:**

.. code-block:: python

   from src.core.config import get_settings, get_mcp_config

   # Get application settings
   settings = get_settings()
   print(f"Using model: {settings.model_choice}")
   print(f"Debug mode: {settings.debug}")

   # Get MCP server configuration
   mcp_config = get_mcp_config()
   brave_config = mcp_config.brave_search

Constants (:mod:`src.core.constants`)
-------------------------------------

The constants module defines system-wide constants, agent types, and configuration values.

.. automodule:: src.core.constants
   :members:
   :undoc-members:
   :show-inheritance:

**Key Constants:**

- ``AgentType``: Enumeration of available agent types
- ``SYSTEM_PROMPTS``: Dictionary mapping agent types to their system prompts
- ``MCP_SERVER_STARTUP_TIMEOUT``: Timeout for MCP server initialization
- ``DEFAULT_CHUNK_SIZE``: Default text chunk size for document processing
- ``SUPPORTED_FILE_TYPES``: List of supported file extensions

**Usage Example:**

.. code-block:: python

   from src.core.constants import AgentType, SYSTEM_PROMPTS

   # Get agent type
   agent_type = AgentType.PRIMARY

   # Get system prompt for an agent
   prompt = SYSTEM_PROMPTS[AgentType.RAG]

Exceptions (:mod:`src.core.exceptions`)
---------------------------------------

The exceptions module defines custom exception classes for the automation agents system.

.. automodule:: src.core.exceptions
   :members:
   :undoc-members:
   :show-inheritance:

**Exception Hierarchy:**

.. autoclass:: src.core.exceptions.AutomationAgentError
   :members:
   :show-inheritance:

   Base exception class for all automation agent errors.

.. autoclass:: src.core.exceptions.MCPServerError
   :members:
   :show-inheritance:

   Exception raised for MCP server-related errors.

.. autoclass:: src.core.exceptions.MCPServerStartupError
   :members:
   :show-inheritance:

   Exception raised when MCP server fails to start.

.. autoclass:: src.core.exceptions.MCPServerConnectionError
   :members:
   :show-inheritance:

   Exception raised for MCP server connection issues.

.. autoclass:: src.core.exceptions.ChromaDBError
   :members:
   :show-inheritance:

   Exception raised for ChromaDB-related errors.

.. autoclass:: src.core.exceptions.DocumentProcessingError
   :members:
   :show-inheritance:

   Exception raised during document processing.

**Usage Example:**

.. code-block:: python

   from src.core.exceptions import MCPServerError, ChromaDBError

   try:
       # Some operation that might fail
       await mcp_manager.initialize()
   except MCPServerError as e:
       logger.error(f"MCP server failed: {e}")
   except ChromaDBError as e:
       logger.error(f"Database error: {e}")

Error Handling Best Practices
-----------------------------

The automation agents system uses structured error handling:

1. **Specific Exceptions**: Use specific exception types for different error categories
2. **Error Propagation**: Errors are caught at agent boundaries and converted to user-friendly messages
3. **Logging Integration**: All exceptions are logged with appropriate detail levels
4. **Graceful Degradation**: Failed components don't crash the entire system

**Example Error Handling Pattern:**

.. code-block:: python

   from src.core.exceptions import AutomationAgentError
   from src.utils.logging import log_error, log_exception

   async def some_agent_operation():
       try:
           # Perform operation
           result = await external_service.call()
           return result
       except ExternalServiceError as e:
           log_error(f"External service failed: {e}")
           raise AutomationAgentError(f"Operation failed: {e}")
       except Exception as e:
           log_exception("Unexpected error in agent operation")
           raise AutomationAgentError(f"Unexpected error: {e}")