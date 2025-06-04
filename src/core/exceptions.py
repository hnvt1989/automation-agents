"""Custom exceptions for the automation agents system."""


class AutomationAgentError(Exception):
    """Base exception for all automation agent errors."""
    pass


class AgentError(AutomationAgentError):
    """Base exception for agent-related errors."""
    pass


class MCPError(AutomationAgentError):
    """Exception for MCP-related errors."""
    pass


class MCPServerError(MCPError):
    """Exception for MCP server-related errors."""
    pass


class MCPServerStartupError(MCPServerError):
    """Exception for MCP server startup errors."""
    pass


class MCPServerConnectionError(MCPServerError):
    """Exception for MCP server connection errors."""
    pass


class ChromaDBError(AutomationAgentError):
    """Exception for ChromaDB-related errors."""
    pass


class GraphDBError(AutomationAgentError):
    """Exception for Graph database (Neo4j) related errors."""
    pass


class ConfigurationError(AutomationAgentError):
    """Exception for configuration-related errors."""
    pass


class ValidationError(AutomationAgentError):
    """Exception for validation errors."""
    pass


class StorageError(AutomationAgentError):
    """Exception for storage-related errors."""
    pass


class ProcessingError(AutomationAgentError):
    """Exception for processing-related errors."""
    pass