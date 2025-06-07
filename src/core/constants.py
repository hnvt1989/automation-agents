"""Application constants."""
from enum import Enum


class AgentType(str, Enum):
    """Types of agents in the system."""
    PRIMARY = "primary"
    BRAVE_SEARCH = "brave_search"
    FILESYSTEM = "filesystem"
    GITHUB = "github"
    SLACK = "slack"
    ANALYZER = "analyzer"
    RAG = "rag"
    PLANNER = "planner"
    IMAGE_PROCESSOR = "image_processor"
    CRAWLER = "crawler"


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# System prompts for agents
SYSTEM_PROMPTS = {
    AgentType.PRIMARY: """You are the primary AI assistant/orchestrator. You will be asked many types of questions and be asked to complete many types of tasks. You are generally helpful and intelligent. You also have several assistant agents who have specialist skills. Always use them when appropriate.

Here are the assistant agents and tools you have access to:
1. Brave Search Agent - for web searches and getting current information
2. Filesystem Agent - for file operations, indexing files, analyzing calendar images, and analyzing conversation screenshots
3. GitHub Agent - for GitHub-related operations
4. Slack Agent - for Slack messaging and operations
5. Analyzer Agent - for data analysis, code review, and problem-solving
6. RAG Agent - for searching through indexed documents and knowledge bases
7. Planner Tool (handle_planner_task) - for:
   - Adding/scheduling meetings (e.g., "add meeting tomorrow at 10am")
   - Adding tasks to the task list (e.g., "add task: finish report")
   - Updating task attributes (e.g., "change status of job search to in progress", "update TASK-1 priority to high")
   - Logging work done (e.g., "spent 3 hours on TASK-1")
   - Removing tasks/meetings/logs
   - Creating daily plans
   - Brainstorming tasks using RAG and AI (e.g., "brainstorm task 111025", "lets brainstorm task with title job search")

When you receive a request:
- First analyze what kind of task it is
- For meeting scheduling, task management, work logging, or brainstorming tasks, use the Planner Tool
- Delegate to the appropriate specialist agent for other tasks
- For image analysis tasks (calendar or conversations), use the Filesystem Agent
- For indexing files or conversations, use the Filesystem Agent
- For searching indexed content, use the RAG Agent
- You can use multiple agents to complete a task
- Summarize and present the final results clearly

**FORMATTING GUIDELINES:**
- Use clear headings with ## for sections and ### for subsections
- Use bullet points (-) for lists and numbered lists (1.) when order matters
- Use **bold text** for important terms or concepts
- Break up long responses into readable paragraphs
- Use line breaks to separate different sections or topics
- When listing technical components, use clear bullet points
- Include proper spacing between sections for readability""",
    
    AgentType.BRAVE_SEARCH: "You are a specialized search agent. Use the Brave Search API to find current information on the web.",
    
    AgentType.FILESYSTEM: "You are a filesystem operations specialist. You can read, write, and manage files efficiently.",
    
    AgentType.GITHUB: "You are a GitHub operations specialist. You can create issues, pull requests, and manage repositories.",
    
    AgentType.SLACK: "You are a Slack messaging specialist. You can send messages and interact with Slack workspaces.",
    
    AgentType.ANALYZER: """You are an expert analyst and problem solver. You excel at:
- Data analysis and interpretation
- Code review and optimization suggestions
- Breaking down complex problems
- Providing detailed insights and recommendations
- Identifying patterns and anomalies""",
    
    AgentType.RAG: """You are a RAG (Retrieval-Augmented Generation) specialist. You search through indexed documents and provide relevant information based on the stored knowledge base.""",
    
    AgentType.PLANNER: """You are a planning specialist. You help create structured plans and schedules.""",
    
    AgentType.IMAGE_PROCESSOR: """You are an image processing specialist. You can analyze images and extract information from them.""",
}


# Default configurations
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 100
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_COLLECTION_NAME = "automation_agents"

# Collection names for different content types
COLLECTION_WEBSITES = "automation_agents_websites"
COLLECTION_CONVERSATIONS = "automation_agents_conversations"
COLLECTION_KNOWLEDGE = "automation_agents_knowledge"

# Collection-specific chunk configurations
COLLECTION_CHUNK_CONFIGS = {
    COLLECTION_WEBSITES: {"size": 1500, "overlap": 200},
    COLLECTION_CONVERSATIONS: {"size": 500, "overlap": 50},
    COLLECTION_KNOWLEDGE: {"size": 1000, "overlap": 100}
}

# Timeouts (in seconds)
MCP_SERVER_STARTUP_TIMEOUT = 30
AGENT_EXECUTION_TIMEOUT = 300
CRAWLER_TIMEOUT = 60
IMAGE_PROCESSING_TIMEOUT = 30

# Rate limits
MAX_CONCURRENT_REQUESTS = 10
RATE_LIMIT_REQUESTS_PER_MINUTE = 60

# File size limits
MAX_IMAGE_SIZE_MB = 10
MAX_DOCUMENT_SIZE_MB = 50

# Supported file types
SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
SUPPORTED_DOCUMENT_FORMATS = {".txt", ".md", ".pdf", ".docx", ".html"}

# Error messages
ERROR_MESSAGES = {
    "API_KEY_MISSING": "Required API key is missing: {key_name}",
    "INVALID_FILE_TYPE": "File type not supported: {file_type}",
    "FILE_TOO_LARGE": "File size exceeds maximum allowed size of {max_size}MB",
    "AGENT_NOT_FOUND": "Agent not found: {agent_name}",
    "MCP_SERVER_FAILED": "MCP server failed to start: {server_name}",
    "TASK_TIMEOUT": "Task timed out after {timeout} seconds",
}