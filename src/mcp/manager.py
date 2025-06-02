"""MCP Server lifecycle management."""
import asyncio
from typing import Dict, Optional, Any, List
from contextlib import AsyncExitStack
from pydantic_ai.mcp import MCPServerStdio

from src.core.config import get_mcp_config, get_settings
from src.core.exceptions import MCPServerStartupError, MCPServerConnectionError
from src.core.constants import MCP_SERVER_STARTUP_TIMEOUT
from src.utils.logging import log_info, log_error, log_warning


class MCPServerManager:
    """Manages MCP server lifecycle and connections."""
    
    def __init__(self):
        """Initialize the MCP server manager."""
        self.config = get_mcp_config()
        self.settings = get_settings()
        self.servers: Dict[str, MCPServerStdio] = {}
        self.exit_stack: Optional[AsyncExitStack] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all MCP servers."""
        if self._initialized:
            log_warning("MCP servers already initialized")
            return
        
        self.exit_stack = AsyncExitStack()
        
        # Create server instances
        self.servers = {
            "brave": MCPServerStdio(
                command=self.config.brave_search["command"],
                args=self.config.brave_search["args"],
                env=self.config.brave_search["env"]
            ),
            "filesystem": MCPServerStdio(
                command=self.config.filesystem["command"],
                args=self.config.filesystem["args"]
            ),
            "github": MCPServerStdio(
                command=self.config.github["command"],
                args=self.config.github["args"],
                env=self.config.github["env"]
            ),
            "slack": MCPServerStdio(
                command=self.config.slack["command"],
                args=self.config.slack["args"],
                env=self.config.slack["env"]
            )
        }
        
        # Start all servers
        for name, server in self.servers.items():
            try:
                log_info(f"Starting MCP server: {name}")
                await self._start_server(name, server)
                log_info(f"Successfully started MCP server: {name}")
            except Exception as e:
                log_error(f"Failed to start MCP server {name}: {str(e)}")
                raise MCPServerStartupError(f"Failed to start MCP server {name}: {str(e)}")
        
        self._initialized = True
        log_info("All MCP servers initialized successfully")
    
    async def _start_server(self, name: str, server: MCPServerStdio) -> None:
        """Start a single MCP server with timeout."""
        try:
            # Use timeout for server startup
            await asyncio.wait_for(
                self.exit_stack.enter_async_context(server),
                timeout=MCP_SERVER_STARTUP_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise MCPServerStartupError(
                f"MCP server {name} startup timed out after {MCP_SERVER_STARTUP_TIMEOUT} seconds"
            )
        except Exception as e:
            raise MCPServerStartupError(f"Failed to start MCP server {name}: {str(e)}")
    
    async def shutdown(self) -> None:
        """Shutdown all MCP servers."""
        if not self._initialized:
            return
        
        log_info("Shutting down MCP servers...")
        
        if self.exit_stack:
            try:
                await self.exit_stack.aclose()
                log_info("All MCP servers shut down successfully")
            except Exception as e:
                log_error(f"Error during MCP server shutdown: {str(e)}")
        
        self.servers.clear()
        self._initialized = False
    
    def get_server(self, name: str) -> MCPServerStdio:
        """Get a specific MCP server instance.
        
        Args:
            name: Name of the server to get
            
        Returns:
            The MCP server instance
            
        Raises:
            MCPServerConnectionError: If server not found or not initialized
        """
        if not self._initialized:
            raise MCPServerConnectionError("MCP servers not initialized")
        
        if name not in self.servers:
            raise MCPServerConnectionError(f"MCP server '{name}' not found")
        
        return self.servers[name]
    
    def get_all_servers(self) -> Dict[str, MCPServerStdio]:
        """Get all MCP server instances.
        
        Returns:
            Dictionary of all MCP servers
            
        Raises:
            MCPServerConnectionError: If servers not initialized
        """
        if not self._initialized:
            raise MCPServerConnectionError("MCP servers not initialized")
        
        return self.servers.copy()
    
    def is_initialized(self) -> bool:
        """Check if MCP servers are initialized."""
        return self._initialized
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all servers.
        
        Returns:
            Dictionary mapping server names to their health status
        """
        health_status = {}
        
        for name, server in self.servers.items():
            try:
                # Try to list tools as a health check
                tools = await server.list_tools()
                health_status[name] = len(tools) > 0
            except Exception:
                health_status[name] = False
        
        return health_status
    
    async def restart_server(self, name: str) -> None:
        """Restart a specific MCP server.
        
        Args:
            name: Name of the server to restart
        """
        if name not in self.servers:
            raise MCPServerConnectionError(f"MCP server '{name}' not found")
        
        log_info(f"Restarting MCP server: {name}")
        
        # For now, we'll need to restart all servers
        # since we're using AsyncExitStack
        await self.shutdown()
        await self.initialize()


# Singleton instance
_mcp_manager: Optional[MCPServerManager] = None


def get_mcp_manager() -> MCPServerManager:
    """Get the MCP server manager singleton."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPServerManager()
    return _mcp_manager