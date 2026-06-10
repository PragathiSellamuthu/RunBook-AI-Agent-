import os
import threading
import datetime
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from . import database as db
from .agent_runner import OpsAgentRunner

# Project base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="RUNBOOK AGENT Dashboard",
    description="Backend API for RunBook Agent"
)

# Enable CORS for frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
server_status = {
    "nginx": "healthy",
    "database": "healthy",
    "cpu": "normal",
    "disk": "normal",
    "agent_busy": False,
    "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

activity_feed = []
confirm_event = threading.Event()

# Initialize Agent Runner
agent = OpsAgentRunner(activity_feed, server_status, confirm_event)

@app.on_event("startup")
def startup_event():
    """Initializes the database on startup."""
    db.init_db()
    print("[Database] SQLite database initialized.")

@app.get("/", response_class=HTMLResponse)
def read_index():
    """Serves the frontend/index.html file."""
    index_path = os.path.join(BASE_DIR, "frontend", "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="frontend/index.html not found")
        
    with open(index_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/api/status")
def get_status():
    """Returns the current server health and agent busy status."""
    server_status["last_updated"] = datetime.datetime.now().strftime("%H:%M:%S")
    server_status["agent_busy"] = agent.is_running
    return server_status

@app.post("/api/trigger/{failure_type}")
def trigger_failure(failure_type: str, background_tasks: BackgroundTasks):
    """Triggers an infrastructure failure and runs the agent in a background task."""
    mapping = {
        "nginx_down": ("nginx_down.md", "nginx", "down"),
        "high_cpu": ("high_cpu.md", "cpu", "critical"),
        "database_failure": ("database_failure.md", "database", "down"),
        "disk_full": ("disk_full.md", "disk", "critical")
    }
    
    if failure_type not in mapping:
        raise HTTPException(status_code=400, detail="Invalid failure type")
    
    runbook, key, status = mapping[failure_type]
    
    if agent.is_running:
        raise HTTPException(status_code=400, detail="Agent is already busy resolving a failure scenario.")
        
    # Set the server state to failed
    server_status[key] = status
    
    # Clear the activity log for the new run
    activity_feed.clear()
    
    # Launch agent runbook runner in the background using FastAPI's thread pool
    background_tasks.add_task(agent.run_runbook, runbook, failure_type)
    
    return {"message": "Agent activated", "runbook": runbook}

@app.get("/api/agent/feed")
def get_feed():
    """Returns the list of agent log activities."""
    return activity_feed

@app.post("/api/confirm")
def confirm_step():
    """Approves execution of the pending risky step."""
    agent.skip_pending_step = False
    confirm_event.set()
    return {"message": "Step confirmed, continuing"}

@app.post("/api/abort")
def abort_step():
    """Aborts execution of the pending risky step and stops the agent."""
    agent.abort_pending_step = True
    confirm_event.set()
    return {"message": "Execution aborted."}

@app.get("/api/runbooks/{name}")
def get_runbook_content(name: str):
    """Returns the raw Markdown text content of a runbook file."""
    path = os.path.join(BASE_DIR, "runbooks", name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Runbook {name} not found")
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"content": content}

@app.get("/api/history")
def get_history():
    """Fetches execution history logs from SQLite database."""
    try:
        return db.get_history(limit=20)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

@app.get("/api/history/{execution_id}/steps")
def get_history_steps(execution_id: int):
    """Fetches steps for a specific execution."""
    try:
        return db.get_execution_steps(execution_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

@app.delete("/api/history/{execution_id}")
def delete_history_record(execution_id: int):
    """Deletes a specific execution history record."""
    try:
        db.delete_history(execution_id)
        return {"message": "Deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

@app.get("/api/stats")
def get_stats():
    """Fetches real-time resolution statistics and averages."""
    try:
        return db.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

@app.get("/api/export/csv")
def export_latest_csv():
    """Serves the latest runbook execution CSV file for download."""
    csv_path = os.path.join(BASE_DIR, "exports", "latest.csv")
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="No runbook execution export is available yet.")
        
    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename=f"latest_execution_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
