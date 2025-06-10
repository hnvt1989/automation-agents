# Automation Agents Frontend

A simple HTML-based frontend for the automation agents system.

## Architecture

- **Technology**: HTML5 with inline React 18 and Babel transpilation
- **No Build Process**: Runs directly in the browser
- **Real-time**: WebSocket connection to backend for chat functionality
- **API**: RESTful endpoints for CRUD operations

## Configuration

Before running the frontend, ensure the backend API URLs are correct in `index.html`:

```javascript
// Configuration - Update these URLs to match your backend server
const CONFIG = {
    API_BASE_URL: 'http://localhost:8000',  // Backend API server URL
    WS_URL: 'ws://localhost:8000/ws'        // WebSocket URL for real-time chat
};
```

## Running the Frontend

### Option 1: Direct File Access
Simply open `index.html` in your web browser.

### Option 2: HTTP Server
```bash
# Using Python (recommended)
python -m http.server 3000

# Using npm scripts
npm run dev
```

Then open http://localhost:3000

## Features

- **Task Management**: Create, edit, and track tasks with priorities and due dates
- **Documents**: Manage and edit documents with indexing capability
- **Meeting Notes**: View and analyze meeting notes with task suggestions
- **Daily Logs**: Track daily work logs with date filtering (✨ recently added)
- **Real-time Chat**: WebSocket-based chat with the AI assistant

## Backend Requirements

The frontend requires the backend API server to be running:

```bash
# From the root directory
uvicorn src.api_server:app --reload --host 0.0.0.0 --port 8000
```

## Recent Updates

- ✅ Added date picker filtering for Daily Logs
- ✅ Cleaned up TypeScript/Vite artifacts
- ✅ Simplified to HTML-only architecture