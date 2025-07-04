from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response, Depends, Header
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
from typing import Optional

from src.core.config import get_settings
from src.mcp import get_mcp_manager
from src.agents.primary import PrimaryAgent, PrimaryAgentDeps
from src.agents.brave_search import BraveSearchAgent
from src.agents.filesystem import FilesystemAgent
from src.agents.rag_cloud import CloudRAGAgent
from src.agents.analyzer import AnalyzerAgent
from src.storage.supabase_ops import SupabaseOperations
from src.storage.auth_storage import AuthStorage

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


class UserRegistration(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


# Load environment variables from local.env
load_dotenv("local.env")

# Initialize Supabase operations
db_ops = SupabaseOperations()

# Initialize FastAPI app
app = FastAPI()

# Initialize auth storage at app startup
@app.on_event("startup")
async def startup_event():
    app.state.auth_storage = AuthStorage()

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


# Authentication helper functions
def get_auth_storage() -> AuthStorage:
    return app.state.auth_storage


def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current user from authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        # Extract token from "Bearer <token>"
        token = authorization.split(" ")[1] if authorization.startswith("Bearer ") else authorization
        auth_storage = get_auth_storage()
        user = auth_storage.verify_session(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authorization header")


def get_current_user_optional(authorization: Optional[str] = Header(None)):
    """Get current user from authorization header, return None if not authenticated."""
    if not authorization:
        return None
    
    try:
        token = authorization.split(" ")[1] if authorization.startswith("Bearer ") else authorization
        auth_storage = get_auth_storage()
        return auth_storage.verify_session(token)
    except Exception:
        return None


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


# Memos endpoints
@app.get("/memos")
async def get_memos():
    """Get all memos from the data/memos directory"""
    memos_dir = BASE_DIR / "data" / "memos"
    if not memos_dir.exists():
        memos_dir.mkdir(parents=True, exist_ok=True)
        return {"memos": []}

    memos = []
    # Sort files by name for consistent ordering
    sorted_files = sorted(memos_dir.glob("*.md"), key=lambda x: x.name)
    
    for file_path in sorted_files:
        name = file_path.stem.replace("_", " ").title()
        description = f"Memo - {file_path.name}"
        memos.append({
            "id": file_path.stem,
            "name": name,
            "description": description,
            "filename": file_path.name,
            "path": str(file_path.relative_to(BASE_DIR)),
            "type": "memo",
            "format": "markdown",
            "lastModified": file_path.stat().st_mtime
        })
    
    return {"memos": memos}


@app.post("/memos")
async def create_memo(memo_update: DocumentUpdate):
    """Create a new memo"""
    try:
        memos_dir = BASE_DIR / "data" / "memos"
        memos_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from name
        filename = memo_update.filename or f"{memo_update.name.lower().replace(' ', '_')}.md"
        if not filename.endswith('.md'):
            filename += '.md'
        
        file_path = memos_dir / filename
        
        # Write content to file
        content = memo_update.content or ""
        file_path.write_text(content)
        
        # Return memo data
        memo = {
            "id": file_path.stem,
            "name": memo_update.name,
            "description": memo_update.description or f"Memo - {filename}",
            "filename": filename,
            "path": str(file_path.relative_to(BASE_DIR)),
            "type": "memo",
            "format": "markdown",
            "content": content,
            "lastModified": file_path.stat().st_mtime
        }
        
        return {"success": True, "memo": memo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/memos/{memo_id}")
async def update_memo(memo_id: str, memo_update: DocumentUpdate):
    """Update an existing memo"""
    try:
        memos_dir = BASE_DIR / "data" / "memos"
        file_path = memos_dir / f"{memo_id}.md"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Memo not found")
        
        # Update content
        if memo_update.content is not None:
            file_path.write_text(memo_update.content)
        
        # Return updated memo data
        memo = {
            "id": memo_id,
            "name": memo_update.name or file_path.stem.replace("_", " ").title(),
            "description": memo_update.description or f"Memo - {file_path.name}",
            "filename": file_path.name,
            "path": str(file_path.relative_to(BASE_DIR)),
            "type": "memo",
            "format": "markdown",
            "content": memo_update.content,
            "lastModified": file_path.stat().st_mtime
        }
        
        return {"success": True, "memo": memo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memos/{memo_id}")
async def delete_memo(memo_id: str):
    """Delete a specific memo"""
    try:
        memos_dir = BASE_DIR / "data" / "memos"
        file_path = memos_dir / f"{memo_id}.md"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Memo not found")
        
        file_path.unlink()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Interviews endpoints
@app.get("/interviews")
async def get_interviews():
    """Get all interviews from the data/interviews directory"""
    interviews_dir = INTERVIEWS_DIR
    if not interviews_dir.exists():
        interviews_dir.mkdir(parents=True, exist_ok=True)
        return {"interviews": []}

    interviews = []
    # Sort files by name for consistent ordering
    sorted_files = sorted(interviews_dir.glob("*.yaml"), key=lambda x: x.name)
    
    for file_path in sorted_files:
        try:
            with open(file_path, 'r') as f:
                interview_data = yaml.safe_load(f) or {}
            
            # Use filename stem as ID
            interview_id = file_path.stem
            
            interview = {
                "id": interview_id,
                "name": interview_data.get("name", file_path.stem.replace("_", " ").title()),
                "description": interview_data.get("description", f"Interview - {file_path.name}"),
                "filename": file_path.name,
                "path": str(file_path.relative_to(BASE_DIR)),
                "status": interview_data.get("status", "pending"),
                "priority": interview_data.get("priority", "medium"),
                "notes": interview_data.get("notes", ""),
                "lastModified": file_path.stat().st_mtime
            }
            interviews.append(interview)
        except Exception as e:
            print(f"Error reading interview file {file_path}: {e}")
            continue
    
    return {"interviews": interviews}


@app.post("/interviews")
async def create_interview(interview_update: InterviewUpdate):
    """Create a new interview"""
    try:
        interviews_dir = INTERVIEWS_DIR
        interviews_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from name
        filename = interview_update.filename or f"{interview_update.name.lower().replace(' ', '_')}.yaml"
        if not filename.endswith('.yaml'):
            filename += '.yaml'
        
        file_path = interviews_dir / filename
        
        # Create interview data
        interview_data = {
            "name": interview_update.name,
            "description": interview_update.description or f"Interview - {filename}",
            "status": interview_update.status or "pending",
            "priority": interview_update.priority or "medium",
            "notes": interview_update.notes or ""
        }
        
        # Write to file
        with open(file_path, 'w') as f:
            yaml.dump(interview_data, f, default_flow_style=False, allow_unicode=True)
        
        # Return interview data
        interview = {
            "id": file_path.stem,
            "name": interview_data["name"],
            "description": interview_data["description"],
            "filename": filename,
            "path": str(file_path.relative_to(BASE_DIR)),
            "status": interview_data["status"],
            "priority": interview_data["priority"],
            "notes": interview_data["notes"],
            "lastModified": file_path.stat().st_mtime
        }
        
        return {"success": True, "interview": interview}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/interviews/{interview_id}")
async def update_interview(interview_id: str, interview_update: InterviewUpdate):
    """Update an existing interview"""
    try:
        interviews_dir = INTERVIEWS_DIR
        file_path = interviews_dir / f"{interview_id}.yaml"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Interview not found")
        
        # Read existing data
        with open(file_path, 'r') as f:
            interview_data = yaml.safe_load(f) or {}
        
        # Update fields that are provided
        if interview_update.name is not None:
            interview_data["name"] = interview_update.name
        if interview_update.description is not None:
            interview_data["description"] = interview_update.description
        if interview_update.status is not None:
            interview_data["status"] = interview_update.status
        if interview_update.priority is not None:
            interview_data["priority"] = interview_update.priority
        if interview_update.notes is not None:
            interview_data["notes"] = interview_update.notes
        
        # Write back to file
        with open(file_path, 'w') as f:
            yaml.dump(interview_data, f, default_flow_style=False, allow_unicode=True)
        
        # Return updated interview data
        interview = {
            "id": interview_id,
            "name": interview_data["name"],
            "description": interview_data["description"],
            "filename": file_path.name,
            "path": str(file_path.relative_to(BASE_DIR)),
            "status": interview_data["status"],
            "priority": interview_data["priority"],
            "notes": interview_data["notes"],
            "lastModified": file_path.stat().st_mtime
        }
        
        return {"success": True, "interview": interview}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/interviews/{interview_id}")
async def delete_interview(interview_id: str):
    """Delete a specific interview"""
    try:
        interviews_dir = INTERVIEWS_DIR
        file_path = interviews_dir / f"{interview_id}.yaml"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Interview not found")
        
        file_path.unlink()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket for real-time chat
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Get instances
    settings = get_settings()
    mcp_manager = get_mcp_manager()
    if not mcp_manager.is_initialized():
        await mcp_manager.initialize()
    
    # Get model
    from pydantic_ai.models.openai import OpenAIModel
    provider = OpenAIProvider(
        api_key=settings.llm_api_key
    )
    model = OpenAIModel(
        settings.model_choice,
        provider=provider
    )
    
    # Create specialized agents
    agents = {
        "brave_search": BraveSearchAgent(model),
        "filesystem": FilesystemAgent(model),
        "rag": CloudRAGAgent(model, use_cloud=True)  # Use cloud-enabled RAG
    }
    
    # Initialize primary agent with model and agents
    primary_agent = PrimaryAgent(model, agents)
    
    try:
        while True:
            try:
                # Receive message with better error handling
                raw_data = await websocket.receive_text()
                
                # Skip empty messages
                if not raw_data or raw_data.strip() == "":
                    continue
                    
                print(f"WebSocket received raw data: {raw_data[:100]}...")  # Debug log
                
                # Try to parse as JSON first, fallback to plain text
                import json
                try:
                    data = json.loads(raw_data)
                    message = data.get("message", raw_data)
                except json.JSONDecodeError:
                    # If not JSON, treat as plain text message
                    message = raw_data
                
                print(f"WebSocket processing message: {message}")  # Debug log
                
                # Use primary agent to handle the request
                response_parts = []
                async for delta in primary_agent.run_stream(message):
                    response_parts.append(delta)
                    await websocket.send_text(delta)
                
                # Send end marker
                await websocket.send_text("[END]")
            except Exception as e:
                print(f"WebSocket message processing error: {e}")
                await websocket.send_text(f"Error: {str(e)}")
                
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()


# Authentication endpoints
@app.post("/auth/register")
async def register(user_data: UserRegistration):
    """Register a new user."""
    auth_storage = get_auth_storage()
    result = auth_storage.register_user(user_data.email, user_data.password)
    
    if result["success"]:
        return {
            "success": True,
            "user": result["user"],
            "token": result["token"]
        }
    else:
        raise HTTPException(status_code=400, detail=result["error"])


@app.post("/auth/login")
async def login(user_data: UserLogin):
    """Login a user."""
    auth_storage = get_auth_storage()
    result = auth_storage.login_user(user_data.email, user_data.password)
    
    if result["success"]:
        return {
            "success": True,
            "user": result["user"],
            "token": result["token"]
        }
    else:
        raise HTTPException(status_code=401, detail=result["error"])


@app.get("/auth/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current user information."""
    return {
        "success": True,
        "user": current_user
    }


@app.post("/auth/logout")
async def logout(current_user = Depends(get_current_user)):
    """Logout user (client should discard token)."""
    return {
        "success": True,
        "message": "Logged out successfully"
    }


@app.post("/auth/setup-default-user")
async def setup_default_user():
    """Create the default user and migrate existing data."""
    auth_storage = get_auth_storage()
    result = auth_storage.create_default_user("huynguyenvt1989@gmail.com", "Vungtau1989")
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=400, detail=result["error"])


if __name__ == "__main__":
    import uvicorn
    ensure_dirs()
    uvicorn.run(app, host="0.0.0.0", port=8000)