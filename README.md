# Multi-Agent Automation System with RAG

A sophisticated multi-agent system using the Model Context Protocol (MCP) for automation, quality assurance, and intelligent document processing. The system orchestrates specialized agents to handle various tasks including web search, file management, code analysis, and contextual information retrieval through an enhanced RAG (Retrieval Augmented Generation) system.

## 🚀 Key Features

### **Multi-Agent Architecture**
- **Primary Orchestration Agent**: Intelligently routes requests to specialized subagents
- **Brave Search Agent**: Web search and research capabilities
- **Filesystem Agent**: File and directory management operations  
- **GitHub Agent**: Repository and development workflow integration
- **Slack Agent**: Team communication and notifications
- **Analyzer Agent**: Test report analysis and insights
- **RAG Agent**: Enhanced document indexing and contextual retrieval

### **Enhanced RAG System**
Our RAG (Retrieval Augmented Generation) agent now supports:

#### **Document Indexing Capabilities**
- **Single File Indexing**: Index individual files with intelligent content parsing
- **Directory Indexing**: Recursively process entire directories with filtering options
- **Multi-Format Support**: Handles various text formats (.py, .js, .ts, .html, .css, .md, .txt, .json, .xml, .yaml, .yml, .sh, .sql, .env, etc.)
- **Smart Chunking**: Overlapping text chunks with intelligent boundary detection
- **Rich Metadata**: Tracks file paths, chunk indices, and source information

#### **Advanced Features**
- **ChromaDB Vector Store**: Persistent, high-performance semantic search
- **File Type Detection**: Automatic MIME type and extension-based filtering
- **Recursive Processing**: Optional subdirectory scanning
- **Extension Filtering**: Target specific file types for indexing
- **Error Handling**: Comprehensive error reporting and recovery
- **Batch Processing**: Efficient handling of large directory structures

## 📋 Prerequisites

- Python 3.8+
- Node.js (for MCP servers)
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

4. **Install MCP servers**
   ```bash
   npm install -g @modelcontextprotocol/server-brave-search
   npm install -g @modelcontextprotocol/server-filesystem
   npm install -g @modelcontextprotocol/server-github
   npm install -g @modelcontextprotocol/server-slack
   ```

## ⚙️ Environment Setup

Create a `.env` file in the project root with the following variables:

```env
# Model Configuration
MODEL_CHOICE=gpt-4o-mini
BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_openai_api_key

# Agent API Keys
BRAVE_API_KEY=your_brave_search_api_key
GITHUB_TOKEN=your_github_personal_access_token
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_TEAM_ID=your_slack_team_id

# File System Configuration
LOCAL_FILE_DIR=/path/to/your/local/files
```

### **Required API Keys**

| Service | Purpose | How to Get |
|---------|---------|------------|
| **OpenAI** | Primary language model | [OpenAI API](https://platform.openai.com/api-keys) |
| **Brave Search** | Web search capabilities | [Brave Search API](https://api.search.brave.com/) |
| **GitHub** | Repository access | [GitHub Personal Access Token](https://github.com/settings/tokens) |
| **Slack** | Team communication | [Slack App Dashboard](https://api.slack.com/apps) |

## 🚀 Usage

### **Starting the System**

```bash
python agents.py
```

The system will:
1. Initialize ChromaDB vector store
2. Start all MCP servers
3. Launch interactive chat interface

### **RAG Agent Commands**

#### **Index Single File**
```
Index the file ./src/main.py
```

#### **Index Directory**
```
Index all Python files in the ./src directory recursively
```

#### **Index with File Filtering**
```
Index the ./docs directory but only include .md and .txt files
```

#### **Search Indexed Content**
```
Find information about user authentication in the indexed codebase
```

#### **Add Text Documents**
```
Add this documentation to the knowledge base: [your text content]
```

### **Other Agent Examples**

#### **Web Search**
```
Search for the latest Python best practices
```

#### **File Operations**
```
List all Python files in the current directory
```

#### **GitHub Integration**
```
Get the latest issues from my repository
```

#### **Slack Communication**
```
Send a message to the #general channel about deployment status
```

## 🏗️ Architecture

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

### **Supported File Types**

The RAG system automatically detects and processes:

- **Code Files**: .py, .js, .ts, .html, .css, .sh, .sql
- **Documentation**: .md, .txt, .rst
- **Configuration**: .json, .xml, .yaml, .yml, .env
- **Text Files**: Any file with `text/*` MIME type

## 📊 ChromaDB Features

### **Vector Store Capabilities**
- **Persistent Storage**: Data persists between sessions in `./chroma_db/`
- **Cosine Similarity**: Optimized for semantic search
- **Metadata Filtering**: Search by file type, source, or custom attributes
- **Scalable**: Handles large document collections efficiently

### **Search Quality**
- **Semantic Understanding**: Goes beyond keyword matching
- **Context Preservation**: Overlapping chunks maintain narrative flow
- **Source Attribution**: Every result includes file path and chunk information
- **Relevance Scoring**: Similarity scores help assess result quality

## 🔧 Configuration

### **Chunk Size Configuration**
Adjust text chunking in RAG operations:
- **Default**: 1000 characters
- **Overlap**: 200 characters
- **Customizable**: Specify in indexing commands

### **Search Parameters**
- **Default Results**: 3 most relevant chunks
- **Configurable**: Adjust `n_results` in search queries
- **Similarity Threshold**: ChromaDB handles relevance automatically

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 Troubleshooting

### **Common Issues**

**ChromaDB Initialization Error**
- Ensure write permissions for `./chroma_db/` directory
- Check available disk space

**MCP Server Connection Fails**
- Verify Node.js packages are installed globally
- Check API keys in environment variables

**File Indexing Errors**
- Verify file permissions and existence
- Check supported file formats
- Review error messages in output

**Memory Issues with Large Directories**
- Use file extension filtering
- Process subdirectories separately
- Adjust chunk sizes

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built with** ❤️ **using PydanticAI, ChromaDB, and Model Context Protocol**

