#!/bin/bash
# Index documents to cloud services

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to project directory
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the indexing script with default directories
echo "Indexing documents to cloud services..."
echo "Directories: data/meeting_notes, data/va_notes"
echo ""

python scripts/index_to_cloud.py "$@"