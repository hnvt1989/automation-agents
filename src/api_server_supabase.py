from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response, Depends, Header
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
# Optional pydantic-ai imports
try:
    from pydantic_ai.providers.openai import OpenAIProvider
    from pydantic_ai.models.openai import OpenAIModel
    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False
    OpenAIProvider = None
    OpenAIModel = None
# import yaml  # Not needed for Vercel deployment
from datetime import datetime
import os
from dotenv import load_dotenv, set_key, find_dotenv
from typing import Optional

from src.core.config import get_settings

# Optional imports for Vercel compatibility
try:
    from src.mcp import get_mcp_manager
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    get_mcp_manager = None

try:
    from src.agents.primary import PrimaryAgent, PrimaryAgentDeps
    from src.agents.brave_search import BraveSearchAgent
    from src.agents.filesystem import FilesystemAgent
    from src.agents.rag_cloud import CloudRAGAgent
    from src.agents.analyzer import AnalyzerAgent
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False
    PrimaryAgent = None
from src.storage.supabase_ops import SupabaseOperations
from src.storage.auth_storage import AuthStorage
from src.storage.document_manager import DocumentManager
from src.storage.user_settings import UserSettingsStorage
from src.utils.logging import get_logger

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


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


class UserSettingsUpdate(BaseModel):
    google_drive_calendar_secret_link: str | None = None
    theme: str | None = None


class UserSetting(BaseModel):
    setting_key: str
    setting_value: str


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
    app.state.user_settings_storage = UserSettingsStorage()

# Add CORS middleware
# Production-ready CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Static file serving
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")



# Authentication helper functions
def get_auth_storage() -> AuthStorage:
    return app.state.auth_storage


def get_user_settings_storage() -> UserSettingsStorage:
    return app.state.user_settings_storage


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


# Document manager will be initialized per request with user context
def get_document_manager(current_user = Depends(get_current_user)):
    """Get document manager for current user."""
    user_id = current_user["user_id"]
    return DocumentManager(user_id=user_id)


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


# Document endpoints using Supabase vector storage
@app.get("/documents")
async def get_documents(doc_manager: DocumentManager = Depends(get_document_manager)):
    """Get all documents from Supabase vector storage."""
    try:
        documents = doc_manager.get_documents("document")
        
        # Format for frontend compatibility
        formatted_docs = []
        for i, doc in enumerate(documents):
            formatted_docs.append({
                "name": doc["name"],
                "description": doc["description"] or "",
                "filename": doc.get("metadata", {}).get("filename", doc["name"]),
                "path": f"supabase://documents/{doc['id']}",
                "id": doc["id"],
                "index": i,  # For compatibility with existing frontend
                "lastModified": doc.get("updated_at") or doc.get("created_at")
            })
        
        return {"documents": formatted_docs}
    except Exception as e:
        log_error(f"Error getting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{doc_identifier}/content")
async def get_document_content(doc_identifier: str, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Get the content of a specific document by ID or index (for backward compatibility)"""
    try:
        # Check if doc_identifier is a number (index) or UUID (ID)
        if doc_identifier.isdigit():
            # It's an index - convert to ID
            documents = doc_manager.get_documents("document")
            doc_index = int(doc_identifier)
            
            if 0 <= doc_index < len(documents):
                doc_id = documents[doc_index]["id"]
            else:
                raise HTTPException(status_code=404, detail="Document index out of range")
        else:
            # It's already a document ID
            doc_id = doc_identifier
        
        content = doc_manager.get_document_content(doc_id, "document")
        if content is not None:
            return {"content": content}
        else:
            raise HTTPException(status_code=404, detail="Document content not found")
    except ValueError:
        # doc_identifier is not a number, treat as ID
        content = doc_manager.get_document_content(doc_identifier, "document")
        if content is not None:
            return {"content": content}
        else:
            raise HTTPException(status_code=404, detail="Document content not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notes")
async def get_notes(doc_manager: DocumentManager = Depends(get_document_manager)):
    """Get all notes from Supabase vector storage."""
    try:
        notes = doc_manager.get_documents("note")
        
        # Format for frontend compatibility
        formatted_notes = []
        for i, note in enumerate(notes):
            formatted_notes.append({
                "name": note["name"],
                "description": note["description"] or "",
                "filename": note.get("metadata", {}).get("filename", note["name"]),
                "path": f"supabase://notes/{note['id']}",
                "id": note["id"],
                "index": i,  # For compatibility with existing frontend
                "lastModified": note.get("updated_at") or note.get("created_at")
            })
        
        return {"notes": formatted_notes}
    except Exception as e:
        log_error(f"Error getting notes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notes/{note_identifier}/content")
async def get_note_content(note_identifier: str, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Get the content of a specific note by ID or index (for backward compatibility)"""
    try:
        # Check if note_identifier is a number (index) or UUID (ID)
        if note_identifier.isdigit():
            # It's an index - convert to ID
            notes = doc_manager.get_documents("note")
            note_index = int(note_identifier)
            
            if 0 <= note_index < len(notes):
                note_id = notes[note_index]["id"]
            else:
                raise HTTPException(status_code=404, detail="Note index out of range")
        else:
            # It's already a note ID
            note_id = note_identifier
        
        content = doc_manager.get_document_content(note_id, "note")
        if content is not None:
            return {"content": content}
        else:
            raise HTTPException(status_code=404, detail="Note content not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notes")
async def create_note(note_update: NoteUpdate, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Create a new note"""
    try:
        content = note_update.content or f"# {note_update.name}\n\n{note_update.description or ''}"
        filename = note_update.name.lower().replace(' ', '_') + '.md'
        
        doc_id = doc_manager.add_document(
            content=content,
            name=note_update.name,
            doc_type="note",
            description=note_update.description,
            filename=filename
        )
        
        # Get updated list to find index
        notes = doc_manager.get_documents("note")
        new_index = next((i for i, n in enumerate(notes) if n["id"] == doc_id), -1)
        
        return {"success": True, "message": "Note created", "filename": filename, "index": new_index, "id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/notes/{note_identifier}")
async def update_note(note_identifier: str, note_update: NoteUpdate, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Update a specific note by ID or index (for backward compatibility)"""
    try:
        # Check if note_identifier is a number (index) or UUID (ID)
        if note_identifier.isdigit():
            # It's an index - convert to ID
            notes = doc_manager.get_documents("note")
            note_index = int(note_identifier)
            
            if 0 <= note_index < len(notes):
                doc_id = notes[note_index]["id"]
            else:
                raise HTTPException(status_code=404, detail="Note index out of range")
        else:
            # It's already a note ID
            doc_id = note_identifier
        
        success = doc_manager.update_document(
            doc_id=doc_id,
            doc_type="note",
            content=note_update.content,
            name=note_update.name,
            description=note_update.description
        )
        
        if success:
            return {"success": True, "message": "Note updated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update note")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents")
async def create_document(doc_update: DocumentUpdate, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Create a new document"""
    try:
        content = doc_update.content or f"# {doc_update.name}\n\n{doc_update.description or ''}"
        filename = doc_update.filename or f"{doc_update.name.lower().replace(' ', '_')}.md"
        
        doc_id = doc_manager.add_document(
            content=content,
            name=doc_update.name,
            doc_type="document",
            description=doc_update.description,
            filename=filename
        )
        
        # Get updated list to find index
        documents = doc_manager.get_documents("document")
        new_index = next((i for i, d in enumerate(documents) if d["id"] == doc_id), -1)
        
        return {"success": True, "message": "Document created", "filename": filename, "index": new_index, "id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/documents/{doc_identifier}")
async def update_document(doc_identifier: str, doc_update: DocumentUpdate, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Update a specific document by ID or index (for backward compatibility)"""
    try:
        # Check if doc_identifier is a number (index) or UUID (ID)
        if doc_identifier.isdigit():
            # It's an index - convert to ID
            documents = doc_manager.get_documents("document")
            doc_index = int(doc_identifier)
            
            if 0 <= doc_index < len(documents):
                doc_id = documents[doc_index]["id"]
            else:
                raise HTTPException(status_code=404, detail="Document index out of range")
        else:
            # It's already a document ID
            doc_id = doc_identifier
        
        success = doc_manager.update_document(
            doc_id=doc_id,
            doc_type="document",
            content=doc_update.content,
            name=doc_update.name,
            description=doc_update.description
        )
        
        if success:
            return {"success": True, "message": "Document updated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update document")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Delete a specific document by ID"""
    try:
        success = doc_manager.delete_document(doc_id, "document")
        
        if success:
            return {"success": True, "message": "Document deleted"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete document")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Memos endpoints using Supabase vector storage
@app.get("/memos")
async def get_memos(doc_manager: DocumentManager = Depends(get_document_manager)):
    """Get all memos from Supabase vector storage"""
    try:
        memos = doc_manager.get_documents("memo")
        
        # Format for frontend compatibility
        formatted_memos = []
        for memo in memos:
            formatted_memos.append({
                "id": memo["id"],
                "name": memo["name"],
                "description": memo["description"] or "",
                "filename": memo.get("metadata", {}).get("filename", memo["name"]),
                "path": f"supabase://memos/{memo['id']}",
                "type": "memo",
                "format": "markdown",
                "lastModified": memo.get("updated_at") or memo.get("created_at")
            })
        
        return {"memos": formatted_memos}
    except Exception as e:
        log_error(f"Error getting memos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memos")
async def create_memo(memo_update: DocumentUpdate, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Create a new memo"""
    try:
        content = memo_update.content or ""
        filename = memo_update.filename or f"{memo_update.name.lower().replace(' ', '_')}.md"
        if not filename.endswith('.md'):
            filename += '.md'
        
        doc_id = doc_manager.add_document(
            content=content,
            name=memo_update.name,
            doc_type="memo",
            description=memo_update.description,
            filename=filename
        )
        
        # Return memo data
        memo = {
            "id": doc_id,
            "name": memo_update.name,
            "description": memo_update.description or f"Memo - {filename}",
            "filename": filename,
            "path": f"supabase://memos/{doc_id}",
            "type": "memo",
            "format": "markdown",
            "content": content
        }
        
        return {"success": True, "memo": memo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/memos/{memo_id}")
async def update_memo(memo_id: str, memo_update: DocumentUpdate, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Update an existing memo"""
    try:
        success = doc_manager.update_document(
            doc_id=memo_id,
            doc_type="memo",
            content=memo_update.content,
            name=memo_update.name,
            description=memo_update.description
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Memo not found")
        
        # Get updated content for response
        content = doc_manager.get_document_content(memo_id, "memo")
        
        # Return updated memo data
        memo = {
            "id": memo_id,
            "name": memo_update.name,
            "description": memo_update.description,
            "filename": f"{memo_update.name.lower().replace(' ', '_')}.md" if memo_update.name else None,
            "path": f"supabase://memos/{memo_id}",
            "type": "memo",
            "format": "markdown",
            "content": content
        }
        
        return {"success": True, "memo": memo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memos/{memo_id}")
async def delete_memo(memo_id: str, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Delete a specific memo"""
    try:
        success = doc_manager.delete_document(memo_id, "memo")
        
        if not success:
            raise HTTPException(status_code=404, detail="Memo not found")
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memos/{memo_id}/content")
async def get_memo_content(memo_id: str, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Get content of a specific memo"""
    try:
        content = doc_manager.get_document_content(memo_id, "memo")
        
        if content is None:
            raise HTTPException(status_code=404, detail="Memo not found")
        
        return Response(content=content, media_type="text/plain")
    except Exception as e:
        log_error(f"Error getting memo content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Interviews endpoints using Supabase vector storage
@app.get("/interviews")
async def get_interviews(doc_manager: DocumentManager = Depends(get_document_manager)):
    """Get all interviews from Supabase vector storage"""
    try:
        interviews = doc_manager.get_documents("interview")
        
        # Format for frontend compatibility
        formatted_interviews = []
        for interview in interviews:
            # Extract metadata fields
            metadata = interview.get("metadata", {})
            formatted_interviews.append({
                "id": interview["id"],
                "name": interview["name"],
                "description": interview["description"] or "",
                "filename": metadata.get("filename", interview["name"]),
                "path": f"supabase://interviews/{interview['id']}",
                "status": metadata.get("status", "pending"),
                "priority": metadata.get("priority", "medium"),
                "notes": metadata.get("original_notes", ""),
                "lastModified": interview.get("updated_at") or interview.get("created_at")
            })
        
        return {"interviews": formatted_interviews}
    except Exception as e:
        log_error(f"Error getting interviews: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/interviews")
async def create_interview(interview_update: InterviewUpdate, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Create a new interview"""
    try:
        # Create content from interview data
        content = f"# {interview_update.name}\n\n"
        if interview_update.description:
            content += f"**Description:** {interview_update.description}\n\n"
        content += f"**Status:** {interview_update.status or 'pending'}\n"
        content += f"**Priority:** {interview_update.priority or 'medium'}\n\n"
        if interview_update.notes:
            content += f"## Notes\n\n{interview_update.notes}\n"
        
        filename = interview_update.filename or f"{interview_update.name.lower().replace(' ', '_')}.yaml"
        if not filename.endswith('.yaml'):
            filename += '.yaml'
        
        doc_id = doc_manager.add_document(
            content=content,
            name=interview_update.name,
            doc_type="interview",
            description=interview_update.description or f"Interview - {filename}",
            filename=filename,
            metadata={
                "status": interview_update.status or "pending",
                "priority": interview_update.priority or "medium",
                "original_notes": interview_update.notes or ""
            }
        )
        
        # Return interview data
        interview = {
            "id": doc_id,
            "name": interview_update.name,
            "description": interview_update.description or f"Interview - {filename}",
            "filename": filename,
            "path": f"supabase://interviews/{doc_id}",
            "status": interview_update.status or "pending",
            "priority": interview_update.priority or "medium",
            "notes": interview_update.notes or ""
        }
        
        return {"success": True, "interview": interview}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/interviews/{interview_id}")
async def update_interview(interview_id: str, interview_update: InterviewUpdate, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Update an existing interview"""
    try:
        # Create updated content
        content = f"# {interview_update.name or 'Interview'}\n\n"
        if interview_update.description:
            content += f"**Description:** {interview_update.description}\n\n"
        content += f"**Status:** {interview_update.status or 'pending'}\n"
        content += f"**Priority:** {interview_update.priority or 'medium'}\n\n"
        if interview_update.notes:
            content += f"## Notes\n\n{interview_update.notes}\n"
        
        # Update metadata
        metadata = {}
        if interview_update.status:
            metadata["status"] = interview_update.status
        if interview_update.priority:
            metadata["priority"] = interview_update.priority
        if interview_update.notes:
            metadata["original_notes"] = interview_update.notes
        
        success = doc_manager.update_document(
            doc_id=interview_id,
            doc_type="interview",
            content=content,
            name=interview_update.name,
            description=interview_update.description,
            metadata=metadata
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        # Return updated interview data
        interview = {
            "id": interview_id,
            "name": interview_update.name,
            "description": interview_update.description,
            "filename": f"{interview_update.name.lower().replace(' ', '_')}.yaml" if interview_update.name else None,
            "path": f"supabase://interviews/{interview_id}",
            "status": interview_update.status,
            "priority": interview_update.priority,
            "notes": interview_update.notes
        }
        
        return {"success": True, "interview": interview}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/interviews/{interview_id}")
async def delete_interview(interview_id: str, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Delete a specific interview"""
    try:
        success = doc_manager.delete_document(interview_id, "interview")
        
        if not success:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/interviews/{interview_id}/content")
async def get_interview_content(interview_id: str, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Get content of a specific interview"""
    try:
        content = doc_manager.get_document_content(interview_id, "interview")
        
        if content is None:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        return Response(content=content, media_type="text/plain")
    except Exception as e:
        log_error(f"Error getting interview content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Document indexing endpoints
@app.post("/index/{doc_type}/{doc_id}")
async def index_document(doc_type: str, doc_id: str, doc_manager: DocumentManager = Depends(get_document_manager)):
    """Index a document for search by fetching its content from Supabase and re-indexing it."""
    try:
        # Validate document type
        valid_types = ["document", "note", "memo", "interview"]
        if doc_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid document type. Must be one of: {valid_types}")
        
        # Get the document content from Supabase
        content = doc_manager.get_document_content(doc_id, doc_type)
        if content is None:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get document metadata
        documents = doc_manager.get_documents(doc_type)
        document = next((doc for doc in documents if doc["id"] == doc_id), None)
        if document is None:
            raise HTTPException(status_code=404, detail="Document metadata not found")
        
        # Re-index the document by updating it (this triggers re-indexing in DocumentManager)
        success = doc_manager.update_document(
            doc_id=doc_id,
            doc_type=doc_type,
            content=content,  # Re-index with existing content
            name=document["name"],
            description=document["description"]
        )
        
        if success:
            logger.info(f"Successfully re-indexed {doc_type}: {document['name']} (ID: {doc_id})")
            return {
                "success": True,
                "message": f"Successfully indexed {doc_type}: {document['name']}",
                "document_id": doc_id,
                "document_name": document["name"]
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to index document")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error indexing document {doc_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error indexing document: {str(e)}")


# WebSocket for real-time chat
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Try to get user from query parameters (token)
    user_id = None
    try:
        token = websocket.query_params.get("token")
        if token:
            auth_storage = get_auth_storage()
            user = auth_storage.verify_session(token)
            if user:
                user_id = user["user_id"]
    except Exception as e:
        print(f"WebSocket auth error: {e}")
    
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
                
                # Use primary agent to handle the request with user context
                response_parts = []
                async for delta in primary_agent.run_stream(message, user_id=user_id):
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


# User Settings endpoints
@app.get("/user/settings")
async def get_user_settings(
    current_user = Depends(get_current_user),
    settings_storage: UserSettingsStorage = Depends(get_user_settings_storage)
):
    """Get all settings for the current user."""
    try:
        user_id = current_user["user_id"]
        settings = settings_storage.get_user_settings(user_id)
        
        # Provide default values for known settings
        default_settings = {
            "google_drive_calendar_secret_link": "",
            "theme": "starwars"
        }
        
        # Merge defaults with user settings
        for key, default_value in default_settings.items():
            if key not in settings:
                settings[key] = default_value
        
        return {
            "success": True,
            "settings": settings
        }
    except Exception as e:
        logger.error(f"Error getting user settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user settings")


@app.get("/user/settings/{setting_key}")
async def get_user_setting(
    setting_key: str,
    current_user = Depends(get_current_user),
    settings_storage: UserSettingsStorage = Depends(get_user_settings_storage)
):
    """Get a specific setting for the current user."""
    try:
        user_id = current_user["user_id"]
        setting_value = settings_storage.get_user_setting(user_id, setting_key)
        
        if setting_value is None:
            # Return default value for known settings
            defaults = {
                "google_drive_calendar_secret_link": "",
                "theme": "starwars"
            }
            setting_value = defaults.get(setting_key, "")
        
        return {
            "success": True,
            "setting_key": setting_key,
            "setting_value": setting_value
        }
    except Exception as e:
        logger.error(f"Error getting user setting {setting_key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user setting")


@app.put("/user/settings")
async def update_user_settings(
    settings_update: UserSettingsUpdate,
    current_user = Depends(get_current_user),
    settings_storage: UserSettingsStorage = Depends(get_user_settings_storage)
):
    """Update user settings."""
    try:
        user_id = current_user["user_id"]
        
        # Build settings dictionary from update model
        settings_to_update = {}
        update_data = settings_update.dict(exclude_unset=True)
        
        for key, value in update_data.items():
            if value is not None:
                settings_to_update[key] = value
        
        if not settings_to_update:
            return {
                "success": True,
                "message": "No settings to update"
            }
        
        success = settings_storage.update_user_settings(user_id, settings_to_update)
        
        if success:
            return {
                "success": True,
                "message": f"Updated {len(settings_to_update)} setting(s)",
                "updated_settings": settings_to_update
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update settings")
    except Exception as e:
        logger.error(f"Error updating user settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user settings")


@app.put("/user/settings/{setting_key}")
async def update_user_setting(
    setting_key: str,
    setting: UserSetting,
    current_user = Depends(get_current_user),
    settings_storage: UserSettingsStorage = Depends(get_user_settings_storage)
):
    """Update a specific user setting."""
    try:
        user_id = current_user["user_id"]
        
        success = settings_storage.set_user_setting(user_id, setting_key, setting.setting_value)
        
        if success:
            return {
                "success": True,
                "message": f"Updated setting {setting_key}",
                "setting_key": setting_key,
                "setting_value": setting.setting_value
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update setting")
    except Exception as e:
        logger.error(f"Error updating user setting {setting_key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user setting")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)