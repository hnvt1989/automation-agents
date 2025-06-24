from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
import yaml
from datetime import datetime
import os
from dotenv import load_dotenv, set_key, find_dotenv

from src.core.config import get_settings
from src.mcp import get_mcp_manager
from src.agents.primary import PrimaryAgent
from src.agents.brave_search import BraveSearchAgent
from src.agents.filesystem import FilesystemAgent
from src.agents.rag import RAGAgent
from src.agents.analyzer import AnalyzerAgent
from src.storage.supabase_ops import SupabaseOperations

BASE_DIR = Path(__file__).resolve().parent.parent
TASKS_FILE = BASE_DIR / "data" / "tasks.md"
TASKS_YAML_FILE = BASE_DIR / "data" / "tasks.yaml"
DAILY_LOGS_FILE = BASE_DIR / "data" / "daily_logs.yaml"
FRONTEND_DIR = BASE_DIR / "frontend"
VA_NOTES_DIR = BASE_DIR / "data" / "va_notes"
MEETING_NOTES_DIR = BASE_DIR / "data" / "meeting_notes"
INTERVIEWS_DIR = BASE_DIR / "data" / "interviews"


class Task(BaseModel):
    name: str
    description: str | None = None


class TaskList(BaseModel):
    tasks: list[Task]


class TaskUpdate(BaseModel):
    id: str | None = None
    title: str | None = None
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: str | None = None
    tags: list[str] | None = None
    todo: str | None = None


class NoteUpdate(BaseModel):
    name: str
    description: str | None = None
    content: str | None = None
    path: str | None = None


class DocumentUpdate(BaseModel):
    name: str
    description: str | None = None
    content: str | None = None
    filename: str | None = None


class InterviewUpdate(BaseModel):
    name: str
    description: str | None = None
    notes: str | None = None
    priority: str | None = None
    status: str | None = None
    filename: str | None = None


class LogUpdate(BaseModel):
    name: str
    description: str | None = None
    date: str | None = None
    log_id: str | None = None
    actual_hours: float | None = None


class ConfigUpdate(BaseModel):
    documents_dir: str | None = None
    notes_dir: str | None = None
    tasks_file: str | None = None
    logs_file: str | None = None


class MeetingAnalysisRequest(BaseModel):
    meeting_content: str
    meeting_date: str
    meeting_title: str


class SuggestedTaskRequest(BaseModel):
    title: str
    description: str
    priority: str
    due_date: str


# Load environment variables from local.env
load_dotenv("local.env")

# Initialize Supabase operations
db_ops = SupabaseOperations()

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You may want to restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# Track config changes dynamically
config_storage = {
    "documents_dir": str(VA_NOTES_DIR),
    "notes_dir": str(MEETING_NOTES_DIR),
    "tasks_file": str(TASKS_YAML_FILE),
    "logs_file": str(DAILY_LOGS_FILE)
}

# Helper function to ensure directories exist
def ensure_dirs():
    docs_dir = Path(config_storage["documents_dir"])
    notes_dir = Path(config_storage["notes_dir"])
    docs_dir.mkdir(parents=True, exist_ok=True)
    notes_dir.mkdir(parents=True, exist_ok=True)


# Root endpoint
@app.get("/")
async def root():
    if FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
    return {"message": "API is running"}


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Tasks endpoints (using Supabase)
@app.get("/tasks")
async def get_tasks():
    """Get all tasks from Supabase."""
    try:
        tasks_data = db_ops.get_all_tasks()
        
        print(f"\n=== GET TASKS DEBUG ===")
        print(f"Total tasks from Supabase: {len(tasks_data)}")
        for i, task in enumerate(tasks_data):
            print(f"  [{i}] ID: {task.get('id')}, Title: {task.get('title')}")
        
        tasks = []
        for task in tasks_data:
            # Format the task for frontend display
            formatted_task = {
                "name": task.get("title", "Untitled Task"),
                "description": task.get("description", ""),
                "id": task.get("id"),
                "priority": task.get("priority"),
                "status": task.get("status"),
                "tags": task.get("tags", []),
                "dueDate": task.get("due_date"),
                "estimate_hours": task.get("estimate_hours"),
                "todo": task.get("todo", "")
            }
            tasks.append(formatted_task)
        
        print(f"Returning {len(tasks)} formatted tasks")
        return {"tasks": tasks}
    except Exception as e:
        print(f"Error reading tasks from Supabase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks")
async def create_task(task_update: TaskUpdate):
    """Create a new task in Supabase."""
    try:
        # Create task data
        task_data = {
            'id': task_update.id,
            'title': task_update.name or task_update.title or "New Task",
            'description': task_update.description,
            'status': task_update.status or 'pending',
            'priority': task_update.priority or 'medium',
            'due_date': task_update.due_date,
            'tags': task_update.tags or [],
            'todo': task_update.todo
        }
        
        result = db_ops.add_task(task_data)
        
        if result["success"]:
            return {"success": True, "task": result["task"]}
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a specific task by ID from Supabase."""
    try:
        print(f"\n=== DELETE TASK DEBUG (Backend) ===")
        print(f"Received request to delete task with ID: {task_id}")
        
        result = db_ops.remove_task(task_id)
        
        if result["success"]:
            return {"success": True, "message": result["message"]}
        else:
            raise HTTPException(status_code=404, detail=result["error"])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/tasks/{task_id}")
async def update_task(task_id: str, task_update: TaskUpdate):
    """Update a specific task by ID in Supabase."""
    try:
        print(f"\n=== UPDATE TASK DEBUG ===")
        print(f"Updating task ID: {task_id}")
        print(f"Update data: {task_update.dict(exclude_unset=True)}")
        
        # Build update data
        updates = {}
        if task_update.title is not None or task_update.name is not None:
            updates["title"] = task_update.title or task_update.name
        if task_update.description is not None:
            updates["description"] = task_update.description
        if task_update.status is not None:
            updates["status"] = task_update.status
        if task_update.priority is not None:
            updates["priority"] = task_update.priority
        if task_update.due_date is not None:
            updates["due_date"] = task_update.due_date
        if task_update.tags is not None:
            updates["tags"] = task_update.tags
        if task_update.todo is not None:
            updates["todo"] = task_update.todo
        
        result = db_ops.update_task(task_id, updates)
        
        if result["success"]:
            return {"success": True, "message": result["message"], "task": result["task"]}
        else:
            raise HTTPException(status_code=404, detail=result["error"])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Logs endpoints (using Supabase)
@app.get("/logs")
async def get_logs():
    """Get all logs from Supabase."""
    try:
        logs_data = db_ops.get_all_logs()
        
        logs = []
        for log in logs_data:
            formatted_log = {
                "name": log.get("description", "No description"),
                "description": f"Date: {log.get('log_date')} | ID: {log.get('log_id', 'N/A')} | Hours: {log.get('actual_hours', 0)}h",
                "date": log.get("log_date"),
                "log_id": log.get("log_id"),
                "actual_hours": log.get("actual_hours"),
                "raw_description": log.get("description", ""),
                "db_id": log.get("id")  # Include database ID for operations
            }
            logs.append(formatted_log)
        
        return {"logs": logs}
    except Exception as e:
        print(f"Error reading logs from Supabase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/logs")
async def create_log(log_update: LogUpdate):
    """Create a new log entry in Supabase."""
    try:
        # Create log data
        log_data = {
            'date': log_update.date or datetime.now().strftime('%Y-%m-%d'),
            'log_id': log_update.log_id,
            'description': log_update.name or log_update.description or "New log entry",
            'actual_hours': log_update.actual_hours or 0
        }
        
        result = db_ops.add_log(log_data)
        
        if result["success"]:
            return {"success": True, "log": result["log"]}
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/logs/{log_index}")
async def delete_log(log_index: int):
    """Delete a specific log by index from Supabase."""
    try:
        # Get all logs to find the one at the given index
        logs_data = db_ops.get_all_logs()
        
        if 0 <= log_index < len(logs_data):
            log = logs_data[log_index]
            db_id = log.get("id")
            
            result = db_ops.remove_log(db_id)
            
            if result["success"]:
                return {"success": True, "message": result["message"], "deleted_log": result["deleted_log"]}
            else:
                raise HTTPException(status_code=404, detail=result["error"])
        else:
            raise HTTPException(status_code=404, detail="Log not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/logs/{log_index}")
async def update_log(log_index: int, log_update: LogUpdate):
    """Update a specific log by index in Supabase."""
    try:
        # Get all logs to find the one at the given index
        logs_data = db_ops.get_all_logs()
        
        if 0 <= log_index < len(logs_data):
            log = logs_data[log_index]
            db_id = log.get("id")
            
            # Build update data
            updates = {}
            if log_update.name is not None or log_update.description is not None:
                updates["description"] = log_update.name or log_update.description
            if log_update.actual_hours is not None:
                updates["actual_hours"] = log_update.actual_hours
            if log_update.log_id is not None:
                updates["log_id"] = log_update.log_id
            
            result = db_ops.update_log(db_id, updates)
            
            if result["success"]:
                return {"success": True, "log": result["log"]}
            else:
                raise HTTPException(status_code=400, detail=result["error"])
        else:
            raise HTTPException(status_code=404, detail="Log not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Keep existing endpoints for documents, notes, interviews unchanged
@app.get("/documents")
async def get_documents():
    docs_dir = Path(config_storage["documents_dir"])
    if not docs_dir.exists():
        return {"documents": []}

    documents = []
    # Sort files by name for consistent ordering
    sorted_files = sorted(docs_dir.glob("*.md"), key=lambda x: x.name)
    
    for file_path in sorted_files:
        name = file_path.stem.replace("_", " ").title()
        description = f"Markdown document - {file_path.name}"
        documents.append({
            "name": name,
            "description": description,
            "filename": file_path.name,
            "path": str(file_path.relative_to(BASE_DIR))
        })
    
    return {"documents": documents}


@app.get("/documents/{doc_index}/content")
async def get_document_content(doc_index: int):
    """Get the content of a specific document"""
    try:
        # Use same sorting as get_documents
        docs_dir = Path(config_storage["documents_dir"])
        docs = sorted(docs_dir.glob("*.md"), key=lambda x: x.name)
        if 0 <= doc_index < len(docs):
            file_path = docs[doc_index]
            content = file_path.read_text()
            return {"content": content}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notes")
async def get_notes():
    notes_dir = Path(config_storage["notes_dir"])
    if not notes_dir.exists():
        return {"notes": []}
    
    notes = []
    # Use rglob to recursively find all .md files in subdirectories
    for file_path in notes_dir.rglob("*.md"):
        # Get relative path from meeting_notes directory
        relative_path = file_path.relative_to(notes_dir)
        
        # Create a more descriptive name from the path
        name = file_path.stem.replace("_", " ").replace("-", " ").title()
        
        # Include subdirectory in description if file is not in root
        if relative_path.parent != Path("."):
            description = f"{relative_path.parent} / {file_path.name}"
        else:
            description = file_path.name
            
        notes.append({
            "name": name,
            "description": description,
            "filename": file_path.name,
            "path": str(file_path.relative_to(BASE_DIR))
        })
    
    # Sort by path for consistent ordering
    notes.sort(key=lambda x: x["path"])
    
    return {"notes": notes}


@app.get("/notes/{note_index}/content")
async def get_note_content(note_index: int):
    """Get the content of a specific note"""
    try:
        notes_dir = Path(config_storage["notes_dir"])
        notes = []
        for file_path in notes_dir.rglob("*.md"):
            notes.append(file_path)
        
        # Sort to ensure consistent ordering
        notes.sort(key=lambda x: str(x))
        
        if 0 <= note_index < len(notes):
            file_path = notes[note_index]
            content = file_path.read_text()
            return {"content": content}
        else:
            raise HTTPException(status_code=404, detail="Note not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notes")
async def create_note(note_update: NoteUpdate):
    """Create a new note"""
    try:
        # Create filename from name
        filename = note_update.name.lower().replace(' ', '_') + '.md'
        notes_dir = Path(config_storage["notes_dir"])
        file_path = notes_dir / filename
        
        # Ensure directory exists
        notes_dir.mkdir(parents=True, exist_ok=True)
        
        # Write content to file
        content = note_update.content or f"# {note_update.name}\n\n{note_update.description or ''}"
        file_path.write_text(content)
        
        # Find the index of the newly created note
        notes = []
        for fp in notes_dir.rglob("*.md"):
            notes.append(fp)
        notes.sort(key=lambda x: str(x))
        
        new_index = next((i for i, n in enumerate(notes) if n.name == filename), -1)
        
        return {"success": True, "message": "Note created", "filename": filename, "index": new_index}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/notes/{note_index}")
async def update_note(note_index: int, note_update: NoteUpdate):
    """Update a specific note by index"""
    try:
        # For notes, we need to handle file content updates
        # This is a simplified version - in production, you'd want more robust file handling
        
        # Get the list of notes to find which file to update
        notes_dir = Path(config_storage["notes_dir"])
        notes = []
        for file_path in notes_dir.rglob("*.md"):
            notes.append(file_path)
        
        # Sort to ensure consistent ordering
        notes.sort(key=lambda x: str(x))
        
        if 0 <= note_index < len(notes):
            file_path = notes[note_index]
            
            # If content is provided, update the file
            if note_update.content is not None:
                file_path.write_text(note_update.content)
            
            return {"success": True, "message": "Note updated"}
        else:
            raise HTTPException(status_code=404, detail="Note not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents")
async def create_document(doc_update: DocumentUpdate):
    """Create a new document"""
    try:
        # Create filename from name
        filename = doc_update.name.lower().replace(' ', '_') + '.md'
        docs_dir = Path(config_storage["documents_dir"])
        file_path = docs_dir / filename
        
        # Ensure directory exists
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Write content to file
        content = doc_update.content or f"# {doc_update.name}\n\n{doc_update.description or ''}"
        file_path.write_text(content)
        
        # Find the index of the newly created document
        docs = sorted(docs_dir.glob("*.md"), key=lambda x: x.name)
        new_index = next((i for i, d in enumerate(docs) if d.name == filename), -1)
        
        return {"success": True, "message": "Document created", "filename": filename, "index": new_index}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/documents/{doc_index}")
async def update_document(doc_index: int, doc_update: DocumentUpdate):
    """Update a specific document by index"""
    try:
        # Use same sorting as get_documents
        docs_dir = Path(config_storage["documents_dir"])
        docs = sorted(docs_dir.glob("*.md"), key=lambda x: x.name)
        
        if 0 <= doc_index < len(docs):
            file_path = docs[doc_index]
            
            # If content is provided, update the file
            if doc_update.content is not None:
                file_path.write_text(doc_update.content)
            
            return {"success": True, "message": "Document updated"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ... (keep remaining endpoints like interviews, chat, config, etc.)

# WebSocket for real-time chat
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Get instances
    settings = get_settings()
    mcp_manager = await get_mcp_manager()
    
    # Initialize agents
    primary_agent = PrimaryAgent()
    
    # Create specialized agents for registration
    agents = {
        "brave_search": BraveSearchAgent(),
        "filesystem": FilesystemAgent(),
        "rag": RAGAgent()
    }
    
    # Register agents
    for name, agent in agents.items():
        primary_agent.register_agent(name, agent)
    
    # Also register mcp_manager for GitHub tools
    primary_agent.register_agent("mcp", mcp_manager)
    
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            
            # Use primary agent to handle the request
            response = await primary_agent.handle_request(message)
            
            await websocket.send_json({
                "type": "response",
                "message": response
            })
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    ensure_dirs()
    uvicorn.run(app, host="0.0.0.0", port=8000)