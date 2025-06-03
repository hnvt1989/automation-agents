"""Custom exceptions for the automation agents system."""


class AutomationAgentError(Exception):
    """Base exception for all automation agent errors."""
    pass


class AgentError(AutomationAgentError):
    """Base exception for agent-related errors."""
    pass


class AgentInitializationError(AgentError):
    """Raised when an agent fails to initialize."""
    pass


class AgentExecutionError(AgentError):
    """Raised when an agent fails during execution."""
    pass


class MCPServerError(AutomationAgentError):
    """Base exception for MCP server errors."""
    pass


class MCPServerStartupError(MCPServerError):
    """Raised when an MCP server fails to start."""
    pass


class MCPServerConnectionError(MCPServerError):
    """Raised when connection to MCP server fails."""
    pass


class ConfigurationError(AutomationAgentError):
    """Raised when there's a configuration error."""
    pass


class ValidationError(AutomationAgentError):
    """Raised when input validation fails."""
    pass


class StorageError(AutomationAgentError):
    """Base exception for storage-related errors."""
    pass


class ChromaDBError(StorageError):
    """Raised when ChromaDB operations fail."""
    pass


class ProcessingError(AutomationAgentError):
    """Base exception for processing errors."""
    pass


class ImageProcessingError(ProcessingError):
    """Raised when image processing fails."""
    pass


class CrawlerError(ProcessingError):
    """Raised when web crawling fails."""
    pass


class PlannerError(ProcessingError):
    """Raised when planning operations fail."""
    pass