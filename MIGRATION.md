# Migration Guide

## Running the Application

Due to the refactoring, the application structure has changed. Here are the new ways to run the automation agents:

### Option 1: Use the New Main Entry Point (Recommended)

```bash
# Activate your virtual environment
source venv/bin/activate

# Run the new modular application
python -m src.main
```

### Option 2: Run the Legacy agents.py (Temporary)

If you need to run the old monolithic `agents.py` file:

```bash
# Activate your virtual environment
source venv/bin/activate

# Run the legacy file
python run_legacy.py
```

### Option 3: Install and Use as Package

```bash
# Install the package in development mode
pip install -e .

# Run using the console script
automation-agents
```

## What Changed?

1. **Project Structure**: The monolithic `agents.py` has been split into:
   - `src/agents/` - Individual agent implementations
   - `src/core/` - Configuration and constants
   - `src/mcp/` - MCP server management
   - `src/processors/` - Data processors
   - `src/storage/` - Storage layer
   - `src/utils/` - Utilities

2. **Entry Point**: The new main entry point is `src/main.py` which provides:
   - Better error handling
   - Cleaner initialization
   - Interactive CLI interface
   - Proper shutdown procedures

3. **Configuration**: Now uses Pydantic settings for better validation and type safety

4. **Logging**: Enhanced logging with file rotation and rich formatting

## Next Steps

1. Test the new structure with: `python -m src.main`
2. Report any issues you encounter
3. The old `agents.py` will be deprecated in future versions