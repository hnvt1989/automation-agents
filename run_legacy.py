#!/usr/bin/env python3
"""Run the legacy agents.py file.

This is a temporary wrapper to run the old monolithic agents.py file
while we transition to the new modular structure.
"""
import sys
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run the main function from agents.py
from agents import main

if __name__ == "__main__":
    asyncio.run(main())