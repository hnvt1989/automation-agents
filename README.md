# Multi-Agent Automation System with RAG

A sophisticated multi-agent system using the Model Context Protocol (MCP) for automation, quality assurance, and intelligent document processing. The system orchestrates specialized agents to handle various tasks including web search, file management, code analysis, and contextual information retrieval through an enhanced RAG (Retrieval Augmented Generation) system.

## 🚀 Key Features

### **Multi-Agent Architecture**
- **Primary Orchestration Agent**: Intelligently routes requests to specialized subagents
- **Brave Search Agent**: Web search and research capabilities
- **Filesystem Agent**: File and directory management, document indexing, and image analysis (calendar & conversations)
- **GitHub Agent**: Repository and development workflow integration
- **Slack Agent**: Team communication and notifications
- **Analyzer Agent**: Test report analysis and insights
- **RAG Agent**: Enhanced document search and contextual retrieval

### **Enhanced RAG System**
Our RAG (Retrieval Augmented Generation) agent supports:

#### **Document Indexing Capabilities**
- **Single File Indexing**: Index individual files with intelligent content parsing
- **Directory Indexing**: Recursively process entire directories with filtering options
- **Multi-Format Support**: Handles various text formats (.py, .js, .ts, .html, .css, .md, .txt, .json, .xml, .yaml, .yml, .sh, .sql, .env, etc.)
- **Smart Chunking**: Overlapping text chunks with intelligent boundary detection
- **Rich Metadata**: Tracks file paths, chunk indices, and source information

#### **Image Analysis Features**
- **Calendar Screenshot Analysis**: Extract events from calendar images using OpenAI Vision API
- **Conversation Screenshot Analysis**: Parse chat conversations and index them for retrieval
- **Automatic Text Extraction**: Convert images to searchable text

#### **Advanced Features**
- **ChromaDB Vector Store**: Persistent, high-performance semantic search
- **File Type Detection**: Automatic MIME type and extension-based filtering
- **Recursive Processing**: Optional subdirectory scanning
- **Extension Filtering**: Target specific file types for indexing
- **Error Handling**: Comprehensive error reporting and recovery
- **Batch Processing**: Efficient handling of large directory structures

## 📋 Prerequisites

- Python 3.8+
- Node.js and npm (for MCP servers)
- Required API keys (see Environment Setup)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd automation-agents
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **For development (optional)**
   ```bash
   pip install -r requirements-dev.txt
   pip install -e .  # Install package in development mode
   ```

## ⚙️ Environment Setup

Create a `local.env` file in the project root with the following variables:

```env
# Model Configuration
MODEL_CHOICE=gpt-4o-mini
BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_openai_api_key
OPENAI_API_KEY=your_openai_api_key  # For embeddings
VISION_LLM_MODEL=gpt-4o  # For image analysis

# Agent API Keys
BRAVE_API_KEY=your_brave_search_api_key
GITHUB_TOKEN=your_github_personal_access_token
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_APP_TOKEN=your_slack_app_token
SLACK_TEAM_ID=your_slack_team_id

# File System Configuration
LOCAL_FILE_DIR=/path/to/your/local/files
LOCAL_FILE_DIR_KNOWLEDGE_BASE=/path/to/knowledge/base

# Optional Configuration
DEBUG=false
LOG_LEVEL=INFO
```

### **Required API Keys**

| Service | Purpose | How to Get |
|---------|---------|------------|
| **OpenAI** | Primary language model & vision | [OpenAI API](https://platform.openai.com/api-keys) |
| **Brave Search** | Web search capabilities | [Brave Search API](https://api.search.brave.com/) |
| **GitHub** | Repository access | [GitHub Personal Access Token](https://github.com/settings/tokens) |
| **Slack** | Team communication | [Slack App Dashboard](https://api.slack.com/apps) |

## 🚀 Usage

### **Starting the System**

**Option 1: New Modular Application (Recommended)**
```bash
./run.sh
# Or directly:
python -m src.main
```

**Option 2: Simple Mode (without MCP servers)**
```bash
./run_simple.sh
# Or directly:
python -m src.main_simple
```

**Option 3: Legacy Mode**
```bash
python agents.py
```

The system will:
1. Initialize ChromaDB vector store
2. Start all MCP servers (using npx to auto-download if needed)
3. Launch interactive chat interface

### **Core Commands**

#### **File Indexing**
```
# Index a single file
index the file at /path/to/document.txt

# Index a directory
index all Python files in ./src directory

# Index with filtering
index all .md and .txt files in ./docs directory
```

#### **Document Search**
```
# Search indexed content
what is Huy's job title?

# Search with context
find information about authentication in the codebase
```

#### **Image Analysis**

**Calendar Events:**
```
analyze the image data/calendar.png and write the calendar events to data/meetings.yaml
```

**Conversation Analysis:**
```
analyze the conversations from data/chat.png and index to the knowledge base
```

#### **Planning**
```
# Create daily plan
plan

# Plan for specific date
plan tomorrow
plan 2025-01-15
```

### **Other Agent Examples**

#### **Web Search**
```
Search for the latest Python best practices
```

#### **File Operations**
```
List all Python files in the current directory
Create a file summary.txt with the project overview
```

#### **GitHub Integration**
```
Get the latest issues from my repository
Create a new issue about the bug in authentication
```

#### **Slack Communication**
```
Send a message to the #general channel about deployment status
```

## 🏗️ Architecture

### **Project Structure**
```
automation-agents/
├── src/
│   ├── agents/          # Individual agent implementations
│   ├── core/            # Configuration, constants, exceptions
│   ├── mcp/             # MCP server management
│   ├── processors/      # Data processors (crawler, image, calendar)
│   ├── storage/         # Storage layer (ChromaDB)
│   ├── utils/           # Utilities (logging)
│   └── main.py          # Main application entry point
├── tests/               # Test suite
├── data/                # Data files (tasks, logs, meetings)
├── docs/                # Documentation
├── scripts/             # Utility scripts
└── requirements.txt     # Python dependencies
```

### **Agent Communication Flow**
```
User Input → Primary Agent → Specialized Subagent → External Service/Tool
                ↓
         Orchestrated Response ← Processed Result ← Service Response
```

### **RAG System Architecture**
```
Files/Directories → Content Reader → Text Chunker → ChromaDB → Vector Search → Context Retrieval
```

## 📊 Data Files

The system uses YAML files in the `data/` directory:

- **tasks.yaml**: Task management with priorities and due dates
- **daily_logs.yaml**: Completed work logs
- **meetings.yaml**: Meeting schedule (can be auto-populated from calendar images)

## 🔧 Configuration

### **Logging**
Logs are stored in the `logs/` directory with rotation. Configure log level via `LOG_LEVEL` environment variable.

### **ChromaDB**
Vector database files are stored in `chroma_db/` directory. The database persists between sessions.

### **MCP Servers**
MCP servers are automatically managed using `npx`. No manual installation required - they download on first use.

## 🧪 Testing

Run tests with:
```bash
pytest tests/
```

For coverage report:
```bash
pytest tests/ --cov=src --cov-report=html
```

## 🔧 Development

### **Code Quality**
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

### **Pre-commit Hooks**
```bash
pre-commit install
pre-commit run --all-files
```

## 📝 Troubleshooting

### **Common Issues**

**MCP Server Connection Fails**
- The system uses `npx` to auto-download MCP servers
- Ensure Node.js and npm are installed
- Check API keys in environment variables

**ChromaDB Initialization Error**
- Ensure write permissions for `./chroma_db/` directory
- Check available disk space

**Image Analysis Not Working**
- Verify OPENAI_API_KEY is set
- Check VISION_LLM_MODEL is set (default: gpt-4o)
- Ensure image files exist and are readable

**Planning Feature Issues**
- Ensure data/*.yaml files exist
- Check date formats in YAML files

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the code style
4. Add tests for new functionality
5. Run tests and code quality checks
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🚀 Migration from Legacy Code

If you're migrating from the monolithic `agents.py`:
1. The new structure provides better modularity and maintainability
2. All functionality has been preserved
3. See `MIGRATION.md` for detailed migration instructions

---

**Built with** ❤️ **using PydanticAI, ChromaDB, and Model Context Protocol**