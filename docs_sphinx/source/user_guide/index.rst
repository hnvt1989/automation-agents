User Guide
==========

Welcome to the Multi-Agent Automation System user guide. This section provides comprehensive instructions for installing, configuring, and using the automation agents system.

.. toctree::
   :maxdepth: 2
   :caption: User Guide:

   installation
   configuration
   getting_started
   agents_overview
   rag_system
   planning_features
   troubleshooting

Quick Start
-----------

**1. Installation**

.. code-block:: bash

   git clone <repository-url>
   cd automation-agents
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt

**2. Configuration**

Create a ``local.env`` file:

.. code-block:: env

   MODEL_CHOICE=gpt-4o-mini
   BASE_URL=https://api.openai.com/v1
   LLM_API_KEY=your_openai_api_key
   OPENAI_API_KEY=your_openai_api_key
   BRAVE_API_KEY=your_brave_search_api_key

**3. Run the System**

.. code-block:: bash

   ./run.sh

System Overview
--------------

The Multi-Agent Automation System provides:

- **Multi-Agent Architecture**: Specialized agents for different tasks
- **RAG System**: Advanced document indexing and retrieval
- **Planning Features**: Task management and scheduling
- **MCP Integration**: Extensible external service connections
- **Rich CLI**: Interactive command-line interface

Core Features
-------------

**🔍 Intelligent Search**
   - Web search through Brave Search API
   - Semantic search in indexed documents
   - Context-aware information retrieval

**📁 File Management**
   - File operations and directory management
   - Document indexing and analysis
   - Image processing for calendars and conversations

**📋 Task Planning**
   - Natural language task management
   - Meeting scheduling and calendar integration
   - Progress tracking and reporting

**🔗 External Integrations**
   - GitHub repository management
   - Slack team communication
   - Extensible MCP server architecture

**🤖 AI-Powered Assistance**
   - Natural language understanding
   - Intelligent request routing
   - Context-aware responses

Getting Help
-----------

- **Troubleshooting**: See the :doc:`troubleshooting` section for common issues
- **API Reference**: Complete API documentation in :doc:`../api/index`
- **Examples**: Practical examples in :doc:`../examples/index`
- **Architecture**: System design details in :doc:`../architecture/index`

Next Steps
----------

1. **Installation**: Follow the detailed :doc:`installation` guide
2. **Configuration**: Set up your API keys and preferences in :doc:`configuration`
3. **Getting Started**: Learn basic usage in :doc:`getting_started`
4. **Explore Features**: Discover advanced capabilities in the other guide sections