#!/bin/bash
# Run both backend and frontend servers

set -e  # Exit on any error

echo "Starting automation agents application with backend and frontend..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install authentication dependencies
echo "Installing authentication dependencies..."
pip install PyJWT>=2.8.0

# Check for required Supabase environment variables
echo "Checking Supabase configuration..."
if [ -f "local.env" ]; then
    source local.env
    if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
        echo "❌ ERROR: SUPABASE_URL and SUPABASE_KEY must be set in local.env"
        echo "Please configure your Supabase credentials in local.env file"
        exit 1
    else
        echo "✅ Supabase configuration found"
    fi
else
    echo "❌ ERROR: local.env file not found"
    echo "Please create local.env with your Supabase credentials"
    exit 1
fi

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process using a port
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        echo "Killing process $pid using port $port..."
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
}

# Function to cleanup background processes on exit
cleanup() {
    echo "Shutting down servers..."
    kill $(jobs -p) 2>/dev/null || true
    exit
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Check and handle backend port
BACKEND_PORT=8000
if check_port $BACKEND_PORT; then
    echo "Port $BACKEND_PORT is already in use. Killing existing process..."
    kill_port $BACKEND_PORT
fi

# Check and handle frontend port
FRONTEND_PORT=3000
if check_port $FRONTEND_PORT; then
    echo "Port $FRONTEND_PORT is already in use. Killing existing process..."
    kill_port $FRONTEND_PORT
fi

# Start Supabase backend API server in background
echo "Starting Supabase backend API server with full cloud storage on port $BACKEND_PORT..."
uvicorn src.api_server_supabase:app --reload --host 0.0.0.0 --port $BACKEND_PORT &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Start frontend server (simple HTTP server) in background
echo "Starting frontend server on port $FRONTEND_PORT..."
cd frontend
python3 -m http.server $FRONTEND_PORT &
FRONTEND_PID=$!
cd ..

echo ""
echo "🚀 Servers are running with full Supabase integration:"
echo "   Backend API (Supabase): http://localhost:$BACKEND_PORT"
echo "   Frontend:               http://localhost:$FRONTEND_PORT"
echo ""
echo "✅ Using Supabase for:"
echo "   • Documents (with vector search)"
echo "   • Tasks & Daily Logs"
echo "   • User Authentication"
echo "   • All data storage"
echo ""
echo "📋 Database Setup:"
echo "   If this is your first time running, make sure you have:"
echo "   1. Created tables using: scripts/supabase_schema.sql"
echo "   2. Added vector functions: scripts/supabase_vector_functions.sql"
echo "   3. Migrated your files using: scripts/run_migration.py"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for background processes
wait