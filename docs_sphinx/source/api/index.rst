API Reference
=============

This section contains the complete API documentation for the Multi-Agent Automation System.

.. toctree::
   :maxdepth: 2
   :caption: API Documentation:

   core
   agents
   processors
   storage
   mcp
   utils

Overview
--------

The API is organized into several key modules:

**Core Modules**
   Configuration management, constants, and exception handling

**Agents**
   Base agent classes and specialized agent implementations

**Processors**
   Data processing components for calendars, images, and web content

**Storage**
   Database clients and storage management

**MCP (Model Context Protocol)**
   Server management and integration layer

**Utilities**
   Logging, helper functions, and common utilities

Quick Reference
---------------

**Main Entry Points:**

.. code-block:: python

   from src.main import AutomationAgentsCLI
   from src.agents.primary import PrimaryAgent
   from src.agents.rag import RAGAgent
   from src.core.config import get_settings

**Key Classes:**

* :class:`src.agents.primary.PrimaryAgent` - Main orchestration agent
* :class:`src.agents.rag.RAGAgent` - Knowledge base search agent
* :class:`src.mcp.manager.MCPServerManager` - MCP server lifecycle management
* :class:`src.storage.chromadb_client.ChromaDBClient` - Vector database interface

**Configuration:**

* :class:`src.core.config.Settings` - Application settings
* :class:`src.core.config.MCPServerConfig` - MCP server configuration

Usage Examples
--------------

**Basic Agent Usage:**

.. code-block:: python

   from src.agents.primary import PrimaryAgent
   from src.core.config import get_settings
   from pydantic_ai.providers.openai import OpenAIProvider
   from pydantic_ai.models.openai import OpenAIModel

   # Initialize model
   settings = get_settings()
   provider = OpenAIProvider(api_key=settings.llm_api_key)
   model = OpenAIModel(settings.model_choice, provider=provider)

   # Create primary agent
   agents = {}  # Dictionary of specialized agents
   primary_agent = PrimaryAgent(model, agents)

   # Run a query
   result = await primary_agent.run("Search for Python best practices")

**RAG System Usage:**

.. code-block:: python

   from src.agents.rag import RAGAgent
   from src.storage.chromadb_client import get_chromadb_client

   # Initialize RAG agent
   rag_agent = RAGAgent(model)

   # Search knowledge base
   result = await rag_agent.run("What is the authentication flow?")

**MCP Server Management:**

.. code-block:: python

   from src.mcp import get_mcp_manager

   # Initialize MCP servers
   mcp_manager = get_mcp_manager()
   await mcp_manager.initialize()

   # Get a specific server
   brave_server = mcp_manager.get_server("brave")

   # Health check
   health_status = await mcp_manager.health_check()

For detailed API documentation, navigate to the specific module sections.