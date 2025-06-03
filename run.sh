#!/bin/bash
# Run the automation agents application

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the application using module syntax
python -m src.main "$@"