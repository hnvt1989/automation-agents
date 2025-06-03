Multi-Agent Automation System Documentation
==========================================

Welcome to the Multi-Agent Automation System documentation. This system provides a sophisticated multi-agent architecture using the Model Context Protocol (MCP) for automation, quality assurance, and intelligent document processing.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   user_guide/index
   api/index
   architecture/index
   development/index
   examples/index

Quick Start
-----------

To get started with the automation agents system:

1. **Installation**:

   .. code-block:: bash

      git clone <repository-url>
      cd automation-agents
      python -m venv venv
      source venv/bin/activate  # On Windows: venv\Scripts\activate
      pip install -r requirements.txt

2. **Configuration**:

   Create a ``local.env`` file with your API keys:

   .. code-block:: env

      MODEL_CHOICE=gpt-4o-mini
      BASE_URL=https://api.openai.com/v1
      LLM_API_KEY=your_openai_api_key
      OPENAI_API_KEY=your_openai_api_key
      BRAVE_API_KEY=your_brave_search_api_key

3. **Run the System**:

   .. code-block:: bash

      ./run.sh
      # Or directly:
      python -m src.main

Key Features
------------

🚀 **Multi-Agent Architecture**
   - Primary orchestration agent with intelligent routing
   - Specialized agents for search, filesystem, GitHub, Slack, and analysis
   - Enhanced RAG system with ChromaDB integration

🧠 **Advanced RAG System**
   - Document indexing with multi-format support
   - Image analysis for calendars and conversations
   - Semantic search with vector embeddings

📋 **Planning & Task Management**
   - YAML-based task and meeting management
   - Natural language planning interface
   - Integration with calendar and scheduling

🔧 **Model Context Protocol Integration**
   - Extensible server architecture
   - Auto-managed external service connections
   - Graceful error handling and recovery

Architecture Overview
--------------------

The system follows a multi-layered architecture:

- **User Interface Layer**: Rich CLI with interactive prompts
- **Orchestration Layer**: Primary agent with intelligent delegation
- **Agent Layer**: Specialized agents for different domains
- **Integration Layer**: MCP servers for external services
- **Storage Layer**: ChromaDB for vectors, YAML for structured data

For detailed architecture diagrams, see the :doc:`architecture/index` section.

API Reference
-------------

Complete API documentation is available in the :doc:`api/index` section, including:

- Core configuration and exceptions
- Agent implementations and base classes
- Data processors and storage clients
- MCP server management
- Utility functions and logging

Contributing
------------

We welcome contributions! Please see our :doc:`development/index` section for:

- Development setup and guidelines
- Code style and testing requirements
- Architecture decisions and patterns
- Contribution workflow

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`