Development Guide
================

This section provides information for developers who want to contribute to, extend, or integrate with the Multi-Agent Automation System.

.. toctree::
   :maxdepth: 2
   :caption: Development:

   setup
   contributing
   testing
   extending_agents
   creating_mcp_servers
   code_style

Development Overview
-------------------

The Multi-Agent Automation System is designed for extensibility and maintainability:

**🛠️ Development Environment**
   - Python 3.8+ with virtual environments
   - Pre-commit hooks for code quality
   - Comprehensive testing suite
   - Documentation generation with Sphinx

**🔧 Code Quality**
   - Type hints throughout the codebase
   - Linting with flake8 and mypy
   - Code formatting with black
   - Import sorting with isort

**🧪 Testing Strategy**
   - Unit tests for individual components
   - Integration tests for agent interactions
   - Performance tests for vector operations
   - Mock external services for isolated testing

**📚 Documentation**
   - Docstring standards (Google/NumPy style)
   - API documentation generation
   - Architecture decision records
   - User guide and examples

Getting Started
--------------

**1. Development Setup**

.. code-block:: bash

   # Clone repository
   git clone <repository-url>
   cd automation-agents

   # Setup development environment
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements-dev.txt
   pip install -e .

   # Install pre-commit hooks
   pre-commit install

**2. Run Tests**

.. code-block:: bash

   # Unit tests
   pytest tests/unit/

   # Integration tests
   pytest tests/integration/

   # All tests with coverage
   pytest tests/ --cov=src --cov-report=html

**3. Code Quality Checks**

.. code-block:: bash

   # Format code
   black src/ tests/

   # Sort imports
   isort src/ tests/

   # Type checking
   mypy src/

   # Linting
   flake8 src/ tests/

Project Structure
----------------

.. code-block::

   automation-agents/
   ├── src/                    # Source code
   │   ├── agents/            # Agent implementations
   │   ├── core/              # Core configuration and exceptions
   │   ├── mcp/               # MCP server management
   │   ├── processors/        # Data processors
   │   ├── storage/           # Storage layer
   │   └── utils/             # Utilities and helpers
   ├── tests/                 # Test suite
   │   ├── unit/              # Unit tests
   │   ├── integration/       # Integration tests
   │   └── conftest.py        # Test configuration
   ├── docs_sphinx/           # Documentation source
   ├── data/                  # Data files (tasks, logs, meetings)
   ├── requirements.txt       # Production dependencies
   ├── requirements-dev.txt   # Development dependencies
   └── pyproject.toml         # Project configuration

Development Workflow
-------------------

**1. Feature Development**

.. code-block:: bash

   # Create feature branch
   git checkout -b feature/new-agent

   # Make changes
   # ... develop your feature ...

   # Run tests
   pytest tests/

   # Check code quality
   black src/ tests/
   isort src/ tests/
   mypy src/
   flake8 src/ tests/

   # Commit changes
   git add .
   git commit -m "Add new agent implementation"

   # Push and create PR
   git push origin feature/new-agent

**2. Testing Guidelines**

- Write tests for all new functionality
- Maintain test coverage above 80%
- Use descriptive test names
- Mock external dependencies
- Test error conditions

**3. Documentation Updates**

- Update docstrings for new/changed functions
- Add usage examples for new features
- Update architecture documentation if needed
- Generate API docs: ``sphinx-build docs_sphinx/source docs_sphinx/build``

Contributing Guidelines
----------------------

**Code Style**

- Follow PEP 8 coding standards
- Use type hints for all function signatures
- Write descriptive docstrings (Google/NumPy style)
- Keep functions focused and single-purpose
- Use meaningful variable and function names

**Git Workflow**

- Create feature branches from main
- Write clear, descriptive commit messages
- Squash commits before merging
- Include tests with new features
- Update documentation as needed

**Pull Request Process**

1. Ensure all tests pass
2. Update documentation
3. Add entry to CHANGELOG.md
4. Request review from maintainers
5. Address review feedback
6. Merge after approval

Extending the System
-------------------

**Creating New Agents**

See :doc:`extending_agents` for detailed instructions on:

- Implementing the BaseAgent interface
- Adding agent-specific tools
- Registering agents with the primary agent
- Testing agent functionality

**Adding MCP Servers**

See :doc:`creating_mcp_servers` for:

- MCP server development
- Integration with the MCP manager
- Configuration and environment setup
- Testing MCP server functionality

**Custom Processors**

To add new data processors:

.. code-block:: python

   from src.processors.base import BaseProcessor

   class CustomProcessor(BaseProcessor):
       async def process(self, input_data: Any) -> Any:
           # Implementation here
           pass

Performance Considerations
-------------------------

**Async Programming**

- Use async/await for I/O operations
- Avoid blocking calls in async functions
- Use asyncio.gather() for concurrent operations
- Implement proper error handling in async code

**Memory Management**

- Use generators for large data processing
- Implement pagination for database queries
- Clean up resources in finally blocks
- Monitor memory usage in long-running operations

**Caching Strategies**

- Cache expensive computation results
- Implement TTL for time-sensitive data
- Use LRU cache for frequently accessed items
- Consider distributed caching for scaling

**Database Optimization**

- Use vector search efficiently
- Batch database operations when possible
- Implement proper indexing strategies
- Monitor query performance

Debugging and Logging
---------------------

**Debug Configuration**

.. code-block:: python

   # Enable debug logging
   DEBUG=true
   LOG_LEVEL=DEBUG

   # Set breakpoints in code
   import pdb; pdb.set_trace()

   # Use rich logging for better output
   from src.utils.logging import log_debug
   log_debug("Debug information", extra={"context": data})

**Performance Profiling**

.. code-block:: python

   import cProfile
   import pstats

   # Profile function
   profiler = cProfile.Profile()
   profiler.enable()
   # ... code to profile ...
   profiler.disable()

   stats = pstats.Stats(profiler)
   stats.sort_stats('cumulative').print_stats(10)

**Memory Profiling**

.. code-block:: bash

   # Install memory profiler
   pip install memory_profiler

   # Profile memory usage
   python -m memory_profiler src/main.py

Release Process
--------------

**Version Management**

- Use semantic versioning (MAJOR.MINOR.PATCH)
- Update version in pyproject.toml
- Tag releases in git
- Maintain CHANGELOG.md

**Release Checklist**

1. ✅ All tests passing
2. ✅ Documentation updated
3. ✅ Version bumped
4. ✅ CHANGELOG.md updated
5. ✅ Security review completed
6. ✅ Performance testing done
7. ✅ Git tag created
8. ✅ Release notes published

**Deployment**

.. code-block:: bash

   # Build package
   python -m build

   # Test installation
   pip install dist/automation-agents-*.whl

   # Deploy to PyPI (if applicable)
   twine upload dist/*

Support and Community
--------------------

**Getting Help**

- Check existing issues and documentation
- Search discussions and forums
- Create detailed bug reports with reproducible steps
- Provide system information and logs

**Contributing to Documentation**

- Fix typos and improve clarity
- Add examples and use cases
- Update API documentation
- Translate documentation (if applicable)

**Community Guidelines**

- Be respectful and inclusive
- Help others learn and contribute
- Share knowledge and best practices
- Follow the code of conduct