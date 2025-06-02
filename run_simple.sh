#!/bin/bash
# Run the simple automation agents application (without MCP servers)

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the simple application
python -m src.main_simple "$@"