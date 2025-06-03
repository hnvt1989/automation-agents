Examples
========

This section provides practical examples and use cases for the Multi-Agent Automation System.

.. toctree::
   :maxdepth: 2
   :caption: Examples:

   basic_usage
   agent_interactions
   rag_workflows
   planning_examples
   integration_examples
   advanced_scenarios

Quick Examples
--------------

**Basic Search Query**

.. code-block:: bash

   # Start the system
   ./run.sh

   # In the CLI, perform a web search
   You: Search for the latest Python 3.12 features

   # The system will delegate to Brave Search agent and return results

**Document Indexing**

.. code-block:: bash

   # Index a single file
   You: index the file at ./README.md

   # Index a directory
   You: index all Python files in the src directory

   # Search indexed content
   You: what is the authentication flow in the codebase?

**Task Management**

.. code-block:: bash

   # Add a task
   You: add a high priority task to implement user authentication due tomorrow

   # List tasks
   You: show me all my pending tasks

   # Create a daily plan
   You: plan today

Common Use Cases
---------------

**1. Code Analysis and Documentation**

.. code-block:: python

   # Example workflow for analyzing a codebase

   # Step 1: Index the entire codebase
   await rag_agent.run("index all Python files in ./src directory")

   # Step 2: Ask questions about the code
   await primary_agent.run("What design patterns are used in this codebase?")
   await primary_agent.run("Find all the authentication-related functions")
   await primary_agent.run("What are the main entry points of the application?")

**2. Research and Information Gathering**

.. code-block:: bash

   # Research workflow
   You: Search for best practices in microservices architecture
   You: Find recent articles about Python async programming
   You: What are the latest security vulnerabilities in Node.js?

**3. Project Management**

.. code-block:: bash

   # Project planning
   You: add a task to review pull requests with high priority due Friday
   You: schedule a team meeting for tomorrow at 2 PM about sprint planning
   You: log 3 hours of work on authentication implementation
   You: plan next week

**4. File and Document Management**

.. code-block:: bash

   # File operations
   You: list all configuration files in the project
   You: create a summary of the project structure
   You: analyze the image at ./docs/architecture.png and extract the diagram elements

**5. Team Communication**

.. code-block:: bash

   # Slack integration
   You: send a message to #general channel about the deployment status
   You: notify the team about the code review completion

Agent Interaction Examples
--------------------------

**RAG Agent Workflow**

.. code-block:: python

   from src.agents.rag import RAGAgent
   from src.storage.chromadb_client import get_chromadb_client

   # Initialize RAG agent
   rag_agent = RAGAgent(model)

   # Index documents
   await rag_agent.run("""
   Index all markdown files in the docs directory and 
   all Python files in the src directory
   """)

   # Search for specific information
   result = await rag_agent.run("""
   Find information about error handling patterns 
   in the codebase
   """)

   # Get collection statistics
   stats_result = await rag_agent.run("Show me statistics about the knowledge base")

**Primary Agent Orchestration**

.. code-block:: python

   from src.agents.primary import PrimaryAgent

   # The primary agent automatically delegates to appropriate agents
   
   # This will go to Brave Search agent
   search_result = await primary_agent.run("Search for Python testing frameworks")
   
   # This will go to RAG agent
   code_result = await primary_agent.run("Find all functions that handle user input")
   
   # This will go to Filesystem agent
   file_result = await primary_agent.run("List all JSON files in the config directory")
   
   # This will go to Planner
   plan_result = await primary_agent.run("Add a task to update documentation")

Advanced Workflows
-----------------

**1. Automated Code Review Workflow**

.. code-block:: python

   async def code_review_workflow(file_path: str):
       """Automated code review using multiple agents."""
       
       # Step 1: Read the file
       file_content = await filesystem_agent.run(f"read file {file_path}")
       
       # Step 2: Analyze code quality
       analysis = await primary_agent.run(f"""
       Analyze this code for:
       - Code quality and best practices
       - Potential security issues  
       - Performance considerations
       - Documentation completeness
       
       Code: {file_content}
       """)
       
       # Step 3: Search for similar patterns in codebase
       patterns = await rag_agent.run(f"""
       Find similar code patterns in the codebase to: {file_path}
       """)
       
       # Step 4: Create review summary
       summary = await primary_agent.run(f"""
       Create a code review summary based on:
       Analysis: {analysis}
       Similar patterns: {patterns}
       """)
       
       return summary

**2. Documentation Generation Workflow**

.. code-block:: python

   async def generate_documentation(module_path: str):
       """Generate documentation for a Python module."""
       
       # Step 1: Index the module
       await rag_agent.run(f"index all files in {module_path}")
       
       # Step 2: Extract module structure
       structure = await rag_agent.run(f"""
       Extract the structure of {module_path} including:
       - All classes and their methods
       - All functions
       - Module dependencies
       """)
       
       # Step 3: Generate documentation
       docs = await primary_agent.run(f"""
       Generate comprehensive documentation for the module at {module_path}
       including:
       - Overview and purpose
       - API reference
       - Usage examples
       - Dependencies
       
       Module structure: {structure}
       """)
       
       # Step 4: Save documentation
       await filesystem_agent.run(f"""
       Create a file docs/{module_path}_api.md with content: {docs}
       """)

**3. Project Analysis Workflow**

.. code-block:: python

   async def analyze_project():
       """Comprehensive project analysis."""
       
       # Index entire project
       await rag_agent.run("index all source files in the project")
       
       # Analyze architecture
       architecture = await rag_agent.run("""
       Analyze the project architecture:
       - Main components and their relationships
       - Design patterns used
       - Data flow
       """)
       
       # Find potential issues
       issues = await rag_agent.run("""
       Identify potential issues:
       - Code smells
       - Unused imports or functions
       - Missing error handling
       - Security concerns
       """)
       
       # Generate improvement suggestions
       suggestions = await primary_agent.run(f"""
       Based on this analysis:
       Architecture: {architecture}
       Issues: {issues}
       
       Provide specific improvement suggestions with priorities
       """)
       
       return {
           "architecture": architecture,
           "issues": issues,
           "suggestions": suggestions
       }

Image Analysis Examples
----------------------

**Calendar Analysis**

.. code-block:: python

   # Analyze calendar screenshot
   await primary_agent.run("""
   analyze the image at ./data/calendar_march.png and 
   extract all meeting events, then save them to data/meetings.yaml
   """)

**Conversation Analysis**

.. code-block:: python

   # Process chat screenshots
   await primary_agent.run("""
   analyze the conversation screenshot at ./data/team_chat.png,
   extract the messages and index them in the knowledge base
   """)

**Diagram Analysis**

.. code-block:: python

   # Analyze architecture diagrams
   await primary_agent.run("""
   analyze the architecture diagram at ./docs/system_design.png
   and describe the components and their relationships
   """)

Integration Examples
-------------------

**GitHub Integration**

.. code-block:: python

   # Create issues automatically
   await primary_agent.run("""
   Create a GitHub issue in the main repository titled 
   "Implement user authentication" with description about 
   adding OAuth2 support and assign it high priority
   """)

   # Analyze repository
   await primary_agent.run("""
   Get information about recent issues and pull requests 
   in the repository and summarize the current development status
   """)

**Slack Integration**

.. code-block:: python

   # Send status updates
   await primary_agent.run("""
   Send a message to the #development channel about 
   the completion of the authentication feature implementation
   """)

   # Daily standup automation
   await primary_agent.run("""
   Send a daily standup summary to #team channel including:
   - Tasks completed yesterday
   - Tasks planned for today  
   - Any blockers or issues
   """)

Custom Agent Examples
--------------------

**Creating a Specialized Agent**

.. code-block:: python

   from src.agents.base import BaseAgent
   from pydantic import BaseModel
   from pydantic_ai import RunContext

   class DatabaseAgentDeps(BaseModel):
       db_connection: Any = None
       class Config:
           arbitrary_types_allowed = True

   class DatabaseAgent(BaseAgent):
       def __init__(self, model, db_connection):
           super().__init__(
               name="database_agent",
               model=model,
               system_prompt="You are a database management assistant.",
               deps_type=DatabaseAgentDeps
           )
           self.db_connection = db_connection
           self._register_tools()

       def _register_tools(self):
           @self.agent.tool
           async def query_database(ctx: RunContext[DatabaseAgentDeps], query: str) -> str:
               """Execute database query and return results."""
               # Implementation here
               pass

           @self.agent.tool
           async def analyze_schema(ctx: RunContext[DatabaseAgentDeps]) -> str:
               """Analyze database schema and return structure."""
               # Implementation here  
               pass

**Using Custom Agents**

.. code-block:: python

   # Register custom agent
   db_agent = DatabaseAgent(model, db_connection)
   agents["database"] = db_agent

   # Add to primary agent
   primary_agent = PrimaryAgent(model, agents)

   # Use through primary agent
   result = await primary_agent.run("Show me all tables in the database")

Error Handling Examples
----------------------

**Graceful Error Handling**

.. code-block:: python

   try:
       result = await primary_agent.run("complex query that might fail")
   except Exception as e:
       # The system handles errors gracefully
       print(f"Operation failed: {e}")
       # System continues to work for other operations

**Retry Logic**

.. code-block:: python

   from src.utils.logging import retry_async

   @retry_async(max_attempts=3, delay=1.0)
   async def reliable_operation():
       return await primary_agent.run("operation that might need retries")

Performance Examples
-------------------

**Batch Operations**

.. code-block:: python

   # Process multiple files efficiently
   files = ["file1.py", "file2.py", "file3.py"]
   
   # This is handled efficiently by the system
   await rag_agent.run(f"index all files: {', '.join(files)}")

**Concurrent Operations**

.. code-block:: python

   import asyncio

   # Run multiple agents concurrently
   tasks = [
       brave_agent.run("search query 1"),
       rag_agent.run("knowledge query 1"),
       filesystem_agent.run("file operation 1")
   ]
   
   results = await asyncio.gather(*tasks)

Testing Examples
---------------

**Unit Testing Agents**

.. code-block:: python

   import pytest
   from unittest.mock import Mock

   @pytest.mark.asyncio
   async def test_rag_agent_search():
       # Mock dependencies
       mock_chromadb = Mock()
       mock_chromadb.query.return_value = {
           'ids': [['doc1']],
           'documents': [['test content']],
           'metadatas': [['source': 'test.py']],
           'distances': [[0.1]]
       }
       
       # Test agent
       agent = RAGAgent(mock_model)
       agent.chromadb_client = mock_chromadb
       
       result = await agent.run("test query")
       assert "test content" in str(result.data)

**Integration Testing**

.. code-block:: python

   @pytest.mark.asyncio
   async def test_primary_agent_delegation():
       # Setup agents
       agents = {
           "rag": Mock(),
           "brave_search": Mock() 
       }
       
       primary = PrimaryAgent(mock_model, agents)
       
       # Test delegation
       await primary.run("search for python tutorials")
       
       # Verify correct agent was called
       agents["brave_search"].run.assert_called_once()

These examples demonstrate the flexibility and power of the Multi-Agent Automation System. The system can be adapted to many different use cases and workflows through its modular architecture and extensible design.