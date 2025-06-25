#!/usr/bin/env python3
"""Wrapper to disable vector operations when using Neo4j Aura."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variable to disable vector operations
os.environ["DISABLE_NEO4J_VECTORS"] = "true"

print("Neo4j vector operations disabled for cloud mode")
print("Use this script before running the main application:")
print("  python scripts/disable_vectors.py && python -m src.main")
