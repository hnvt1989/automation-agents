# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Full application with MCP servers (recommended)
./run.sh
# OR
python -m src.main

# Simple mode (no MCP servers)
./run_simple.sh
# OR
python -m src.main_simple

# Web API server for frontend
uvicorn src.api_server:app --reload
```

### Testing
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test types
pytest tests/unit/      # Unit tests only
pytest tests/integration/  # Integration tests only

# Run single test file
pytest tests/unit/test_planner_agent.py
```

### Code Quality
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/
```

### Environment Setup
Requires `local.env` file with API keys:
```env
MODEL_CHOICE=gpt-4o-mini
LLM_API_KEY=your_openai_api_key
OPENAI_API_KEY=your_openai_api_key
BRAVE_API_KEY=your_brave_search_api_key
GITHUB_TOKEN=your_github_token
SLACK_BOT_TOKEN=your_slack_bot_token
LOCAL_FILE_DIR=/path/to/files
LOCAL_FILE_DIR_KNOWLEDGE_BASE=/path/to/knowledge
```

## Architecture Overview

### Multi-Agent System
This is a PydanticAI-based multi-agent system using Model Context Protocol (MCP) for tool integration. The architecture follows a hub-and-spoke pattern:

- **Primary Agent** (`src/agents/primary.py`) - Main orchestrator that routes requests to specialized agents
- **Specialized Agents** - Each handles specific domains (search, filesystem, RAG, planning, etc.)
- **MCP Integration** (`src/mcp/manager.py`) - Manages external tool servers (GitHub, Slack)
- **Storage Layer** (`src/storage/`) - ChromaDB vector database for RAG functionality

### Key Components

#### Agent Layer (`src/agents/`)
- `primary.py` - Main orchestrator with intelligent routing
- `rag.py` - Enhanced RAG with contextual chunking
- `planner.py` - Task planning and scheduling
- `filesystem.py` - File operations and directory management
- `brave_search.py` - Web search capabilities

#### Storage Layer (`src/storage/`)
- `chromadb_client.py` - Vector database operations
- `contextual_chunker.py` - Intelligent text segmentation
- `collection_manager.py` - Multi-collection RAG management
- `graph_knowledge_manager.py` - Neo4j integration for knowledge graphs

#### Processing Layer (`src/processors/`)
- `image.py` - Vision API integration for calendar/chat screenshots
- `calendar.py` - Calendar event extraction
- `crawler.py` - Web content processing

### Data Flow
```
User Input → Primary Agent → Specialized Agent → MCP Tool/Processor → Storage/External Service
                ↓
         Orchestrated Response ← Processed Result ← Tool Response
```

## Key Patterns

### Agent Structure
All agents follow the PydanticAI pattern:
```python
agent = Agent(
    model=get_model(),
    system_prompt="...",
    deps_type=YourDepsType,
)

@agent.tool
def your_tool(ctx: RunContext[YourDepsType], param: str) -> str:
    # Tool implementation
    pass
```

### MCP Server Management
MCP servers are auto-managed via `npx` - no manual installation required. The system handles GitHub, Slack, and other external tool integrations through standardized MCP protocols.

### RAG Implementation
The RAG system uses multi-collection architecture:
- Contextual chunking with overlap
- Metadata-rich indexing (file paths, chunk indices)
- ChromaDB for vector similarity search
- Support for images, text, and structured data

### Configuration Management
- Core settings in `src/core/config.py`
- Environment variables via `local.env`
- Logging configuration in `src/utils/logging.py`

## Data Files

The system uses YAML files in `data/` directory:
- `tasks.yaml` - Task management with priorities
- `daily_logs.yaml` - Work completion logs
- `meetings.yaml` - Meeting schedules (auto-populated from calendar images)

## Testing Strategy

- **Unit tests** in `tests/unit/` for individual components
- **Integration tests** in `tests/integration/` for agent interactions
- Use `pytest` with async support enabled
- Mock external services in tests
- Coverage target: maintain above 80% for core modules

## Development Guidelines

### Code Style
- Line length: 100 characters (configured in pyproject.toml)
- Use type hints throughout
- Follow PEP 8 with Black formatting
- Import sorting with isort

### Error Handling
- Use structured exceptions from `src/core/exceptions.py`
- Log errors appropriately using configured logger
- Graceful degradation for external service failures

### Adding New Agents
1. Create agent file in `src/agents/`
2. Follow PydanticAI patterns
3. Add tools with proper type hints
4. Register in primary agent's routing logic
5. Add corresponding tests

### MCP Tool Integration
- MCP servers auto-download via `npx`
- Add new tools by updating MCP server configurations
- Test MCP integration in `tests/integration/`