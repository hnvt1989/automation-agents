#!/bin/bash
# Script to run the markdown indexer with proper virtual environment

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ -d "venv" ]; then
    VENV_PATH="venv"
elif [ -d ".venv" ]; then
    VENV_PATH=".venv"
else
    echo "ERROR: No virtual environment found!"
    echo "Please create a virtual environment first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment and run the script
echo "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

echo "Running markdown indexer..."
python scripts/index_data.py

# Deactivate virtual environment
deactivate

echo "Done!"