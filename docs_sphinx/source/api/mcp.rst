MCP (Model Context Protocol)
============================

The MCP module provides Model Context Protocol server management and integration for external services.

MCP Manager (:mod:`src.mcp.manager`)
------------------------------------

The MCP manager handles lifecycle management and connections for all MCP servers.

.. automodule:: src.mcp.manager
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: src.mcp.manager.MCPServerManager
   :members:
   :undoc-members:
   :show-inheritance:

   **Key Responsibilities:**

   - MCP server lifecycle management (start, stop, restart)
   - Connection pooling and health monitoring
   - Graceful shutdown and error recovery
   - Server configuration and environment setup

   **Managed Servers:**

   - **Brave Search Server**: Web search capabilities
   - **Filesystem Server**: File and directory operations  
   - **GitHub Server**: Repository and issue management
   - **Slack Server**: Team communication and notifications

**Usage Example:**

.. code-block:: python

   from src.mcp import get_mcp_manager

   # Get manager instance
   mcp_manager = get_mcp_manager()

   # Initialize all servers
   await mcp_manager.initialize()

   # Get specific server
   brave_server = mcp_manager.get_server("brave")

   # Health check
   health_status = await mcp_manager.health_check()
   print(f"Brave server healthy: {health_status['brave']}")

   # Shutdown all servers
   await mcp_manager.shutdown()

MCP Server Configuration
-----------------------

**Server Definitions:**

MCP servers are configured through the ``MCPServerConfig`` class:

.. code-block:: python

   # Example server configurations
   server_configs = {
       "brave_search": {
           "command": "npx",
           "args": ["-y", "@modelcontextprotocol/server-brave-search"],
           "env": {"BRAVE_API_KEY": "your_api_key"}
       },
       "filesystem": {
           "command": "npx", 
           "args": [
               "-y",
               "@modelcontextprotocol/server-filesystem",
               "/path/to/files",
               "/path/to/knowledge/base"
           ]
       },
       "github": {
           "command": "npx",
           "args": ["-y", "@modelcontextprotocol/server-github"],
           "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "your_token"}
       },
       "slack": {
           "command": "npx",
           "args": ["-y", "@modelcontextprotocol/server-slack"],
           "env": {
               "SLACK_BOT_TOKEN": "your_bot_token",
               "SLACK_TEAM_ID": "your_team_id"
           }
       }
   }

**Environment Variables:**

Each server requires specific environment variables:

.. code-block:: bash

   # Brave Search
   BRAVE_API_KEY=your_brave_search_api_key

   # GitHub
   GITHUB_TOKEN=your_github_personal_access_token

   # Slack
   SLACK_BOT_TOKEN=xoxb-your-bot-token
   SLACK_APP_TOKEN=xapp-your-app-token
   SLACK_TEAM_ID=T1234567890

   # Filesystem
   LOCAL_FILE_DIR=/path/to/your/files
   LOCAL_FILE_DIR_KNOWLEDGE_BASE=/path/to/knowledge/base

Server Lifecycle Management
---------------------------

**Initialization Process:**

.. code-block:: python

   async def initialize_mcp_servers():
       """Complete MCP server initialization workflow."""
       
       manager = get_mcp_manager()
       
       try:
           # Start all servers with timeout
           await manager.initialize()
           
           # Verify all servers are healthy
           health_status = await manager.health_check()
           
           failed_servers = [name for name, healthy in health_status.items() if not healthy]
           if failed_servers:
               raise MCPServerError(f"Failed servers: {failed_servers}")
           
           print("All MCP servers initialized successfully")
           
       except asyncio.TimeoutError:
           print("Server initialization timed out")
           await manager.shutdown()
           raise
       except Exception as e:
           print(f"Initialization failed: {e}")
           await manager.shutdown()
           raise

**Graceful Shutdown:**

.. code-block:: python

   async def shutdown_mcp_servers():
       """Gracefully shutdown all MCP servers."""
       
       manager = get_mcp_manager()
       
       try:
           await manager.shutdown()
           print("All MCP servers shut down successfully")
       except Exception as e:
           print(f"Shutdown error: {e}")

**Health Monitoring:**

.. code-block:: python

   async def monitor_server_health():
       """Monitor server health and restart if needed."""
       
       manager = get_mcp_manager()
       
       while True:
           try:
               health_status = await manager.health_check()
               
               for server_name, is_healthy in health_status.items():
                   if not is_healthy:
                       print(f"Server {server_name} is unhealthy, restarting...")
                       await manager.restart_server(server_name)
               
               # Check every 30 seconds
               await asyncio.sleep(30)
               
           except Exception as e:
               print(f"Health check failed: {e}")
               await asyncio.sleep(60)  # Wait longer on error

MCP Integration Patterns
------------------------

**Agent-MCP Integration:**

Agents integrate with MCP servers through the manager:

.. code-block:: python

   from src.agents.base import BaseAgent
   from src.mcp import get_mcp_manager

   class MCPEnabledAgent(BaseAgent):
       def __init__(self, model, server_names: List[str] = None):
           super().__init__(
               name="mcp_agent",
               model=model,
               system_prompt="Agent with MCP server access"
           )
           self.mcp_manager = get_mcp_manager()
           self.server_names = server_names or []
           self._register_tools()

       def _register_tools(self):
           @self.agent.tool
           async def call_mcp_server(server_name: str, tool_name: str, args: dict) -> str:
               """Generic MCP server tool caller."""
               try:
                   server = self.mcp_manager.get_server(server_name)
                   result = await server.call_tool(tool_name, args)
                   return str(result)
               except Exception as e:
                   return f"MCP call failed: {e}"

**Error Handling:**

.. code-block:: python

   from src.core.exceptions import MCPServerError, MCPServerConnectionError

   async def safe_mcp_call(server_name: str, operation: callable):
       """Safely call MCP server with error handling."""
       
       manager = get_mcp_manager()
       
       try:
           server = manager.get_server(server_name)
           return await operation(server)
           
       except MCPServerConnectionError as e:
           # Try to restart server
           try:
               await manager.restart_server(server_name)
               server = manager.get_server(server_name)
               return await operation(server)
           except Exception:
               raise MCPServerError(f"Server {server_name} unavailable: {e}")
               
       except Exception as e:
           raise MCPServerError(f"MCP operation failed: {e}")

**Retry Logic:**

.. code-block:: python

   import asyncio
   from typing import Callable, Any

   async def retry_mcp_operation(
       operation: Callable,
       max_retries: int = 3,
       delay: float = 1.0
   ) -> Any:
       """Retry MCP operations with exponential backoff."""
       
       for attempt in range(max_retries):
           try:
               return await operation()
           except MCPServerConnectionError as e:
               if attempt == max_retries - 1:
                   raise
               
               wait_time = delay * (2 ** attempt)
               print(f"MCP operation failed, retrying in {wait_time}s: {e}")
               await asyncio.sleep(wait_time)

MCP Server Types
---------------

**Brave Search Server:**

.. code-block:: python

   # Available tools:
   brave_tools = [
       "search",           # Web search
       "summarize_url",    # URL content summarization
       "get_trends"        # Search trends
   ]

   # Example usage:
   async def search_web(query: str) -> str:
       server = mcp_manager.get_server("brave")
       result = await server.call_tool("search", {"query": query})
       return result

**Filesystem Server:**

.. code-block:: python

   # Available tools:
   filesystem_tools = [
       "read_file",        # Read file contents
       "write_file",       # Write file contents
       "list_directory",   # List directory contents
       "create_directory", # Create directories
       "delete_file",      # Delete files
       "move_file",        # Move/rename files
       "get_file_info"     # Get file metadata
   ]

   # Example usage:
   async def read_project_file(file_path: str) -> str:
       server = mcp_manager.get_server("filesystem")
       result = await server.call_tool("read_file", {"path": file_path})
       return result

**GitHub Server:**

.. code-block:: python

   # Available tools:
   github_tools = [
       "create_issue",     # Create GitHub issues
       "list_issues",      # List repository issues
       "get_issue",        # Get specific issue
       "update_issue",     # Update issue
       "create_pr",        # Create pull request
       "list_prs",         # List pull requests
       "get_repository"    # Get repository info
   ]

   # Example usage:
   async def create_bug_report(title: str, body: str, repo: str) -> str:
       server = mcp_manager.get_server("github")
       result = await server.call_tool("create_issue", {
           "repository": repo,
           "title": title,
           "body": body,
           "labels": ["bug"]
       })
       return result

**Slack Server:**

.. code-block:: python

   # Available tools:
   slack_tools = [
       "send_message",     # Send message to channel/user
       "list_channels",    # List available channels
       "get_channel_info", # Get channel information
       "upload_file",      # Upload file to Slack
       "get_user_info"     # Get user information
   ]

   # Example usage:
   async def notify_team(channel: str, message: str) -> str:
       server = mcp_manager.get_server("slack")
       result = await server.call_tool("send_message", {
           "channel": channel,
           "text": message
       })
       return result

Advanced MCP Features
--------------------

**Custom Server Registration:**

.. code-block:: python

   class CustomMCPManager(MCPServerManager):
       def register_custom_server(self, name: str, config: Dict[str, Any]):
           """Register a custom MCP server."""
           
           from pydantic_ai.mcp import MCPServerStdio
           
           server = MCPServerStdio(
               command=config["command"],
               args=config["args"], 
               env=config.get("env", {})
           )
           
           self.servers[name] = server

**Middleware Integration:**

.. code-block:: python

   class MCPMiddleware:
       def __init__(self, manager: MCPServerManager):
           self.manager = manager
           self.call_history = []

       async def call_with_logging(self, server_name: str, tool_name: str, args: dict):
           """Call MCP server with request/response logging."""
           
           import time
           start_time = time.time()
           
           try:
               server = self.manager.get_server(server_name)
               result = await server.call_tool(tool_name, args)
               
               duration = time.time() - start_time
               
               self.call_history.append({
                   "server": server_name,
                   "tool": tool_name,
                   "args": args,
                   "success": True,
                   "duration": duration,
                   "timestamp": time.time()
               })
               
               return result
               
           except Exception as e:
               duration = time.time() - start_time
               
               self.call_history.append({
                   "server": server_name,
                   "tool": tool_name,
                   "args": args,
                   "success": False,
                   "error": str(e),
                   "duration": duration,
                   "timestamp": time.time()
               })
               
               raise

**Performance Monitoring:**

.. code-block:: python

   class MCPPerformanceMonitor:
       def __init__(self):
           self.metrics = {
               "total_calls": 0,
               "successful_calls": 0,
               "failed_calls": 0,
               "average_response_time": 0,
               "server_stats": {}
           }

       def record_call(self, server_name: str, success: bool, duration: float):
           """Record MCP call metrics."""
           
           self.metrics["total_calls"] += 1
           
           if success:
               self.metrics["successful_calls"] += 1
           else:
               self.metrics["failed_calls"] += 1
           
           # Update average response time
           total_time = self.metrics["average_response_time"] * (self.metrics["total_calls"] - 1)
           self.metrics["average_response_time"] = (total_time + duration) / self.metrics["total_calls"]
           
           # Update server-specific stats
           if server_name not in self.metrics["server_stats"]:
               self.metrics["server_stats"][server_name] = {
                   "calls": 0,
                   "success_rate": 0,
                   "avg_response_time": 0
               }
           
           server_stats = self.metrics["server_stats"][server_name]
           server_stats["calls"] += 1
           
           # Update server success rate and response time
           # Implementation details...

       def get_performance_report(self) -> Dict[str, Any]:
           """Get comprehensive performance report."""
           return {
               "overall_metrics": self.metrics,
               "success_rate": self.metrics["successful_calls"] / max(self.metrics["total_calls"], 1),
               "health_status": "healthy" if self.metrics["successful_calls"] > self.metrics["failed_calls"] else "degraded"
           }