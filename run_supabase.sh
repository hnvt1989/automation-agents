#!/bin/bash

# Run the API server with Supabase backend

echo "Starting API server with Supabase backend..."
echo "Make sure you have set SUPABASE_URL and SUPABASE_KEY in local.env"
echo ""

# Load environment variables
if [ -f "local.env" ]; then
    export $(cat local.env | grep -v '^#' | xargs)
fi

# Check if Supabase credentials are set
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    echo "ERROR: SUPABASE_URL and SUPABASE_KEY must be set in local.env"
    echo "Please copy local.env.example to local.env and add your Supabase credentials"
    exit 1
fi

# Run the Supabase version of the API server
python -m uvicorn src.api_server_supabase:app --reload --host 0.0.0.0 --port 8000