"""Vercel entry point for the FastAPI application."""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the FastAPI app
from src.api_server_supabase import app

# Vercel expects the app to be named 'app'
# This will be the entry point for the serverless function