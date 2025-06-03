# C4 Model - Level 3: Component Diagram

```mermaid
C4Component
    title Component Diagram - Primary Agent Container
    
    Container_Boundary(primary_container, "Primary Agent Container") {
        Component(cli_interface, "CLI Interface", "Rich Console", "Interactive command-line interface with prompts and markdown rendering")
        Component(primary_agent, "Primary Agent", "PydanticAI Agent", "Central orchestrator with delegation tools")
        
        ComponentDb(agent_registry, "Agent Registry", "Dict[str, BaseAgent]", "Registry of available specialized agents")
        
        Component_Boundary(orchestration_tools, "Orchestration Tools") {
            Component(brave_delegator, "Brave Search Delegator", "Tool Function", "Delegates search queries to Brave Search agent")
            Component(filesystem_delegator, "Filesystem Delegator", "Tool Function", "Delegates file operations to Filesystem agent")
            Component(rag_delegator, "RAG Delegator", "Tool Function", "Delegates knowledge queries to RAG agent")
            Component(github_delegator, "GitHub Delegator", "Tool Function", "Delegates GitHub tasks to GitHub agent")
            Component(slack_delegator, "Slack Delegator", "Tool Function", "Delegates messaging to Slack agent")
            Component(planner_handler, "Planner Handler", "Tool Function", "Handles planning and task management directly")
        }
        
        Component_Boundary(planner_components, "Planner Components") {
            Component(planner_parser, "Planner Parser", "PydanticAI Agent", "Parses natural language into structured actions")
            Component(planner_ops, "Planner Operations", "Python Class", "Executes CRUD operations on tasks/meetings")
            Component(task_searcher, "Task Searcher", "Python Methods", "Keyword and LLM-based task search")
        }
    }
    
    Container_Boundary(specialized_agents, "Specialized Agents") {
        Component(brave_agent, "Brave Search Agent", "BaseAgent + Tools", "Web search with MCP server integration")
        Component(filesystem_agent, "Filesystem Agent", "BaseAgent + Tools", "File operations with MCP server integration")
        Component(rag_agent, "RAG Agent", "BaseAgent + Tools", "Knowledge base search and document management")
    }
    
    Container_Boundary(mcp_container, "MCP Manager Container") {
        Component(mcp_manager, "MCP Manager", "Python Class", "Manages MCP server lifecycle")
        Component(server_registry, "Server Registry", "Dict[str, MCPServerStdio]", "Registry of active MCP servers")
        Component(exit_stack, "Exit Stack", "AsyncExitStack", "Manages async context for server cleanup")
        
        Component_Boundary(health_monitoring, "Health Monitoring") {
            Component(health_checker, "Health Checker", "Async Method", "Monitors server health status")
            Component(restart_handler, "Restart Handler", "Async Method", "Handles server restart operations")
        }
    }
    
    Container_Boundary(storage_container, "Storage Container") {
        ComponentDb(vector_db, "ChromaDB Client", "ChromaDB", "Vector database for embeddings and semantic search")
        ComponentDb(yaml_storage, "YAML Storage", "File System", "Persistent storage for tasks, logs, meetings")
    }
    
    %% User interactions
    Rel(cli_interface, primary_agent, "Delegates", "User commands and queries")
    
    %% Primary agent to registry
    Rel(primary_agent, agent_registry, "Accesses", "Available agents")
    
    %% Primary agent to tools
    Rel(primary_agent, brave_delegator, "Uses", "Search delegation")
    Rel(primary_agent, filesystem_delegator, "Uses", "File delegation")
    Rel(primary_agent, rag_delegator, "Uses", "Knowledge delegation")
    Rel(primary_agent, github_delegator, "Uses", "GitHub delegation")
    Rel(primary_agent, slack_delegator, "Uses", "Slack delegation")
    Rel(primary_agent, planner_handler, "Uses", "Planning tasks")
    
    %% Delegation to agents
    Rel(brave_delegator, brave_agent, "Calls", "Search requests")
    Rel(filesystem_delegator, filesystem_agent, "Calls", "File operations")
    Rel(rag_delegator, rag_agent, "Calls", "Knowledge queries")
    
    %% Planner components
    Rel(planner_handler, planner_parser, "Uses", "Natural language parsing")
    Rel(planner_handler, planner_ops, "Uses", "Task/meeting operations")
    Rel(planner_handler, task_searcher, "Uses", "Task search functionality")
    
    %% Agent to MCP Manager
    Rel(brave_agent, mcp_manager, "Uses", "Server connections")
    Rel(filesystem_agent, mcp_manager, "Uses", "Server connections")
    
    %% MCP Manager internals
    Rel(mcp_manager, server_registry, "Manages", "Server instances")
    Rel(mcp_manager, exit_stack, "Uses", "Context management")
    Rel(mcp_manager, health_checker, "Uses", "Health monitoring")
    Rel(mcp_manager, restart_handler, "Uses", "Server restart")
    
    %% Storage connections
    Rel(rag_agent, vector_db, "Queries", "Vector search")
    Rel(planner_ops, yaml_storage, "Reads/Writes", "Task/meeting data")
    
    %% Search components
    Rel(task_searcher, primary_agent, "Uses", "LLM for semantic search")
    
    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

## Component Overview

### **CLI Interface Component**
- **Responsibility**: User interaction management
- **Technology**: Rich Console library
- **Key Features**:
  - Interactive prompts with auto-completion
  - Markdown rendering for responses
  - Panel-based UI with syntax highlighting
  - Error handling and graceful shutdown

### **Primary Agent Orchestration**
- **Primary Agent**: Central coordinator implementing delegation pattern
- **Agent Registry**: Dynamic registry of available specialized agents
- **Orchestration Tools**: Collection of tool functions for delegation:
  - Each delegator is a decorated tool function
  - Handles error propagation and logging
  - Provides consistent interface for agent communication

### **Planner Components**
- **Planner Parser**: NLP-to-action converter using PydanticAI
- **Planner Operations**: CRUD operations for tasks/meetings
- **Task Searcher**: Dual search strategy (keyword + LLM)

### **MCP Manager Components**
- **MCP Manager**: Lifecycle management for external servers
- **Server Registry**: Active server instance tracking
- **Exit Stack**: Async context management for cleanup
- **Health Monitoring**: Server status tracking and recovery

### **Storage Components**
- **ChromaDB Client**: Vector operations and similarity search
- **YAML Storage**: Structured data persistence

## Design Patterns

### **Delegation Pattern**
- Primary agent uses tool functions to delegate to specialized agents
- Each delegation tool handles error catching and logging
- Consistent return format across all delegations

### **Registry Pattern**
- Agent registry enables dynamic agent discovery
- Server registry manages MCP server lifecycle
- Both registries support runtime modifications

### **Strategy Pattern**
- Task searching supports multiple strategies (keyword vs LLM)
- Automatic strategy selection based on query complexity
- Fallback mechanisms for robustness

### **Context Manager Pattern**
- AsyncExitStack for proper async resource cleanup
- MCP servers managed as async contexts
- Graceful shutdown handling

## Error Handling

- **Graceful Degradation**: Failed agents don't crash the system
- **Fallback Mechanisms**: LLM search falls back to keyword search
- **Error Propagation**: Structured error responses maintain user experience
- **Logging Integration**: Comprehensive logging at component boundaries