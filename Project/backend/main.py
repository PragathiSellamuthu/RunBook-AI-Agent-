import os
import threading
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import datetime

from .agent_runner import OpsAgentRunner
from . import database as db

# Initialize App
app = FastAPI(title="RUNBOOK AGENT Dashboard")

# Global State
server_status = {
    "nginx": "healthy",
    "database": "healthy",
    "cpu": "normal",
    "disk": "normal",
    "agent_busy": False,
    "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

@app.get("/api/runbooks/{name}")
async def get_runbook_content(name: str):
    path = f"runbooks/{name}"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Runbook not found")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"content": content}

activity_feed = []
confirm_event = threading.Event()

# Initialize Agent
agent = OpsAgentRunner(activity_feed, server_status, confirm_event)

# Initialize DB on Startup
@app.on_event("startup")
async def startup():
    db.init_db()

# --- ROUTES ---

@app.get("/")
async def read_index():
    return FileResponse("frontend/index.html")

@app.get("/api/status")
async def get_status():
    server_status["last_updated"] = datetime.datetime.now().strftime("%H:%M:%S")
    return server_status

@app.post("/api/trigger/{failure_type}")
async def trigger_failure(failure_type: str, background_tasks: BackgroundTasks):
    mapping = {
        "nginx_down": ("nginx_down.md", "nginx", "down"),
        "high_cpu": ("high_cpu.md", "cpu", "critical"),
        "database_failure": ("database_failure.md", "database", "down"),
        "disk_full": ("disk_full.md", "disk", "critical")
    }
    
    if failure_type not in mapping:
        raise HTTPException(status_code=400, detail="Invalid failure type")
    
    runbook, key, status = mapping[failure_type]
    
    if server_status[key] != "healthy" and server_status[key] != "normal":
         return {"message": "Incident already in progress", "runbook": runbook}

    server_status[key] = status
    
    # Start Agent Loop in background
    background_tasks.add_task(agent.run_runbook, runbook, failure_type)
    
    return {"message": "Agent activated", "runbook": runbook}

@app.get("/api/agent/feed")
async def get_feed():
    return activity_feed

@app.post("/api/confirm")
async def confirm_step():
    confirm_event.set()
    return {"message": "Step confirmed, continuing"}

@app.post("/api/skip")
async def skip_step():
    confirm_event.set() # For demo, skip just confirms and continues
    return {"message": "Step skipped, continuing"}

@app.get("/api/history")
async def get_history():
    return db.get_history(limit=20)

@app.get("/api/stats")
async def get_stats():
    return db.get_stats()

# Serve other static files if any
# app.mount("/static", StaticFiles(directory="frontend"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
