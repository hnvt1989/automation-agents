Agents
======

The agents module contains the core agent implementations, including the base agent class and all specialized agents for different tasks.

Base Agent (:mod:`src.agents.base`)
------------------------------------

The base agent provides common functionality for all agents in the system.

.. automodule:: src.agents.base
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: src.agents.base.BaseAgent
   :members:
   :undoc-members:
   :show-inheritance:

   **Key Methods:**

   .. automethod:: src.agents.base.BaseAgent.__init__
   .. automethod:: src.agents.base.BaseAgent.run
   .. automethod:: src.agents.base.BaseAgent.run_stream

**Usage Example:**

.. code-block:: python

   from src.agents.base import BaseAgent
   from pydantic_ai.models.openai import OpenAIModel

   class CustomAgent(BaseAgent):
       def __init__(self, model: OpenAIModel):
           super().__init__(
               name="custom_agent",
               model=model,
               system_prompt="You are a helpful assistant."
           )

Primary Agent (:mod:`src.agents.primary`)
------------------------------------------

The primary agent orchestrates requests and delegates to specialized agents.

.. automodule:: src.agents.primary
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: src.agents.primary.PrimaryAgent
   :members:
   :undoc-members:
   :show-inheritance:

   The primary agent implements a delegation pattern, using tool functions to route requests to appropriate specialized agents.

.. autoclass:: src.agents.primary.PrimaryAgentDeps
   :members:
   :undoc-members:
   :show-inheritance:

**Delegation Tools:**

The primary agent includes several delegation tools:

- ``delegate_to_brave_search``: Routes search queries to Brave Search agent
- ``delegate_to_filesystem``: Routes file operations to Filesystem agent  
- ``delegate_to_rag``: Routes knowledge queries to RAG agent
- ``delegate_to_github``: Routes GitHub tasks to GitHub agent
- ``delegate_to_slack``: Routes messaging to Slack agent
- ``handle_planner_task``: Handles planning and task management directly

**Usage Example:**

.. code-block:: python

   from src.agents.primary import PrimaryAgent
   from src.agents.rag import RAGAgent
   from src.agents.brave_search import BraveSearchAgent

   # Create specialized agents
   agents = {
       "rag": RAGAgent(model),
       "brave_search": BraveSearchAgent(model)
   }

   # Create primary agent
   primary_agent = PrimaryAgent(model, agents)

   # Run a query - will be automatically delegated
   result = await primary_agent.run("Search for Python documentation")

RAG Agent (:mod:`src.agents.rag`)
----------------------------------

The RAG (Retrieval-Augmented Generation) agent handles knowledge base search and document retrieval.

.. automodule:: src.agents.rag
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: src.agents.rag.RAGAgent
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: src.agents.rag.RAGAgentDeps
   :members:
   :undoc-members:
   :show-inheritance:

**RAG Tools:**

- ``search_knowledge_base``: Semantic search through indexed documents
- ``get_collection_stats``: Statistics about the knowledge base
- ``list_recent_documents``: List recently indexed documents

**Usage Example:**

.. code-block:: python

   from src.agents.rag import RAGAgent

   # Initialize RAG agent
   rag_agent = RAGAgent(model)

   # Search knowledge base
   result = await rag_agent.run("Find information about authentication")

   # The agent will use vector similarity search to find relevant documents

Brave Search Agent (:mod:`src.agents.brave_search`)
----------------------------------------------------

The Brave Search agent provides web search capabilities through the Brave Search API.

.. automodule:: src.agents.brave_search
   :members:
   :undoc-members:
   :show-inheritance:

**Features:**

- Web search through Brave Search API
- MCP server integration for external API calls
- Result formatting and filtering

**Usage Example:**

.. code-block:: python

   from src.agents.brave_search import BraveSearchAgent

   # Initialize agent
   brave_agent = BraveSearchAgent(model)

   # Perform web search
   result = await brave_agent.run("Latest Python 3.12 features")

Filesystem Agent (:mod:`src.agents.filesystem`)
------------------------------------------------

The Filesystem agent handles file and directory operations.

.. automodule:: src.agents.filesystem
   :members:
   :undoc-members:
   :show-inheritance:

**Features:**

- File reading, writing, and management
- Directory operations
- Integration with local file system through MCP
- Support for various file formats

**Usage Example:**

.. code-block:: python

   from src.agents.filesystem import FilesystemAgent

   # Initialize agent
   fs_agent = FilesystemAgent(model)

   # File operations
   result = await fs_agent.run("List all Python files in the src directory")

Planner Module (:mod:`src.agents.planner`)
-------------------------------------------

The planner module provides task management and scheduling functionality.

.. automodule:: src.agents.planner
   :members:
   :undoc-members:
   :show-inheritance:

**Key Functions:**

.. autofunction:: src.agents.planner.plan_day

**Usage Example:**

.. code-block:: python

   from src.agents.planner import plan_day

   payload = {
       'paths': {
           'tasks': 'data/tasks.yaml',
           'logs': 'data/daily_logs.yaml', 
           'meets': 'data/meetings.yaml'
       },
       'target_date': '2024-03-15',
       'work_hours': {'start': '09:00', 'end': '17:00'}
   }

   plan = plan_day(payload)

Planner Operations (:mod:`src.agents.planner_ops`)
---------------------------------------------------

The planner operations module provides CRUD operations for tasks and meetings.

.. automodule:: src.agents.planner_ops
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: src.agents.planner_ops.PlannerOperations
   :members:
   :undoc-members:
   :show-inheritance:

**Key Methods:**

- ``add_task``: Add new tasks to the system
- ``update_task``: Update existing tasks
- ``remove_task``: Remove tasks
- ``add_meeting``: Schedule new meetings
- ``remove_meeting``: Cancel meetings
- ``add_log``: Log work completion

Planner Parser (:mod:`src.agents.planner_parser`)
--------------------------------------------------

The planner parser converts natural language into structured planning actions.

.. automodule:: src.agents.planner_parser
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: src.agents.planner_parser.PlannerParser
   :members:
   :undoc-members:
   :show-inheritance:

**Features:**

- Natural language understanding for planning tasks
- Conversion to structured action objects
- Support for complex scheduling and task management requests

Agent Design Patterns
----------------------

**Delegation Pattern**
   The primary agent uses delegation to route requests to specialized agents, providing a unified interface while maintaining separation of concerns.

**Tool-Based Architecture**
   Agents use PydanticAI's tool system to expose capabilities, enabling flexible composition and extension.

**Dependency Injection**
   Agents receive their dependencies (like database clients) through dependency injection, improving testability and flexibility.

**Error Handling**
   All agents implement consistent error handling with graceful degradation and informative error messages.

**Example Agent Implementation:**

.. code-block:: python

   from src.agents.base import BaseAgent
   from pydantic import BaseModel
   from pydantic_ai import RunContext

   class MyAgentDeps(BaseModel):
       some_service: Any = None
       class Config:
           arbitrary_types_allowed = True

   class MyAgent(BaseAgent):
       def __init__(self, model, some_service):
           super().__init__(
               name="my_agent",
               model=model,
               system_prompt="Custom system prompt",
               deps_type=MyAgentDeps
           )
           self.some_service = some_service
           self._register_tools()

       def _register_tools(self):
           @self.agent.tool
           async def my_tool(ctx: RunContext[MyAgentDeps], param: str) -> str:
               # Tool implementation
               return await ctx.deps.some_service.process(param)

       async def run(self, prompt: str, **kwargs):
           deps = MyAgentDeps(some_service=self.some_service)
           return await super().run(prompt, deps=deps, **kwargs)