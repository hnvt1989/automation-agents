from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel

from src.core.config import get_settings
from src.mcp import get_mcp_manager
from src.agents.primary import PrimaryAgent
from src.agents.brave_search import BraveSearchAgent
from src.agents.filesystem import FilesystemAgent
from src.agents.rag import RAGAgent

BASE_DIR = Path(__file__).resolve().parent.parent
TASKS_FILE = BASE_DIR / "data" / "tasks.md"
FRONTEND_DIR = BASE_DIR / "frontend"


class Task(BaseModel):
    name: str
    description: str | None = None


class TaskList(BaseModel):
    tasks: list[Task]

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
    if not TASKS_FILE.exists():
        return {"tasks": []}

    text = TASKS_FILE.read_text()
    lines = [line[2:] for line in text.splitlines() if line.startswith("- ")]
    tasks = []
    for line in lines:
        if ":" in line:
            name, desc = line.split(":", 1)
            tasks.append({"name": name.strip(), "description": desc.strip()})
        else:
            tasks.append({"name": line.strip(), "description": ""})
    return {"tasks": tasks}


@app.put("/tasks")
async def update_tasks(task_list: TaskList):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api_server:app", host="0.0.0.0", port=8000)
