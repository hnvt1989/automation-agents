from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
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

BASE_DIR = Path(__file__).resolve().parent.parent
TASKS_FILE = BASE_DIR / "data" / "tasks.md"
TASKS_YAML_FILE = BASE_DIR / "data" / "tasks.yaml"
DAILY_LOGS_FILE = BASE_DIR / "data" / "daily_logs.yaml"
FRONTEND_DIR = BASE_DIR / "frontend"
VA_NOTES_DIR = BASE_DIR / "data" / "va_notes"
MEETING_NOTES_DIR = BASE_DIR / "data" / "meeting_notes"


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


# Load configuration from environment file
ENV_FILE = BASE_DIR / "local.env"

def load_config_from_env():
    """Load configuration from environment variables"""
    # Clear existing env vars to avoid pollution
    for key in ["DOCUMENTS_DIR", "NOTES_DIR", "TASKS_FILE", "LOGS_FILE"]:
        if key in os.environ:
            del os.environ[key]
    
    load_dotenv(ENV_FILE, override=True)
    return {
        "documents_dir": os.getenv("DOCUMENTS_DIR", str(VA_NOTES_DIR)),
        "notes_dir": os.getenv("NOTES_DIR", str(MEETING_NOTES_DIR)),
        "tasks_file": os.getenv("TASKS_FILE", str(TASKS_YAML_FILE)),
        "logs_file": os.getenv("LOGS_FILE", str(DAILY_LOGS_FILE))
    }

def save_config_to_env(config):
    """Save configuration to environment file"""
    env_path = find_dotenv(str(ENV_FILE)) or str(ENV_FILE)
    
    # Ensure file exists
    if not os.path.exists(env_path):
        Path(env_path).touch()
    
    # Save each configuration value
    set_key(env_path, "DOCUMENTS_DIR", config.get("documents_dir", ""))
    set_key(env_path, "NOTES_DIR", config.get("notes_dir", ""))
    set_key(env_path, "TASKS_FILE", config.get("tasks_file", ""))
    set_key(env_path, "LOGS_FILE", config.get("logs_file", ""))

# Load configuration on startup
config_storage = load_config_from_env()

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
async def read_root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

settings = get_settings()
mcp_manager = get_mcp_manager()

@app.on_event("startup")
async def startup_event():
    await mcp_manager.initialize()
    provider = OpenAIProvider(base_url=settings.base_url, api_key=settings.llm_api_key)
    model = OpenAIModel(settings.model_choice, provider=provider)
    agents = {
        "brave_search": BraveSearchAgent(model),
        "filesystem": FilesystemAgent(model),
        "rag": RAGAgent(model),
    }
    app.state.primary_agent = PrimaryAgent(model, agents)

@app.on_event("shutdown")
async def shutdown_event():
    await mcp_manager.shutdown()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            query = await websocket.receive_text()
            async for delta in app.state.primary_agent.run_stream(query):
                await websocket.send_text(delta)
            await websocket.send_text("[END]")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text(f"Error: {str(e)}")


@app.get("/tasks")
async def get_tasks():
    tasks_file = Path(config_storage["tasks_file"])
    if not tasks_file.exists():
        return {"tasks": []}
    
    try:
        with open(tasks_file, 'r') as f:
            yaml_tasks = yaml.safe_load(f) or []
        
        tasks = []
        for task in yaml_tasks:
            # Format the task for frontend display
            formatted_task = {
                "name": task.get("title", "Untitled Task"),
                "description": f"ID: {task.get('id', 'N/A')} | Priority: {task.get('priority', 'N/A')} | Status: {task.get('status', 'N/A')}",
                "id": task.get("id"),
                "priority": task.get("priority"),
                "status": task.get("status"),
                "tags": task.get("tags", []),
                "dueDate": task.get("due_date"),
                "estimate_hours": task.get("estimate_hours")
            }
            tasks.append(formatted_task)
        
        return {"tasks": tasks}
    except Exception as e:
        print(f"Error reading tasks.yaml: {e}")
        return {"tasks": []}


@app.put("/tasks")
async def update_tasks(task_list: TaskList):
    # For now, just update the old tasks.md file
    # In a real implementation, you might want to update the YAML file
    lines = ["# Tasks"]
    for t in task_list.tasks:
        line = f"- {t.name}"
        if t.description:
            line += f": {t.description}"
        lines.append(line)
    try:
        TASKS_FILE.write_text("\n".join(lines))
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"success": True}


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


@app.get("/logs")
async def get_logs():
    logs_file = Path(config_storage["logs_file"])
    if not logs_file.exists():
        return {"logs": []}
    
    try:
        with open(logs_file, 'r') as f:
            logs_data = yaml.safe_load(f) or {}
        
        logs = []
        # Process each date entry
        for date, daily_logs in logs_data.items():
            if daily_logs:
                for log in daily_logs:
                    formatted_log = {
                        "name": log.get("description", "No description"),
                        "description": f"Date: {date} | ID: {log.get('log_id', 'N/A')} | Hours: {log.get('actual_hours', 0)}h",
                        "date": date,
                        "log_id": log.get("log_id"),
                        "actual_hours": log.get("actual_hours"),
                        # Include raw description for editor
                        "raw_description": log.get("description", "")
                    }
                    logs.append(formatted_log)
        
        # Sort logs by date (newest first)
        logs.sort(key=lambda x: x["date"], reverse=True)
        
        return {"logs": logs}
    except Exception as e:
        print(f"Error reading daily_logs.yaml: {e}")
        return {"logs": []}


@app.post("/tasks")
async def create_task(task_update: TaskUpdate):
    """Create a new task"""
    try:
        tasks_file = Path(config_storage["tasks_file"])
        with open(tasks_file, 'r') as f:
            tasks = yaml.safe_load(f) or []
        
        # Create new task with provided data
        new_task = {
            'id': f"TASK-{len(tasks) + 1}",  # Generate a simple ID
            'title': task_update.name or task_update.title or "New Task",
            'status': task_update.status or 'pending',
            'priority': task_update.priority or 'medium',
            'due_date': task_update.due_date,
            'tags': task_update.tags or [],
            'estimate_hours': None
        }
        
        # Add to tasks list
        tasks.append(new_task)
        
        # Write back to file
        with open(tasks_file, 'w') as f:
            yaml.dump(tasks, f, default_flow_style=False, allow_unicode=True)
        
        return {"success": True, "task": new_task}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/tasks/{task_index}")
async def delete_task(task_index: int):
    """Delete a specific task by index"""
    try:
        tasks_file = Path(config_storage["tasks_file"])
        with open(tasks_file, 'r') as f:
            tasks = yaml.safe_load(f) or []
        
        if 0 <= task_index < len(tasks):
            # Remove the task at the specified index
            deleted_task = tasks.pop(task_index)
            
            # Write back to file
            with open(tasks_file, 'w') as f:
                yaml.dump(tasks, f, default_flow_style=False, allow_unicode=True)
            
            return {"success": True, "message": "Task deleted successfully", "deleted_task": deleted_task}
        else:
            raise HTTPException(status_code=404, detail="Task not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/tasks/{task_index}")
async def update_task(task_index: int, task_update: TaskUpdate):
    """Update a specific task by index"""
    try:
        tasks_file = Path(config_storage["tasks_file"])
        with open(tasks_file, 'r') as f:
            tasks = yaml.safe_load(f) or []
        
        if 0 <= task_index < len(tasks):
            # Update the task with new values
            if task_update.title is not None:
                tasks[task_index]['title'] = task_update.title
            if task_update.name is not None:
                tasks[task_index]['title'] = task_update.name  # Map name to title
            if task_update.status is not None:
                tasks[task_index]['status'] = task_update.status
            if task_update.priority is not None:
                tasks[task_index]['priority'] = task_update.priority
            if task_update.due_date is not None:
                tasks[task_index]['due_date'] = task_update.due_date
            if task_update.tags is not None:
                tasks[task_index]['tags'] = task_update.tags
            
            # Preserve existing fields that weren't updated
            for key in ['id', 'estimate_hours']:
                if key in tasks[task_index] and key not in task_update.dict(exclude_unset=True):
                    # Keep existing value
                    pass
            
            # Write back to file
            with open(tasks_file, 'w') as f:
                yaml.dump(tasks, f, default_flow_style=False, allow_unicode=True)
            
            return {"success": True, "task": tasks[task_index]}
        else:
            raise HTTPException(status_code=404, detail="Task not found")
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


@app.post("/logs")
async def create_log(log_update: LogUpdate):
    """Create a new log entry"""
    try:
        logs_file = Path(config_storage["logs_file"])
        with open(logs_file, 'r') as f:
            logs_data = yaml.safe_load(f) or {}
        
        # Get the date for the log
        date = log_update.date or datetime.now().strftime('%Y-%m-%d')
        
        # Create new log entry
        new_log = {
            'log_id': log_update.log_id or f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'description': log_update.name or log_update.description or "New log entry",
            'actual_hours': log_update.actual_hours or 0
        }
        
        # Add to the date's logs
        if date not in logs_data:
            logs_data[date] = []
        logs_data[date].append(new_log)
        
        # Write back to file
        with open(logs_file, 'w') as f:
            yaml.dump(logs_data, f, default_flow_style=False, allow_unicode=True)
        
        return {"success": True, "log": new_log}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/logs/{log_index}")
async def delete_log(log_index: int):
    """Delete a specific log by index"""
    try:
        logs_file = Path(config_storage["logs_file"])
        with open(logs_file, 'r') as f:
            logs_data = yaml.safe_load(f) or {}
        
        # Convert to flat list with indices
        flat_logs = []
        for date, daily_logs in logs_data.items():
            if daily_logs:
                for log in daily_logs:
                    flat_logs.append((date, log))
        
        # Sort by date (newest first) to match GET /logs endpoint
        flat_logs.sort(key=lambda x: x[0], reverse=True)
        
        if 0 <= log_index < len(flat_logs):
            date, log_to_delete = flat_logs[log_index]
            
            # Remove the log from its date
            logs_data[date].remove(log_to_delete)
            
            # If no logs left for this date, remove the date entry
            if not logs_data[date]:
                del logs_data[date]
            
            # Write back to file
            with open(logs_file, 'w') as f:
                yaml.dump(logs_data, f, default_flow_style=False, allow_unicode=True)
            
            return {"success": True, "message": "Log deleted successfully", "deleted_log": log_to_delete}
        else:
            raise HTTPException(status_code=404, detail="Log not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/logs/{log_index}")
async def update_log(log_index: int, log_update: LogUpdate):
    """Update a specific log by index"""
    try:
        logs_file = Path(config_storage["logs_file"])
        with open(logs_file, 'r') as f:
            logs_data = yaml.safe_load(f) or {}
        
        # Convert to flat list with indices
        flat_logs = []
        for date, daily_logs in logs_data.items():
            if daily_logs:
                for log in daily_logs:
                    flat_logs.append((date, log))
        
        # Sort by date (newest first) to match GET /logs endpoint
        flat_logs.sort(key=lambda x: x[0], reverse=True)
        
        if 0 <= log_index < len(flat_logs):
            date, log = flat_logs[log_index]
            
            # Update the log
            if log_update.name is not None:
                log['description'] = log_update.name
            if log_update.description is not None:
                log['description'] = log_update.description
            if log_update.actual_hours is not None:
                log['actual_hours'] = log_update.actual_hours
            if log_update.log_id is not None:
                log['log_id'] = log_update.log_id
            
            # Write back to file
            with open(logs_file, 'w') as f:
                yaml.dump(logs_data, f, default_flow_style=False, allow_unicode=True)
            
            return {"success": True, "log": log}
        else:
            raise HTTPException(status_code=404, detail="Log not found")
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
            
            # Note: We're not updating the filename or other metadata in this simple version
            # In a production app, you might want to handle file renaming, etc.
            
            return {"success": True, "message": "Document updated"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config")
async def get_config():
    """Get current configuration paths"""
    return config_storage


@app.put("/config")
async def update_config(config_update: ConfigUpdate):
    """Update configuration paths with validation"""
    errors = []
    
    # Validate documents_dir
    if config_update.documents_dir is not None:
        if not config_update.documents_dir:
            errors.append("documents_dir cannot be empty")
        else:
            path = Path(config_update.documents_dir)
            if not path.exists():
                errors.append(f"documents_dir '{config_update.documents_dir}' does not exist")
            elif not path.is_dir():
                errors.append(f"documents_dir '{config_update.documents_dir}' is not a directory")
    
    # Validate notes_dir
    if config_update.notes_dir is not None:
        if not config_update.notes_dir:
            errors.append("notes_dir cannot be empty")
        else:
            path = Path(config_update.notes_dir)
            if not path.exists():
                errors.append(f"notes_dir '{config_update.notes_dir}' does not exist")
            elif not path.is_dir():
                errors.append(f"notes_dir '{config_update.notes_dir}' is not a directory")
    
    # Validate tasks_file
    if config_update.tasks_file is not None:
        if not config_update.tasks_file:
            errors.append("tasks_file cannot be empty")
        else:
            path = Path(config_update.tasks_file)
            if not path.exists():
                errors.append(f"tasks_file '{config_update.tasks_file}' does not exist")
            elif not path.is_file():
                errors.append(f"tasks_file '{config_update.tasks_file}' is not a file")
    
    # Validate logs_file
    if config_update.logs_file is not None:
        if not config_update.logs_file:
            errors.append("logs_file cannot be empty")
        else:
            path = Path(config_update.logs_file)
            if not path.exists():
                errors.append(f"logs_file '{config_update.logs_file}' does not exist")
            elif not path.is_file():
                errors.append(f"logs_file '{config_update.logs_file}' is not a file")
    
    # If there are validation errors, return 400
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    
    # Update configuration (only update provided fields)
    if config_update.documents_dir is not None:
        config_storage["documents_dir"] = str(Path(config_update.documents_dir).absolute())
    if config_update.notes_dir is not None:
        config_storage["notes_dir"] = str(Path(config_update.notes_dir).absolute())
    if config_update.tasks_file is not None:
        config_storage["tasks_file"] = str(Path(config_update.tasks_file).absolute())
    if config_update.logs_file is not None:
        config_storage["logs_file"] = str(Path(config_update.logs_file).absolute())
    
    # Save to environment file
    save_config_to_env(config_storage)
    
    return {"success": True, "message": "Configuration updated successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api_server:app", host="0.0.0.0", port=8000)
