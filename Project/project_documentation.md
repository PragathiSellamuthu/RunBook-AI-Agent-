# RunBook AI Agent - Complete Project Documentation

This document contains the entire folder structure and source code needed to rebuild this project from scratch.

## Folder Structure
```text
project/
├── requirements.txt
├── README.md
├── frontend/
│   └── index.html
├── runbook_agent/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── agent_runner.py
│   ├── mcp_tool.py
│   └── runbook_parser.py
├── test_parser.py
└── runbooks/
    ├── database_failure.md
    ├── disk_full.md
    ├── high_cpu.md
    ├── nginx_down.md
    └── riskless_test.md
```

## Source Code Files

### File: `requirements.txt`
```text
fastapi>=0.109.0
uvicorn>=0.27.0
openai>=1.12.0
requests>=2.31.0
pyyaml>=6.0.1

```

### File: `README.md`
```markdown
# 🤖 RunBook Agent — Autonomous IT Operations Runbook Agent

[![Python 3.11](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-v0.109.0-green.svg)](https://fastapi.tiangolo.com/)
[![Ollama LLaMA3](https://img.shields.io/badge/Ollama-llama3-purple.svg)](https://ollama.com/)
[![SQLite](https://img.shields.io/badge/SQLite-built--in-lightgrey.svg)](https://www.sqlite.org/)
[![Discord Webhook](https://img.shields.io/badge/Discord-Webhook-blue.svg)](https://discord.com/developers/docs/resources/webhook)
[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

RunBook Agent is a production-ready, autonomous IT operations agent designed to detect, triage, and automatically resolve infrastructure failures using Markdown-defined runbooks and simulated Model Context Protocol (MCP) commands. It runs an intelligent, interactive loop that classifies steps as **SAFE** or **RISKY**, prompts for human verification on risky actions, sends notifications to Discord in real-time, and records all activities in SQLite.

---

## 🏗️ Architecture

```mermaid
graph TD
    A[Frontend OBS Dashboard] <-->|Polls /api/status & /api/agent/feed| B[FastAPI Web Server]
    B -->|Invokes runbook resolution| C[RunBook Agent Loop]
    C -->|Classifies Steps| D[Ollama LLaMA3 / Groq / Rules Fallback]
    C -->|Blocks on RISKY steps| E[Human Operator Confirmation]
    C -->|Executes simulated commands| F[ShellExecutorMCPTool]
    C -->|Logs runs & steps| G[SQLite Database]
    C -->|Dispatches logs| H[Discord Webhook Alerts]
    C -->|Writes telemetry| I[exports/latest.csv]
```

---

## 🛠️ Windows Setup Instructions

Run these commands in order in a Windows PowerShell console:

1. **Clone & Navigate to Project Directory**
   ```powershell
   cd project
   ```

2. **Install Dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Start Local LLaMA3 (Optional)**
   Make sure you have [Ollama](https://ollama.com/) installed, then pull and run LLaMA3:
   ```powershell
   ollama pull llama3
   ```

4. **Run FastAPI Server**
   Start the application using Uvicorn:
   ```powershell
   python -m uvicorn runbook_agent.main:app --reload --port 8000
   ```

5. **Access the Dashboard**
   Open your browser and navigate to: [http://localhost:8000](http://localhost:8000)

---

## 🔴 Failure Scenarios

You can trigger and test 5 scenarios from the dashboard control buttons:
- **Nginx Server Down**: Resolves service listening on port 80.
- **High CPU Usage**: Locates and kills the runaway processor thread.
- **Database Connection Failed**: Verifies ports and restarts PostgreSQL.
- **Disk Space Critical**: Cleans up files by compressing log archives.
- **Riskless Execution Test**: Safe operation test — automated Discord notification (INFO).

---

## 🔌 Production Upgrade: PostgreSQL Integration

In multi-server containerized environments, replace the lightweight SQLite database with a central PostgreSQL database.

### Docker Setup

```bash
docker run --name runbook-postgres -e POSTGRES_DB=runbook_agent -e POSTGRES_USER=ops_agent -e POSTGRES_PASSWORD=securepassword -p 5432:5432 -d postgres:15
```

### Connection String Example

In production, update `database.py` connection client using `psycopg2`:

```python
import psycopg2

DATABASE_URL = "postgresql://ops_agent:securepassword@localhost:5432/runbook_agent"

def get_connection():
    return psycopg2.connect(DATABASE_URL)
```

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE details.
Built with ❤️ for the Infinite Computer Solutions Hackathon 2024.

```

### File: `runbook_agent/__init__.py`
```python
# RunBook Agent Backend Package

```

### File: `runbook_agent/main.py`
```python
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

@app.post("/api/skip")
def skip_step():
    """Skips execution of the pending risky step (resumes the loop)."""
    agent.skip_pending_step = True
    confirm_event.set()
    return {"message": "Step skipped, continuing"}

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

```

### File: `runbook_agent/database.py`
```python
import sqlite3
from datetime import datetime
import os

# Database file path inside the project directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "opsbot.db")

def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database by creating tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Executions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        failure_type TEXT,
        runbook_name TEXT,
        started_at TEXT,
        completed_at TEXT,
        total_steps INTEGER,
        completed_steps INTEGER,
        status TEXT, -- running, completed, failed
        discord_sent INTEGER DEFAULT 0
    )
    """)
    
    # Steps table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        execution_id INTEGER,
        step_number INTEGER,
        step_type TEXT,
        description TEXT,
        command TEXT,
        output TEXT,
        status TEXT,
        needs_confirm INTEGER,
        confirmed_at TEXT,
        executed_at TEXT,
        FOREIGN KEY (execution_id) REFERENCES executions (id)
    )
    """)
    
    conn.commit()
    conn.close()

def start_execution(failure_type: str, runbook_name: str) -> int:
    """Inserts a new runbook execution entry into the database and returns its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    started_at = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO executions (failure_type, runbook_name, started_at, total_steps, completed_steps, status, discord_sent)
    VALUES (?, ?, ?, 0, 0, 'running', 0)
    """, (failure_type, runbook_name, started_at))
    execution_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return execution_id

def update_execution_steps(execution_id: int, total_steps: int):
    """Updates the total step count of an execution."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE executions SET total_steps = ? WHERE id = ?", (total_steps, execution_id))
    conn.commit()
    conn.close()

def complete_execution(execution_id: int, status: str, completed_steps: int):
    """Updates the execution status, completed steps counter, and end timestamp."""
    conn = get_connection()
    cursor = conn.cursor()
    completed_at = datetime.now().isoformat()
    cursor.execute("""
    UPDATE executions
    SET status = ?, completed_steps = ?, completed_at = ?
    WHERE id = ?
    """, (status, completed_steps, completed_at, execution_id))
    conn.commit()
    conn.close()

def log_step(execution_id: int, step_data: dict):
    """Logs individual step run using step dictionary."""
    conn = get_connection()
    cursor = conn.cursor()
    executed_at = datetime.now().isoformat()
    
    cursor.execute("""
    INSERT INTO steps (execution_id, step_number, step_type, description, command, output, status, needs_confirm, confirmed_at, executed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        execution_id,
        step_data.get("step_number"),
        step_data.get("step_type"),
        step_data.get("description"),
        step_data.get("command"),
        step_data.get("output"),
        step_data.get("status"),
        1 if step_data.get("needs_confirm") or step_data.get("step_type") == "RISKY" else 0,
        step_data.get("confirmed_at"),
        executed_at
    ))
    conn.commit()
    conn.close()

def increment_discord_sent(execution_id: int):
    """Increments the discord sent counter for an execution."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE executions SET discord_sent = discord_sent + 1 WHERE id = ?", (execution_id,))
    conn.commit()
    conn.close()

def get_history(limit: int = 20):
    """Fetches the last N executions, sorted by start time descending."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, failure_type, runbook_name, started_at, completed_at, total_steps, completed_steps, status, discord_sent
    FROM executions
    ORDER BY id DESC
    LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    
    history = []
    for r in rows:
        history.append({
            "id": r["id"],
            "failure_type": r["failure_type"],
            "runbook_name": r["runbook_name"],
            "started_at": r["started_at"],
            "completed_at": r["completed_at"],
            "total_steps": r["total_steps"],
            "completed_steps": r["completed_steps"],
            "status": r["status"],
            "discord_sent": r["discord_sent"]
        })
    conn.close()
    return history

def get_stats():
    """Computes execution dashboard statistics from SQLite."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Total executions
    cursor.execute("SELECT COUNT(*) FROM executions WHERE status = 'completed'")
    total_runs = cursor.fetchone()[0]
    
    # 2. Steps completed successfully
    cursor.execute("SELECT COUNT(*) FROM steps WHERE status = 'SUCCESS'")
    steps_today = cursor.fetchone()[0]
    
    # 3. Discord alerts sent
    cursor.execute("SELECT SUM(discord_sent) FROM executions")
    discord_sent = cursor.fetchone()[0] or 0
    
    # 4. Average resolution time in minutes
    # We do a database-agnostic parsing in Python for safety, or parse in SQL. Let's do it in Python to avoid SQLite strftime issues.
    cursor.execute("""
    SELECT started_at, completed_at FROM executions WHERE status = 'completed' AND completed_at IS NOT NULL
    """)
    completed_runs = cursor.fetchall()
    
    total_duration_secs = 0
    completed_count = len(completed_runs)
    
    for run in completed_runs:
        try:
            start = datetime.fromisoformat(run["started_at"])
            end = datetime.fromisoformat(run["completed_at"])
            total_duration_secs += (end - start).total_seconds()
        except Exception:
            pass
            
    if completed_count > 0:
        avg_res_mins = (total_duration_secs / completed_count) / 60.0
    else:
        avg_res_mins = 0.0
        
    conn.close()
    return {
        "total_runs": total_runs,
        "steps_today": steps_today,
        "discord_sent": discord_sent,
        "avg_resolution_mins": round(avg_res_mins, 1)
    }

```

### File: `runbook_agent/agent_runner.py`
```python
import time
import datetime
import threading
import requests
import os
import csv
from openai import OpenAI
from .mcp_tool import ShellExecutorMCPTool
from .runbook_parser import RunbookParser
from . import database as db

# Configuration
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "https://discord.com/api/webhooks/1513869705314570320/ZLSV5Qi4G2K78gux_KLPUYIFtl2w6F5R8ztTqGlXBjCkH3wUxNNl5z85TKjLO-yQlJJV")
OLLAMA_URL = "http://localhost:11434/v1"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Directory settings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")

class OpsAgentRunner:
    def __init__(self, activity_feed, server_status, confirm_event):
        self.mcp = ShellExecutorMCPTool(server_status)
        self.activity_feed = activity_feed
        self.server_status = server_status
        self.confirm_event = confirm_event
        self.current_execution_id = None
        self.is_running = False
        
        # Local Ollama Llama3 client (OpenAI compatible)
        self.ollama = OpenAI(
            base_url=OLLAMA_URL,
            api_key="ollama",
            max_retries=0,
            timeout=2.0
        )
        
        self.ai_mode_warning = ""

    def log_activity(self, entry):
        entry['timestamp'] = datetime.datetime.now().strftime("%H:%M:%S")
        self.activity_feed.append(entry)
        if len(self.activity_feed) > 50:
            self.activity_feed.pop(0)
        
        # Print to console for Windows log visibility safely
        try:
            safe_status = entry['status'].encode('ascii', 'ignore').decode()
            safe_msg = entry['message'].encode('ascii', 'ignore').decode().replace('\n', ' ')
            print(f"[{entry['timestamp']}] [{safe_status}] {safe_msg}")
        except Exception:
            pass

    def send_discord(self, message):
        try:
            safe_log_msg = message.encode('ascii', 'ignore').decode().replace('\n', ' ')
            print(f"[DISCORD DEBUG] send_discord: {safe_log_msg[:100]}...")
            
            if not DISCORD_WEBHOOK or "YOUR_WEBHOOK_URL" in DISCORD_WEBHOOK or DISCORD_WEBHOOK == "":
                print(f"[DISCORD DEBUG] Webhook bypass (not configured).")
                return
                
            payload = {"content": message}
            res = requests.post(DISCORD_WEBHOOK, json=payload, timeout=5)
            print(f"[DISCORD DEBUG] Webhook response status: {res.status_code}")
            if res.status_code in [200, 204] and self.current_execution_id:
                db.increment_discord_sent(self.current_execution_id)
        except Exception as e:
            print(f"[DISCORD DEBUG] Discord error: {type(e).__name__}")

    def classify_step(self, step_number, step_type, step_description, command, failure_context):
        """
        Ask Llama3 to classify this step as SAFE or RISKY.
        Supports Groq fallback and rule-based fallback.
        """
        prompt = f"""You are an expert IT operations AI agent named RUNBOOK AGENT.
You are executing a runbook to fix a critical infrastructure failure.

Step number: {step_number}
Step type from runbook: {step_type}
Step description: {step_description}
Command to execute: {command}
Current failure context: {failure_context}

Should this step be automatically executed without human confirmation?

Criteria:
SAFE steps = execute automatically always
RISKY steps = require human confirmation because they restart services, kill processes, or modify/delete files

Respond EXACTLY in this format only:
AUTO_EXECUTE: yes
REASONING: one sentence why

OR:
AUTO_EXECUTE: no  
REASONING: one sentence why confirmation needed"""

        self.ai_mode_warning = ""

        # 1. Try Local Ollama LLaMA3
        try:
            payload = {
                "model": "llama3",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0
            }
            res = requests.post(f"{OLLAMA_URL}/chat/completions", json=payload, timeout=1.5)
            if res.status_code == 200:
                content = res.json()['choices'][0]['message']['content'].strip()
                return self._parse_classification(content)
            else:
                raise Exception(f"HTTP {res.status_code}")
        except Exception as e_ollama:
            print(f"[Info] Ollama LLaMA3 offline ({e_ollama}). Trying Groq fallback...", flush=True)
            
            # 2. Try Groq API Fallback
            if GROQ_API_KEY and GROQ_API_KEY != "YOUR_GROQ_API_KEY_HERE":
                try:
                    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
                    res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=2.0)
                    if res.status_code == 200:
                        content = res.json()['choices'][0]['message']['content'].strip()
                        return self._parse_classification(content)
                    else:
                        raise Exception(f"HTTP {res.status_code}")
                except Exception as e_groq:
                    print(f"[Info] Groq fallback failed ({e_groq}). Falling back to rules...", flush=True)
            else:
                print("[Info] Groq API Key not configured. Falling back to rules...", flush=True)

        # 3. Rule-Based Fallback
        self.ai_mode_warning = "AI offline, using runbook rules"
        auto_execute = (step_type.upper() == "SAFE")
        reasoning = f"Rule-based fallback: step type is {step_type}."
        return {"auto_execute": auto_execute, "reasoning": reasoning}

    def _parse_classification(self, content):
        """Helper to parse LLM response text."""
        auto_execute = True
        reasoning = "Classified by AI"
        
        match_auto = None
        for line in content.splitlines():
            if line.upper().startswith("AUTO_EXECUTE:"):
                val = line.split(":", 1)[1].strip().lower()
                if "no" in val:
                    auto_execute = False
                else:
                    auto_execute = True
                match_auto = True
            elif line.upper().startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()

        if not match_auto:
            if "auto_execute: no" in content.lower():
                auto_execute = False
            else:
                auto_execute = True
            if "reasoning:" in content.lower():
                parts = content.lower().split("reasoning:", 1)
                if len(parts) > 1:
                    reasoning = parts[1].split("\n")[0].strip()
                    
        return {"auto_execute": auto_execute, "reasoning": reasoning}

    def run_runbook(self, runbook_file, failure_type):
        if self.is_running:
            return
        
        self.is_running = True
        self.server_status['agent_busy'] = True
        start_time = time.time()
        start_timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Parse Runbook
        runbook_path = os.path.join(BASE_DIR, "runbooks", runbook_file)
        steps = RunbookParser.parse(runbook_path)
        
        if not steps:
            self.log_activity({"status": "ERROR", "message": f"Runbook {runbook_file} not found or empty."})
            self.is_running = False
            self.server_status['agent_busy'] = False
            self._restore_server_status(failure_type)
            return

        # 2. Start Database Execution
        self.current_execution_id = db.start_execution(failure_type, runbook_file)
        db.update_execution_steps(self.current_execution_id, len(steps))

        # 3. Incident Detected Notification
        self.log_activity({"status": "FAILURE DETECTED", "message": f"{failure_type.replace('_', ' ').title()} System Critical!"})
        self.send_discord(
            f"🚨 **INCIDENT DETECTED**\n"
            f"**Type:** {failure_type.replace('_', ' ').title()}\n"
            f"**Runbook:** `{runbook_file}` activated\n"
            f"**Agent:** Starting autonomous resolution...\n"
            f"**Time:** {start_timestamp_str}"
        )
        self.log_activity({"status": "AGENT ACTIVATED", "message": f"Executing {runbook_file}"})
        
        steps_history_log = [] # used for CSV export later
        completed_count = 0
        
        try:
            has_warned_ai = False
            for step in steps:
                step_num = step['step_number']
                step_type = step['step_type']
                desc = step['description']
                cmd = step['command']
                expected = step['expected_output']
                risk = step.get('risk', 'Service interruption')
                
                # Log step start
                self.log_activity({"status": "INFO", "message": f"🔍 Step {step_num} Starting: {desc}"})
                
                # Classify step
                classification = self.classify_step(
                    step_num, 
                    step_type, 
                    desc, 
                    cmd, 
                    failure_type
                )
                
                auto_execute = classification['auto_execute']
                reasoning = classification['reasoning']
                
                if self.ai_mode_warning and not has_warned_ai:
                    self.log_activity({"status": "WARNING", "message": f"⚠️ {self.ai_mode_warning} (defaulting to runbook configuration)"})
                    has_warned_ai = True
                
                should_skip = False
                # Confirmation block if RISKY
                if not auto_execute:
                    self.log_activity({
                        "status": "AWAITING CONFIRMATION", 
                        "message": f"Step {step_num}: {cmd}",
                        "needs_confirm": True,
                        "risk": f"{desc}. {risk}"
                    })
                    
                    self.send_discord(
                        f"⚠️ **HUMAN CONFIRMATION REQUIRED**\n"
                        f"**Runbook:** `{runbook_file}` | **Step {step_num}**\n"
                        f"**Command:** `{cmd}`\n"
                        f"**Risk:** {risk}\n"
                        f"**Action:** Approve in Dashboard"
                    )
                    
                    self.confirm_event.clear()
                    self.skip_pending_step = False
                    # Block waiting for human confirmation POST `/api/confirm` or `/api/skip`
                    self.confirm_event.wait()
                    
                    if getattr(self, 'skip_pending_step', False):
                        self.log_activity({"status": "INFO", "message": "⏭️ Human skipped risky step."})
                        should_skip = True
                    else:
                        self.log_activity({"status": "INFO", "message": "✅ Human confirmed risky step. Continuing..."})

                if should_skip:
                    cmd_success = True
                    cmd_output = "Step skipped by user."
                    step_status = "SKIPPED"
                    execution_time_ms = 0
                else:
                    # Execute via MCP Tool
                    mcp_res = self.mcp.execute(cmd, desc, failure_type)
                    cmd_success = mcp_res["success"]
                    cmd_output = mcp_res["output"] if cmd_success else mcp_res["error"]
                    step_status = "SUCCESS" if cmd_success else "FAILED"
                    execution_time_ms = mcp_res['execution_time_ms']
                    
                executed_timestamp = datetime.datetime.now().isoformat()
                
                # Log feed entry
                status_icon = "⏭️" if step_status == "SKIPPED" else ("✅" if cmd_success else "❌")
                action_text = "Skipped" if step_status == "SKIPPED" else "Complete"
                self.log_activity({
                    "status": step_status,
                    "message": f"{status_icon} Step {step_num} {action_text}: {desc}"
                })
                
                # Save step telemetry to CSV log list
                steps_history_log.append({
                    "timestamp": executed_timestamp,
                    "failure_type": failure_type,
                    "step_number": step_num,
                    "command": cmd,
                    "output": cmd_output.replace("\n", " "),
                    "status": step_status,
                    "duration_ms": execution_time_ms
                })

                # Update database step
                db.log_step(self.current_execution_id, {
                    "step_number": step_num,
                    "step_type": step_type,
                    "description": desc,
                    "command": cmd,
                    "expected_output": expected,
                    "output": cmd_output,
                    "status": step_status,
                    "needs_confirm": not auto_execute
                })
                
                if cmd_success:
                    completed_count += 1
                    self.send_discord(
                        f"✅ **Step {step_num} Complete** — `{runbook_file}`\n"
                        f"**Command:** `{cmd}`\n"
                        f"**Status:** SUCCESS | **Time:** {mcp_res['execution_time_ms']}ms"
                    )
                
                time.sleep(1.5) # Demo delay

            # Complete Execution
            duration_mins = int((time.time() - start_time) / 60)
            duration_secs = int((time.time() - start_time) % 60)
            
            # Reset server status back to healthy
            self._restore_server_status(failure_type)
            
            db.complete_execution(self.current_execution_id, "completed", completed_count)
            self.log_activity({"status": "RESOLVED", "message": f"🟢 ALL SYSTEMS OPERATIONAL: {failure_type.replace('_', ' ').title()}"})
            
            # Export to CSV
            self._export_to_csv(self.current_execution_id, steps_history_log)
            
            # Send Discord alert
            self.send_discord(
                f"🟢 **INCIDENT RESOLVED**\n"
                f"**Type:** {failure_type.replace('_', ' ').title()}\n"
                f"**Resolution Time:** {duration_mins}m {duration_secs}s\n"
                f"**Steps Executed:** {completed_count}/{len(steps)}\n"
                f"**Status:** OPERATIONAL"
            )

        except Exception as e:
            print(f"[Agent Runner Crash] {e}")
            self.log_activity({"status": "ERROR", "message": f"Agent Loop Crashed: {str(e)}"})
            self._restore_server_status(failure_type)
            db.complete_execution(self.current_execution_id, "failed", completed_count)
        finally:
            self.is_running = False
            self.server_status['agent_busy'] = False

    def _restore_server_status(self, failure_type):
        """Helper to restore healthy status states globally."""
        if failure_type == "nginx_down":
            self.server_status['nginx'] = "healthy"
        elif failure_type == "database_failure":
            self.server_status['database'] = "healthy"
        elif failure_type == "high_cpu":
            self.server_status['cpu'] = "normal"
        elif failure_type == "disk_full":
            self.server_status['disk'] = "normal"

    def _export_to_csv(self, execution_id, log_list):
        """Generates a CSV report file of the runbook resolution."""
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        exec_file = os.path.join(EXPORTS_DIR, f"execution_{execution_id}.csv")
        latest_file = os.path.join(EXPORTS_DIR, "latest.csv")
        
        headers = ["timestamp", "failure_type", "step_number", "command", "output", "status", "duration_ms"]
        
        for file_path in [exec_file, latest_file]:
            try:
                with open(file_path, mode="w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    for row in log_list:
                        writer.writerow(row)
            except Exception as csv_err:
                print(f"[CSV Export Error] Failed to write {file_path}: {csv_err}")

```

### File: `runbook_agent/mcp_tool.py`
```python
import datetime
import time

class ShellExecutorMCPTool:
    """
    MODEL CONTEXT PROTOCOL TOOL
    
    Execution layer for RunBook Agent.
    Simulates Linux commands on Windows with realistic outputs.
    """
    
    ALLOWED_COMMANDS = [
        "systemctl status nginx",
        "systemctl restart nginx",
        "tail -n 20 /var/log/nginx/error.log",
        "curl -I http://localhost",
        "top -bn1 | grep 'Cpu'",
        "ps aux --sort=-%cpu | head -10",
        "df -h",
        "du -sh /var/log/*",
        "systemctl status postgresql",
        "systemctl restart postgresql",
        "pg_isready -h localhost",
        "tail -n 20 /var/log/postgresql/postgresql-15-main.log",
        "free -m",
        "uptime",
        "tar -czf /backup/logs_$(date +%F).tar.gz /var/log/nginx/*.log",
        "rm /var/log/nginx/*.log.1",
        "ls -lh /var/log/nginx"
    ]
    
    def __init__(self, server_status_dict=None):
        self.start_time = datetime.datetime.now()
        # Reference to global status dict if provided
        self.server_status = server_status_dict or {
            "nginx": "healthy",
            "database": "healthy",
            "cpu": "normal",
            "disk": "normal"
        }

    def get_simulated_output(self, command, failure_context=None):
        timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        
        # STATE SYNC TRICK FOR NGINX
        if "systemctl restart nginx" in command:
            self.server_status["nginx"] = "healthy"
            # If we're executing high cpu runbook, restart nginx is the resolution step
            if failure_context == "high_cpu":
                self.server_status["cpu"] = "normal"
            return "Stopping nginx: [  OK  ]\nStarting nginx: [  OK  ]"

        if "systemctl status nginx" in command:
            # If server status shows down, return dead status
            if self.server_status.get("nginx") == "down" or failure_context == "nginx_down" and self.server_status.get("nginx") == "down":
                return f"""● nginx.service - A high performance web server and a reverse proxy server
   Loaded: loaded (/lib/systemd/system/nginx.service; enabled; vendor preset: enabled)
   Active: inactive (dead) since {timestamp}; 5min ago
     Docs: man:nginx(8)
 Main PID: 1234 (code=exited, status=0/SUCCESS)"""
            else:
                return f"""● nginx.service - A high performance web server and a reverse proxy server
   Loaded: loaded (/lib/systemd/system/nginx.service; enabled; vendor preset: enabled)
   Active: active (running) since {self.start_time.strftime("%a %Y-%m-%d %H:%M:%S")}; 2h 15min ago
 Main PID: 4567 (nginx)
    Tasks: 2 (limit: 4915)
   Memory: 8.2M
   CGroup: /system.slice/nginx.service
           ├─4567 nginx: master process /usr/sbin/nginx -g daemon on; master_process on;
           └─4568 nginx: worker process"""

        if "tail -n 20 /var/log/nginx/error.log" in command:
            if self.server_status.get("nginx") == "down" or failure_context == "nginx_down" and self.server_status.get("nginx") == "down":
                return f"""{timestamp} [alert] 4567#0: *123 worker process 4568 exited on signal 9
{timestamp} [error] 4567#0: *124 open() "/var/www/html/index.html" failed (2: No such file or directory)
{timestamp} [emerg] 4567#0: bind() to 0.0.0.0:80 failed (98: Address already in use)
{timestamp} [error] 1234#0: *125 upstream timed out (110: Connection timed out) while connecting to upstream"""
            return f"{timestamp} [notice] 4567#0: signal process started"

        if "curl -I http://localhost" in command:
            if self.server_status.get("nginx") == "down" or failure_context == "nginx_down" and self.server_status.get("nginx") == "down":
                return "curl: (7) Failed to connect to localhost port 80: Connection refused"
            return f"""HTTP/1.1 200 OK
Server: nginx/1.24.0
Date: {timestamp} GMT
Content-Type: text/html
Content-Length: 612
Connection: keep-alive"""

        # STATE SYNC TRICK FOR CPU
        if "top -bn1 | grep 'Cpu'" in command:
            if self.server_status.get("cpu") == "critical" or failure_context == "high_cpu" and self.server_status.get("cpu") == "critical":
                return "Cpu(s): 94.3 us, 3.1 sy, 0.0 ni, 1.2 id, 0.8 wa, 0.4 hi, 0.2 si, 0.0 st"
            return "Cpu(s): 12.5 us, 2.1 sy, 0.0 ni, 85.0 id, 0.2 wa, 0.1 hi, 0.1 si, 0.0 st"

        if "ps aux --sort=-%cpu | head -10" in command:
            if self.server_status.get("cpu") == "critical" or failure_context == "high_cpu" and self.server_status.get("cpu") == "critical":
                return """USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root      8812 87.4  4.2 1284560 342100 ?      Sl   10:00   5:23 /usr/bin/java -jar /apps/analytics-engine.jar
nginx     4567  2.1  0.5  158220  12440 ?      S    08:00   0:15 nginx: worker process
postgres  5432  1.8  2.1  456120  89120 ?      S    08:00   0:12 postgres: writer process"""
            return """USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
nginx     4567  0.5  0.5  158220  12440 ?      S    08:00   0:05 nginx: worker process
postgres  5432  0.4  2.1  456120  89120 ?      S    08:00   0:08 postgres: writer process"""

        # STATE SYNC TRICK FOR POSTGRESQL
        if "systemctl restart postgresql" in command:
            self.server_status["database"] = "healthy"
            return "Stopping postgresql: [  OK  ]\nStarting postgresql: [  OK  ]"

        if "systemctl status postgresql" in command:
            if self.server_status.get("database") == "down" or failure_context == "database_failure" and self.server_status.get("database") == "down":
                return f"""● postgresql.service - PostgreSQL RDBMS
   Loaded: loaded (/lib/systemd/system/postgresql.service; enabled; vendor preset: enabled)
   Active: failed (Result: exit-code) since {timestamp}; 2min ago
  Process: 9912 ExecStart=/usr/lib/postgresql/15/bin/pg_ctl start -D /var/lib/postgresql/15/main -l /var/log/postgresql/postgresql-15-main.log (code=exited, status=1/FAILURE)"""
            return f"""● postgresql.service - PostgreSQL RDBMS
   Loaded: loaded (/lib/systemd/system/postgresql.service; enabled; vendor preset: enabled)
   Active: active (running) since {self.start_time.strftime("%a %Y-%m-%d %H:%M:%S")}; 2h 14min ago
 Main PID: 5432 (postgres)"""

        if "pg_isready" in command:
            if self.server_status.get("database") == "down" or failure_context == "database_failure" and self.server_status.get("database") == "down":
                return "localhost:5432 - no response"
            return "localhost:5432 - accepting connections"

        if "tail -n 20 /var/log/postgresql/postgresql-15-main.log" in command:
            if self.server_status.get("database") == "down" or failure_context == "database_failure" and self.server_status.get("database") == "down":
                return f"""2026-06-10 14:02:11 UTC FATAL:  could not bind IPv4 address "0.0.0.0": Address already in use
2026-06-10 14:02:11 UTC HINT:   Is another postmaster already running on port 5432?
2026-06-10 14:02:12 UTC FATAL:  could not create shared memory segment: No space left on device
2026-06-10 14:02:12 UTC LOG:    database system is shut down"""
            return f"""2026-06-10 14:15:10 UTC LOG:    database system was shut down at 2026-06-10 14:14:50 UTC
2026-06-10 14:15:11 UTC LOG:    database system is ready to accept connections
2026-06-10 14:15:12 UTC LOG:    autovacuum launcher started"""

        # STATE SYNC TRICK FOR DISK
        if "tar -czf" in command:
            self.server_status["disk"] = "normal"
            return f"tar: Removing leading `/' from member names\nArchive /backup/logs_{timestamp.replace('/', '-').split(' ')[0]}.tar.gz created successfully."

        if "df -h" in command:
            if self.server_status.get("disk") == "critical" or failure_context == "disk_full" and self.server_status.get("disk") == "critical":
                return """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        40G   37G  1.2G  91% /
tmpfs           7.8G     0  7.8G   0% /dev/shm
/dev/sdb1       100G   20G   75G  21% /data"""
            return """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        40G   15G   23G  40% /
tmpfs           7.8G     0  7.8G   0% /dev/shm
/dev/sdb1       100G   20G   75G  21% /data"""

        if "du -sh /var/log/*" in command:
            return """16G     /var/log/nginx
4.5G    /var/log/syslog
1.2G    /var/log/postgresql
412M    /var/log/apt
124M    /var/log/journal"""

        if "ls -lh /var/log/nginx" in command:
            return """-rw-r----- 1 www-data adm 14G Jun 10 14:00 access.log.1
-rw-r----- 1 www-data adm 22M Jun 10 14:00 error.log
-rw-r----- 1 syslog   adm 4.5G Jun 10 14:02 syslog"""

        if "uptime" in command:
            return f" 14:15:10 up 2 days,  3:17,  1 user,  load average: { '11.45, 8.32, 4.10' if failure_context == 'high_cpu' else '0.22, 0.45, 0.51' }"

        if "free -m" in command:
            return """               total        used        free      shared  buff/cache   available
Mem:           15920        4812        8122         256        2986       10612
Swap:           2048         128        1920"""

        return f"Executed command: {command}\nStatus: SUCCESS\nOutput: [Simulated standard output for {command}]"

    def execute(self, command, step_description, failure_context):
        # Security check
        is_allowed = any(cmd in command for cmd in self.ALLOWED_COMMANDS)
        
        if not is_allowed:
            return {
                "success": False,
                "command": command,
                "output": f"ERROR: Command '{command}' is not in the security allowlist.",
                "error": "Permission Denied",
                "timestamp": datetime.datetime.now().isoformat(),
                "simulated": True,
                "execution_time_ms": 5
            }
        
        # Simulate execution time
        time.sleep(0.5) 
        
        output = self.get_simulated_output(command, failure_context)
        
        return {
            "success": True,
            "command": command,
            "output": output,
            "error": None,
            "timestamp": datetime.datetime.now().isoformat(),
            "simulated": True,
            "execution_time_ms": 520
        }

```

### File: `runbook_agent/runbook_parser.py`
```python
import re

class RunbookParser:
    """
    Parses markdown runbooks to extract structured steps for the AI Agent.
    """
    
    @staticmethod
    def parse(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            steps = []
            # Find all step blocks (e.g., ### Step 1)
            step_blocks = re.split(r'### Step \d+', content)[1:]
            
            for i, block in enumerate(step_blocks):
                step_num = i + 1
                
                # Extract fields using regex
                type_match = re.search(r'- \*\*Type:\*\* (SAFE|RISKY)', block)
                desc_match = re.search(r'- \*\*Description:\*\* (.*)', block)
                cmd_match = re.search(r'- \*\*Command:\*\* `(.*?)`', block)
                expected_match = re.search(r'- \*\*Expected Output:\*\* (.*)', block)
                risk_match = re.search(r'- \*\*Risk:\*\* (.*)', block)
                
                steps.append({
                    "step_number": step_num,
                    "step_type": type_match.group(1) if type_match else "SAFE",
                    "description": desc_match.group(1).strip() if desc_match else "",
                    "command": cmd_match.group(1).strip() if cmd_match else "",
                    "expected_output": expected_match.group(1).strip() if expected_match else "",
                    "risk": risk_match.group(1).strip() if risk_match else None
                })
            
            return steps
        except Exception as e:
            print(f"Error parsing runbook {file_path}: {e}")
            return []

```

### File: `frontend/index.html`
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RUNBOOK AGENT — Autonomous Runbook Execution Agent</title>
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #05070a;
            --card-bg: #0d1117;
            --navbar-bg: rgba(10, 14, 26, 0.95);
            --primary: #3b82f6;
            --primary-gradient: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #10b981 100%);
            --secondary: #8b5cf6;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #1e293b;
            --terminal-bg: #080d1a;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }

        body {
            background-color: var(--bg);
            color: var(--text-main);
            line-height: 1.6;
            overflow-x: hidden;
        }

        /* --- Animations --- */
        @keyframes pulse-green {
            0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1.1); box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        @keyframes pulse-red {
            0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
            70% { transform: scale(1.1); box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }

        @keyframes shake {
            0% { transform: translateX(0); }
            25% { transform: translateX(-5px); }
            50% { transform: translateX(5px); }
            75% { transform: translateX(-5px); }
            100% { transform: translateX(0); }
        }

        @keyframes slideInLeft {
            from { transform: translateX(-20px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        @keyframes fadeInUp {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        @keyframes glow-pulse {
            0% { border-color: var(--border); box-shadow: 0 0 0 rgba(59, 130, 246, 0); }
            50% { border-color: var(--primary); box-shadow: 0 0 20px rgba(59, 130, 246, 0.3); }
            100% { border-color: var(--border); box-shadow: 0 0 0 rgba(59, 130, 246, 0); }
        }

        /* --- Navbar --- */
        nav {
            position: sticky;
            top: 0;
            height: 64px;
            background: var(--navbar-bg);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 40px;
            z-index: 1000;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 1.5rem;
            font-weight: 700;
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .logo i {
            -webkit-text-fill-color: var(--primary);
        }

        .nav-links {
            display: flex;
            gap: 32px;
        }

        .nav-links a {
            color: var(--text-muted);
            text-decoration: none;
            font-weight: 500;
            transition: color 0.3s;
        }

        .nav-links a:hover {
            color: var(--text-main);
        }

        .nav-right {
            display: flex;
            align-items: center;
            gap: 20px;
        }

        /* --- Hero Section --- */
        .hero {
            padding: 80px 40px;
            text-align: center;
            position: relative;
            background-image: radial-gradient(rgba(59, 130, 246, 0.05) 1px, transparent 1px);
            background-size: 40px 40px;
        }

        .hero::before, .hero::after {
            content: '';
            position: absolute;
            width: 300px;
            height: 300px;
            border-radius: 50%;
            filter: blur(120px);
            z-index: -1;
            opacity: 0.15;
        }

        .hero::before { top: 10%; left: 10%; background: var(--primary); }
        .hero::after { bottom: 10%; right: 10%; background: var(--secondary); }

        .hero-badge {
            display: inline-block;
            background: rgba(255, 255, 255, 0.05);
            padding: 8px 16px;
            border-radius: 30px;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 24px;
        }

        .hero h1 {
            font-size: 4rem;
            font-weight: 800;
            margin-bottom: 16px;
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            filter: drop-shadow(0 0 30px rgba(59, 130, 246, 0.3));
        }

        .hero p {
            font-size: 1.25rem;
            color: var(--text-muted);
            max-width: 700px;
            margin: 0 auto 32px;
        }

        .hero-btns {
            display: flex;
            justify-content: center;
            gap: 16px;
        }

        .btn {
            padding: 12px 28px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 10px;
        }

        .btn-primary {
            background-color: var(--primary);
            color: white;
            border: none;
        }

        .btn-primary:hover {
            background-color: #2563eb;
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(37, 99, 235, 0.4);
        }

        .btn-outline {
            background: transparent;
            color: var(--primary);
            border: 1px solid var(--primary);
        }

        .btn-outline:hover {
            background: rgba(59, 130, 246, 0.1);
        }

        /* --- Stats Row --- */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 24px;
            padding: 0 40px 60px;
        }

        .stat-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            padding: 24px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            gap: 20px;
            transition: all 0.3s;
        }

        .stat-card:hover {
            transform: translateY(-5px);
            border-color: var(--primary);
        }

        .stat-icon {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
        }

        .stat-info h3 {
            font-size: 1.75rem;
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 4px;
        }

        .stat-info p {
            color: var(--text-muted);
            font-size: 0.85rem;
        }

        .stat-trend {
            font-size: 0.75rem;
            margin-top: 4px;
        }

        /* --- Infrastructure Status --- */
        .page-section {
            padding: 0 40px 80px;
        }

        .section-header {
            margin-bottom: 32px;
        }

        .section-header h2 {
            font-size: 2rem;
            margin-bottom: 8px;
        }

        .section-header p {
            color: var(--text-muted);
        }

        .infra-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 24px;
        }

        .server-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            padding: 24px;
            border-radius: 12px;
            transition: all 0.3s;
            position: relative;
            overflow: hidden;
        }

        .server-card.down {
            border-color: var(--danger);
            animation: shake 0.5s;
        }

        .server-card.down .server-status-dot {
            background: var(--danger);
            animation: pulse-red 2s infinite;
        }

        .server-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .server-id {
            display: flex;
            align-items: center;
            gap: 12px;
            font-weight: 700;
        }

        .server-id i {
            color: var(--primary);
            font-size: 1.2rem;
        }

        .server-status-badge {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }

        .server-status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--success);
        }

        .server-metric {
            margin-bottom: 16px;
        }

        .metric-label {
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            margin-bottom: 8px;
            color: var(--text-muted);
        }

        .progress-bg {
            height: 6px;
            background: var(--bg);
            border-radius: 3px;
            overflow: hidden;
        }

        .progress-bar {
            height: 100%;
            background: var(--primary);
            width: 0%;
            transition: width 1s;
        }

        /* --- Demo Controls & Feed --- */
        .action-container {
            display: grid;
            grid-template-columns: 1fr 1.5fr;
            gap: 32px;
            padding: 0 40px 80px;
        }

        .trigger-list {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .trigger-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            padding: 20px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            gap: 20px;
            transition: all 0.3s;
        }

        .trigger-info { flex: 1; }
        .trigger-info h4 { margin-bottom: 4px; }
        .trigger-info p { font-size: 0.85rem; color: var(--text-muted); }

        .btn-trigger {
            background: transparent;
            color: var(--danger);
            border: 1px solid var(--danger);
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn-trigger:hover {
            background: var(--danger);
            color: white;
        }

        .btn-trigger:disabled {
            border-color: var(--warning);
            color: var(--warning);
            cursor: not-allowed;
            opacity: 0.7;
        }

        /* --- Agent Feed --- */
        .feed-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            display: flex;
            flex-direction: column;
            height: 500px;
            overflow: hidden;
        }

        .feed-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .feed-status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.85rem;
            color: var(--text-muted);
        }

        .feed-body {
            flex: 1;
            background: var(--terminal-bg);
            padding: 20px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            scroll-behavior: smooth;
        }

        .feed-entry {
            margin-bottom: 8px;
            animation: slideInLeft 0.3s ease-out;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            padding-bottom: 4px;
        }

        .ts { color: #565f89; margin-right: 8px; }
        .success-text { color: var(--success); font-weight: bold; }
        .failure-text { color: var(--danger); font-weight: bold; }
        .info-text { color: #bb9af7; }
        .wait-text { color: var(--warning); font-weight: bold; animation: pulse 1s infinite; }

        .confirm-panel {
            padding: 16px 20px;
            background: rgba(245, 158, 11, 0.1);
            border-top: 1px solid var(--warning);
            display: none;
        }

        .confirm-panel.active { display: block; }

        .confirm-btns {
            display: flex;
            gap: 12px;
            margin-top: 12px;
        }

        /* --- Stats/Tech/History --- */
        .history-table {
            width: 100%;
            border-collapse: collapse;
            background: var(--card-bg);
            border-radius: 12px;
            overflow: hidden;
            margin-top: 20px;
        }

        .history-table th, .history-table td {
            padding: 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }

        .history-table th {
            background: rgba(255, 255, 255, 0.02);
            color: var(--text-muted);
            font-weight: 600;
            font-size: 0.85rem;
        }

        .badge {
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }

        .badge-success { background: rgba(16, 185, 129, 0.1); color: var(--success); }
        .badge-running { background: rgba(59, 130, 246, 0.1); color: var(--primary); }
        .badge-fail { background: rgba(239, 68, 68, 0.1); color: var(--danger); }

        /* --- Toasts --- */
        #toast-container {
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 10000;
        }

        .toast {
            background: var(--card-bg);
            border-left: 4px solid var(--primary);
            padding: 16px 24px;
            border-radius: 8px;
            margin-top: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            gap: 12px;
            animation: slideInRight 0.3s ease-out;
        }

        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        /* --- Utilities --- */
        .mb-10 { margin-bottom: 40px; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }

        footer {
            padding: 60px 40px;
            background: #020305;
            border-top: 1px solid var(--border);
            text-align: center;
            color: var(--text-muted);
        }

        .offline-banner {
            background: var(--warning);
            color: black;
            text-align: center;
            padding: 4px;
            font-weight: 700;
            font-size: 0.8rem;
            display: none;
        }

        .runbook-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            padding: 24px;
            border-radius: 12px;
            transition: all 0.3s;
            cursor: pointer;
        }

        .runbook-card:hover {
            border-color: var(--primary);
            transform: translateY(-5px);
        }

        .runbook-card h4 {
            margin-bottom: 8px;
            color: var(--primary);
        }

        .runbook-content-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 10001;
        }

        .modal-body {
            background: var(--card-bg);
            width: 80%;
            max-width: 800px;
            max-height: 80vh;
            border-radius: 12px;
            padding: 40px;
            overflow-y: auto;
            position: relative;
            border: 1px solid var(--border);
        }

        .close-modal {
            position: absolute;
            top: 20px;
            right: 20px;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--text-muted);
        }

    </style>
</head>
<body>

<div id="offline-banner" class="offline-banner">⚠️ DEMO MODE — Backend not connected. Showing sample data.</div>

<nav>
    <div class="logo">
        <i class="fas fa-robot"></i> RUNBOOK AGENT
    </div>
    <div class="nav-links">
        <a href="#dashboard">Dashboard</a>
        <a href="#runbooks">Runbooks</a>
        <a href="#history">History</a>
        <a href="#about">About</a>
    </div>
    <div class="nav-right">
        <div class="status-badge" style="display: flex; align-items: center; gap: 8px; background: rgba(16, 185, 129, 0.1); color: var(--success); padding: 6px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600;">
            <div class="status-dot" style="width: 8px; height: 8px; background: var(--success); border-radius: 50%; animation: pulse-green 2s infinite;"></div>
            Agent Online
        </div>
    </div>
</nav>

<section class="hero">
    <h1>RUNBOOK AGENT</h1>
    <p>Autonomous IT Operations Agent powered by Ollama LLaMA3. <br>Resolving complex infrastructure failures in real-time with zero manual effort.</p>
    <div class="hero-btns">
        <a href="#dashboard" class="btn btn-primary"><i class="fas fa-rocket"></i> View Live Demo</a>
        <a href="#runbooks" class="btn btn-outline"><i class="fas fa-clipboard-list"></i> View Runbooks</a>
    </div>
</section>

<!-- Stats Row -->
<div class="stats-grid">
    <div class="stat-card" style="border-left: 4px solid var(--success);">
        <div class="stat-icon" style="background: rgba(16, 185, 129, 0.1); color: var(--success);">
            <i class="fas fa-shield-check"></i>
        </div>
        <div class="stat-info">
            <h3 id="stat-resolved">0</h3>
            <p>Incidents Resolved</p>
            <div class="stat-trend success">+0 today</div>
        </div>
    </div>
    <div class="stat-card" style="border-left: 4px solid var(--primary);">
        <div class="stat-icon" style="background: rgba(59, 130, 246, 0.1); color: var(--primary);">
            <i class="fas fa-list-check"></i>
        </div>
        <div class="stat-info">
            <h3 id="stat-steps">0</h3>
            <p>Steps Executed</p>
            <div class="stat-trend" style="color: var(--primary);">Real-time tracking</div>
        </div>
    </div>
    <div class="stat-card" style="border-left: 4px solid var(--warning);">
        <div class="stat-icon" style="background: rgba(245, 158, 11, 0.1); color: var(--warning);">
            <i class="fas fa-bell"></i>
        </div>
        <div class="stat-info">
            <h3 id="stat-discord">0</h3>
            <p>Alerts Sent</p>
            <div class="stat-trend" style="color: var(--warning);">Discord Live</div>
        </div>
    </div>
    <div class="stat-card" style="border-left: 4px solid var(--secondary);">
        <div class="stat-icon" style="background: rgba(139, 92, 246, 0.1); color: var(--secondary);">
            <i class="fas fa-clock"></i>
        </div>
        <div class="stat-info">
            <h3 id="stat-avg">~4m</h3>
            <p>Avg Resolution</p>
            <div class="stat-trend" style="color: var(--secondary);">vs 45 min manual</div>
        </div>
    </div>
</div>

<!-- Infra Status -->
<section id="dashboard" class="page-section">
    <div class="section-header">
        <h2><i class="fas fa-server"></i> Infrastructure Status</h2>
        <p>Real-time machine health monitoring</p>
    </div>
    <div class="infra-grid">
        <!-- Nginx -->
        <div class="server-card" id="card-nginx">
            <div class="server-top">
                <div class="server-id"><i class="fas fa-globe"></i> Web Server (Nginx)</div>
                <div class="server-status-badge">
                    <div class="server-status-dot"></div>
                    <span id="status-nginx">HEALTHY</span>
                </div>
            </div>
            <div class="server-metric">
                <div class="metric-label">
                    <span>Availability</span>
                    <span id="metric-nginx">99.9%</span>
                </div>
                <div class="progress-bg"><div id="progress-nginx" class="progress-bar" style="width: 100%; background: var(--success);"></div></div>
            </div>
            <div class="metric-label" style="font-size: 0.7rem;">Last checked: 2s ago</div>
        </div>
        <!-- Database -->
        <div class="server-card" id="card-database">
            <div class="server-top">
                <div class="server-id"><i class="fas fa-database"></i> Database Server</div>
                <div class="server-status-badge">
                    <div class="server-status-dot"></div>
                    <span id="status-database">HEALTHY</span>
                </div>
            </div>
            <div class="server-metric">
                <div class="metric-label">
                    <span>Connections</span>
                    <span id="metric-database">42</span>
                </div>
                <div class="progress-bg"><div id="progress-database" class="progress-bar" style="width: 42%; background: var(--success);"></div></div>
            </div>
            <div class="metric-label" style="font-size: 0.7rem;">Last checked: 2s ago</div>
        </div>
        <!-- CPU -->
        <div class="server-card" id="card-cpu">
            <div class="server-top">
                <div class="server-id"><i class="fas fa-microchip"></i> System CPU</div>
                <div class="server-status-badge">
                    <div class="server-status-dot"></div>
                    <span id="status-cpu">NORMAL</span>
                </div>
            </div>
            <div class="server-metric">
                <div class="metric-label">
                    <span>Current Load</span>
                    <span id="metric-cpu">23%</span>
                </div>
                <div class="progress-bg"><div id="progress-cpu" class="progress-bar" style="width: 23%; background: var(--success);"></div></div>
            </div>
            <div class="metric-label" style="font-size: 0.7rem;">Last checked: 2s ago</div>
        </div>
        <!-- Disk -->
        <div class="server-card" id="card-disk">
            <div class="server-top">
                <div class="server-id"><i class="fas fa-hard-drive"></i> Disk Usage</div>
                <div class="server-status-badge">
                    <div class="server-status-dot"></div>
                    <span id="status-disk">NORMAL</span>
                </div>
            </div>
            <div class="server-metric">
                <div class="metric-label">
                    <span>Storage Used</span>
                    <span id="metric-disk">67%</span>
                </div>
                <div class="progress-bg"><div id="progress-disk" class="progress-bar" style="width: 67%; background: var(--success);"></div></div>
            </div>
            <div class="metric-label" style="font-size: 0.7rem;">Last checked: 2s ago</div>
        </div>
    </div>
</section>

<!-- Main Agent View -->
<div class="action-container">
    <!-- Left: Controls -->
    <div class="trigger-list">
        <div class="section-header">
            <h2><i class="fas fa-bolt"></i> Demo Controls</h2>
            <p>Trigger failures to activate the agent</p>
        </div>
        <div class="trigger-card" id="trigger-nginx">
            <i class="fas fa-globe-africa fa-2x" style="color: var(--danger);"></i>
            <div class="trigger-info">
                <h4>Nginx Server Down</h4>
                <p>Web server stopped responding (CRITICAL)</p>
            </div>
            <button class="btn-trigger" onclick="triggerFailure('nginx_down')">🔴 TRIGGER</button>
        </div>
        <div class="trigger-card" id="trigger-cpu">
            <i class="fas fa-fire fa-2x" style="color: #f97316;"></i>
            <div class="trigger-info">
                <h4>High CPU Usage</h4>
                <p>CPU at 94% — performance lag (HIGH)</p>
            </div>
            <button class="btn-trigger" onclick="triggerFailure('high_cpu')">🔴 TRIGGER</button>
        </div>
        <div class="trigger-card" id="trigger-database">
            <i class="fas fa-database fa-2x" style="color: var(--danger);"></i>
            <div class="trigger-info">
                <h4>Database Failure</h4>
                <p>PostgreSQL connection refused (CRITICAL)</p>
            </div>
            <button class="btn-trigger" onclick="triggerFailure('database_failure')">🔴 TRIGGER</button>
        </div>
        <div class="trigger-card" id="trigger-disk">
            <i class="fas fa-hdd fa-2x" style="color: #f97316;"></i>
            <div class="trigger-info">
                <h4>Disk Space Critical</h4>
                <p>Disk at 91% — space exhausted (HIGH)</p>
            </div>
            <button class="btn-trigger" onclick="triggerFailure('disk_full')">🔴 TRIGGER</button>
        </div>
    </div>

    <!-- Right: Agent Feed -->
    <div class="feed-card">
        <div class="feed-header">
            <div class="feed-status" id="agent-status-bar">
                <div class="status-dot" style="background: var(--text-muted); animation: none; width: 8px; height: 8px; border-radius: 50%;"></div>
                 Agent Idle — Waiting for incidents
            </div>
            <i class="fas fa-terminal"></i>
        </div>
        <div class="feed-body" id="agent-feed">
            <div class="feed-entry"><span class="ts">[00:00:00]</span> ⚡ SYSTEM INITIALIZED. MCP TOOLS LOADED.</div>
            <div class="feed-entry"><span class="ts">[00:00:00]</span> 🤖 RUNBOOK AGENT v1.0.0 Online.</div>
        </div>
        <div class="confirm-panel" id="confirm-panel">
            <div style="font-weight: 700; color: var(--warning);"><i class="fas fa-triangle-exclamation"></i> HUMAN CONFIRMATION REQUIRED</div>
            <div id="confirm-msg" style="font-size: 0.85rem; margin-top: 5px; color: var(--text-main);"></div>
            <div class="confirm-btns">
                <button class="btn btn-primary" style="background: var(--success); font-size: 0.8rem; padding: 6px 16px;" onclick="confirmStep()">✅ Confirm & Execute</button>
                <button class="btn btn-outline" style="border-color: var(--danger); color: var(--danger); font-size: 0.8rem; padding: 6px 16px;" onclick="skipStep()">❌ Skip</button>
            </div>
        </div>
    </div>
</div>

<!-- Runbooks Section -->
<section id="runbooks" class="page-section">
    <div class="section-header">
        <h2><i class="fas fa-clipboard-list"></i> Operational Runbooks</h2>
        <p>Pre-defined resolution strategies for common failures</p>
    </div>
    <div class="infra-grid">
        <div class="runbook-card" onclick="viewRunbook('nginx_down.md')">
            <i class="fas fa-globe fa-2x mb-2" style="color: var(--primary);"></i>
            <h4>Nginx Server Down</h4>
            <p>6 steps to restore web availability</p>
        </div>
        <div class="runbook-card" onclick="viewRunbook('high_cpu.md')">
            <i class="fas fa-microchip fa-2x mb-2" style="color: var(--secondary);"></i>
            <h4>High CPU Usage</h4>
            <p>5 steps to mitigate performance lag</p>
        </div>
        <div class="runbook-card" onclick="viewRunbook('database_failure.md')">
            <i class="fas fa-database fa-2x mb-2" style="color: var(--danger);"></i>
            <h4>Database Failure</h4>
            <p>6 steps to restore DB connectivity</p>
        </div>
        <div class="runbook-card" onclick="viewRunbook('disk_full.md')">
            <i class="fas fa-hard-drive fa-2x mb-2" style="color: var(--warning);"></i>
            <h4>Disk Space Critical</h4>
            <p>6 steps to free up storage space</p>
        </div>
    </div>
</section>

<!-- Runbook Modal -->
<div id="runbook-modal" class="runbook-content-modal" onclick="closeModal()">
    <div class="modal-body" onclick="event.stopPropagation()">
        <span class="close-modal" onclick="closeModal()">&times;</span>
        <h2 id="modal-title" style="margin-bottom: 20px; color: var(--primary);"></h2>
        <pre id="modal-content" style="white-space: pre-wrap; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: var(--text-muted);"></pre>
    </div>
</div>

<!-- History Table -->
<section id="history" class="page-section">
    <div class="section-header" style="display: flex; justify-content: space-between; align-items: flex-end;">
        <div>
            <h2><i class="fas fa-history"></i> Execution History</h2>
            <p>Recent incident resolutions and agent performance</p>
        </div>
        <button class="btn btn-outline" style="font-size: 0.8rem;" onclick="exportCSV()"><i class="fas fa-download"></i> Export CSV</button>
    </div>
    <table class="history-table">
        <thead>
            <tr>
                <th>ID</th>
                <th>Time Started</th>
                <th>Failure Type</th>
                <th>Runbook</th>
                <th>Steps</th>
                <th>Status</th>
                <th>Discord</th>
            </tr>
        </thead>
        <tbody id="history-body">
            <!-- Dynamic rows -->
        </tbody>
    </table>
</section>

<!-- Tech Stack -->
<section id="about" class="page-section">
    <div class="section-header text-center">
        <h2>🛠️ Technology Stack</h2>
        <p>Built for the Modern DevOps Enterprise</p>
    </div>
    <div class="infra-grid">
        <div class="stat-card" style="padding: 15px; border: 1px solid var(--border);">
            <i class="fab fa-python fa-2x" style="color: #3776ab;"></i>
            <div><div style="font-weight: 700;">Python 3.11</div><p style="font-size: 0.7rem;">Backend Core</p></div>
        </div>
        <div class="stat-card" style="padding: 15px; border: 1px solid var(--border);">
            <i class="fas fa-bolt fa-2x" style="color: #009688;"></i>
            <div><div style="font-weight: 700;">FastAPI</div><p style="font-size: 0.7rem;">REST Gateway</p></div>
        </div>
        <div class="stat-card" style="padding: 15px; border: 1px solid var(--border);">
            <i class="fas fa-brain fa-2x" style="color: #facc15;"></i>
            <div><div style="font-weight: 700;">Ollama Llama3</div><p style="font-size: 0.7rem;">Local Brain</p></div>
        </div>
        <div class="stat-card" style="padding: 15px; border: 1px solid var(--border);">
            <i class="fas fa-code-branch fa-2x" style="color: var(--secondary);"></i>
            <div><div style="font-weight: 700;">MCP Protocol</div><p style="font-size: 0.7rem;">Execution Layer</p></div>
        </div>
    </div>
</section>

<div id="toast-container"></div>

<footer>
    <div class="logo" style="justify-content: center; margin-bottom: 0;">
        <i class="fas fa-robot"></i> RUNBOOK AGENT
    </div>
</footer>

<script>
    const API_BASE = window.location.origin;
    const POLL_INTERVAL_STATUS = 2000;
    const POLL_INTERVAL_FEED = 1000;
    
    let lastLogCount = 0;
    let isOffline = false;
    let historyData = [];

    // --- Core Functions ---

    async function fetchStatus() {
        try {
            const res = await fetch(`${API_BASE}/api/status`);
            const data = await res.json();
            isOffline = false;
            document.getElementById('offline-banner').style.display = 'none';
            updateUIStatus(data);
        } catch (e) {
            console.warn("Backend offline");
            isOffline = true;
            document.getElementById('offline-banner').style.display = 'block';
        }
    }

    function updateUIStatus(data) {
        // Server Cards
        updateServerCard('nginx', data.nginx, data.nginx === 'healthy' ? '99.9%' : 'OFFLINE');
        updateServerCard('database', data.database, data.database === 'healthy' ? '42 conn' : 'REJECTED');
        updateServerCard('cpu', data.cpu, data.cpu === 'normal' ? '23%' : '94%');
        updateServerCard('disk', data.disk, data.disk === 'normal' ? '67%' : '91%');

        // Agent Button States
        const btns = document.querySelectorAll('.btn-trigger');
        btns.forEach(b => {
             if (data.agent_busy) b.disabled = true;
             else b.disabled = false;
        });

        // Global Agent Status Bar
        const statusBar = document.getElementById('agent-status-bar');
        if (data.agent_busy) {
            statusBar.innerHTML = `<div class="status-dot" style="background: var(--primary); animation: pulse-green 1s infinite;"></div> Agent Active — Resolving Incident...`;
        } else {
            statusBar.innerHTML = `<div class="status-dot" style="background: var(--text-muted);"></div> Agent Idle — Waiting for incidents`;
        }
    }

    function updateServerCard(id, status, metric) {
        const card = document.getElementById(`card-${id}`);
        const statusSpan = document.getElementById(`status-${id}`);
        const metricSpan = document.getElementById(`metric-${id}`);
        const progress = document.getElementById(`progress-${id}`);

        if (status === 'down' || status === 'critical') {
            card.classList.add('down');
            statusSpan.innerText = status.toUpperCase();
            metricSpan.innerText = metric;
            progress.style.width = '100%';
            progress.style.background = 'var(--danger)';
        } else {
            card.classList.remove('down');
            statusSpan.innerText = 'HEALTHY';
            metricSpan.innerText = metric;
            progress.style.background = 'var(--success)';
            if (id === 'cpu') progress.style.width = '23%';
            else if (id === 'disk') progress.style.width = '67%';
            else progress.style.width = '100%';
        }
    }

    async function fetchAgentFeed() {
        if (isOffline) return;
        try {
            const res = await fetch(`${API_BASE}/api/agent/feed`);
            const data = await res.json();
            
            // If the feed was cleared on the backend for a new runbook
            if (data.length < lastLogCount) {
                document.getElementById('agent-feed').innerHTML = '';
                lastLogCount = 0;
            }

            if (data.length > lastLogCount) {
                for (let i = lastLogCount; i < data.length; i++) {
                    addFeedEntry(data[i]);
                }
                lastLogCount = data.length;
            }
        } catch (e) {}
    }

    function addFeedEntry(entry) {
        const feed = document.getElementById('agent-feed');
        const div = document.createElement('div');
        div.className = 'feed-entry';
        
        let colorClass = 'info-text';
        if (entry.status.includes('FAILURE') || entry.status.includes('FAILED')) colorClass = 'failure-text';
        if (entry.status.includes('RESOLVED') || entry.status.includes('SUCCESS')) colorClass = 'success-text';
        if (entry.status.includes('CONFIRMATION')) colorClass = 'wait-text';

        div.innerHTML = `<span class="ts">[${entry.timestamp}]</span> <span class="${colorClass}">${entry.status}</span> — ${entry.message}`;
        feed.appendChild(div);
        feed.scrollTop = feed.scrollHeight;

        // Handle Confirmation Panel
        const panel = document.getElementById('confirm-panel');
        if (entry.needs_confirm) {
            panel.classList.add('active');
            document.getElementById('confirm-msg').innerText = `${entry.message}\nRisk: ${entry.risk || "Restarting core service"}`;
            if (lastLogCount > 0) showToast("⚠️ Intervention Required!", "warning");
        } else if (entry.message.includes('Human skipped') || entry.message.includes('Human confirmed') || entry.status.includes('RESOLVED') || entry.status.includes('ERROR')) {
            panel.classList.remove('active');
        }
    }

    async function triggerFailure(type) {
        showToast("🚨 Triggering incident...", "info");
        try {
            await fetch(`${API_BASE}/api/trigger/${type}`, { method: 'POST' });
            fetchStatus();
        } catch (e) {
            showToast("Failed to connect to backend", "error");
        }
    }

    async function confirmStep() {
        document.getElementById('confirm-panel').classList.remove('active');
        await fetch(`${API_BASE}/api/confirm`, { method: 'POST' });
        showToast("✅ Confirmed. Agent continuing...", "success");
    }

    async function skipStep() {
        document.getElementById('confirm-panel').classList.remove('active');
        await fetch(`${API_BASE}/api/skip`, { method: 'POST' });
        showToast("⏭️ Step skipped.", "info");
    }

    async function viewRunbook(name) {
        try {
            const res = await fetch(`${API_BASE}/api/runbooks/${name}`);
            const data = await res.json();
            document.getElementById('modal-title').innerText = `Runbook: ${name}`;
            document.getElementById('modal-content').innerText = data.content;
            document.getElementById('runbook-modal').style.display = 'flex';
        } catch (e) {
            showToast("Failed to fetch runbook", "error");
        }
    }

    function closeModal() {
        document.getElementById('runbook-modal').style.display = 'none';
    }

    async function fetchHistory() {
        if (isOffline) return;
        try {
            const res = await fetch(`${API_BASE}/api/history`);
            const data = await res.json();
            historyData = data;
            const body = document.getElementById('history-body');
            body.innerHTML = '';
            
            data.forEach((row, i) => {
                const tr = document.createElement('tr');
                const statusBadge = row.status === 'completed' ? 'badge-success' : (row.status === 'running' ? 'badge-running' : 'badge-fail');
                tr.innerHTML = `
                    <td>#${row.id}</td>
                    <td>${new Date(row.started_at).toLocaleTimeString()}</td>
                    <td>${row.failure_type.replace('_',' ').toUpperCase()}</td>
                    <td>${row.runbook_name}</td>
                    <td>${row.completed_steps}/${row.total_steps}</td>
                    <td><span class="badge ${statusBadge}">${row.status}</span></td>
                    <td><i class="fas fa-bell" style="color: var(--warning);"></i> Sent</td>
                `;
                body.appendChild(tr);
            });

            // Update stats from another endpoint
            const statRes = await fetch(`${API_BASE}/api/stats`);
            const stats = await statRes.json();
            document.getElementById('stat-resolved').innerText = stats.total_runs;
            document.getElementById('stat-steps').innerText = stats.steps_today;
            document.getElementById('stat-discord').innerText = stats.discord_sent;
            document.getElementById('stat-avg').innerText = `~${stats.avg_resolution_mins} min`;

        } catch (e) {}
    }

    function exportCSV() {
        if (!historyData || historyData.length === 0) {
            showToast("No history data to export", "warning");
            return;
        }
        
        const headers = ["ID", "Time Started", "Completed At", "Failure Type", "Runbook Name", "Completed Steps", "Total Steps", "Status"];
        const rows = historyData.map(row => [
            row.id,
            row.started_at,
            row.completed_at || "N/A",
            row.failure_type.replace('_',' ').toUpperCase(),
            row.runbook_name,
            row.completed_steps,
            row.total_steps,
            row.status
        ]);
        
        const csvContent = [
            headers.join(","),
            ...rows.map(e => e.map(val => `"${String(val).replace(/"/g, '""')}"`).join(","))
        ].join("\n");
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `runbook_agent_history_${new Date().toISOString().slice(0,10)}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showToast("📊 CSV exported successfully!", "success");
    }

    function showToast(message, type) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = 'toast';
        const colors = { success: 'var(--success)', error: 'var(--danger)', warning: 'var(--warning)', info: 'var(--primary)' };
        const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', warning: 'fa-triangle-exclamation', info: 'fa-info-circle' };
        
        toast.style.borderLeftColor = colors[type];
        toast.innerHTML = `<i class="fas ${icons[type]}" style="color: ${colors[type]}"></i> ${message}`;
        
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // --- Initiation ---
    setInterval(fetchStatus, POLL_INTERVAL_STATUS);
    setInterval(fetchAgentFeed, POLL_INTERVAL_FEED);
    setInterval(fetchHistory, 5000);

    window.onload = () => {
        fetchStatus();
        fetchHistory();
        showToast("🤖 RUNBOOK AGENT Dashboard Connected", "success");
    };

</script>
</body>
</html>

```

### File: `runbooks/high_cpu.md`
```markdown
# Runbook: High CPU Usage (>95%)
## Failure Type: high_cpu
## Severity: High
## Estimated Resolution: 5 minutes
## Description: Resolves performance degradation caused by runaway processes consuming system CPU.

## Steps

### Step 1
- **Type:** SAFE
- **Description:** Check current CPU usage breakdown
- **Command:** `top -bn1 | grep 'Cpu'`
- **Expected Output:** CPU idle percentage should be above 10%

### Step 2
- **Type:** SAFE
- **Description:** Find top CPU consuming processes
- **Command:** `ps aux --sort=-%cpu | head -10`
- **Expected Output:** Identify the offending process ID

### Step 3
- **Type:** SAFE
- **Description:** Check system load average
- **Command:** `uptime`
- **Expected Output:** Load average should be within CPUs count

### Step 4
- **Type:** RISKY
- **Description:** Kill the top consuming process to restore stability
- **Command:** `systemctl restart nginx`
- **Expected Output:** Success message
- **Risk:** Terminating a process may result in data loss for that specific application.

### Step 5
- **Type:** SAFE
- **Description:** Verify CPU usage has normalized
- **Command:** `top -bn1 | grep 'Cpu'`
- **Expected Output:** Usage below 50%

### Step 6
- **Type:** SAFE
- **Description:** Check filesystem impact
- **Command:** `df -h`
- **Expected Output:** Normal disk I/O

```

### File: `runbooks/database_failure.md`
```markdown
# Runbook: Database Connection Failed
## Failure Type: database_failure
## Severity: Critical
## Estimated Resolution: 6 minutes
## Description: Restores PostgreSQL database availability when connections are refused.

## Steps

### Step 1
- **Type:** SAFE
- **Description:** Check database process status
- **Command:** `systemctl status postgresql`
- **Expected Output:** Process should be active (running)

### Step 2
- **Type:** SAFE
- **Description:** Check database port 5432 status
- **Command:** `pg_isready -h localhost`
- **Expected Output:** Accepting connections

### Step 3
- **Type:** SAFE
- **Description:** Check database error logs
- **Command:** `tail -n 20 /var/log/postgresql/postgresql-15-main.log`
- **Expected Output:** No 'fatal' or 'panic' messages

### Step 4
- **Type:** SAFE
- **Description:** Test database connectivity
- **Command:** `uptime`
- **Expected Output:** System healthy

### Step 5
- **Type:** RISKY
- **Description:** Restart database service to clear locked sessions
- **Command:** `systemctl restart postgresql`
- **Expected Output:** Success message
- **Risk:** Existing database connections will be dropped, and pending transactions may roll back.

### Step 6
- **Type:** SAFE
- **Description:** Verify connections restored after restart
- **Command:** `pg_isready -h localhost`
- **Expected Output:** Accepting connections

```

### File: `runbooks/disk_full.md`
```markdown
# Runbook: Disk Space Critical (>90%)
## Failure Type: disk_full
## Severity: High
## Estimated Resolution: 5 minutes
## Description: Frees up space on the primary partition to prevent system lockup.

## Steps

### Step 1
- **Type:** SAFE
- **Description:** Check current disk usage
- **Command:** `df -h`
- **Expected Output:** Use% should be below 90%

### Step 2
- **Type:** SAFE
- **Description:** Find largest directories in /var/log
- **Command:** `du -sh /var/log/*`
- **Expected Output:** List of large log folders

### Step 3
- **Type:** SAFE
- **Description:** Check specific nginx log file sizes
- **Command:** `ls -lh /var/log/nginx`
- **Expected Output:** Identify bloated access.log files

### Step 4
- **Type:** RISKY
- **Description:** Archive and compress old logs to free space
- **Command:** `tar -czf /backup/logs_$(date +%F).tar.gz /var/log/nginx/*.log`
- **Expected Output:** Archive created
- **Risk:** Log rotation/cleanup might make troubleshooting recent history more difficult.

### Step 5
- **Type:** SAFE
- **Description:** Verify disk space freed
- **Command:** `df -h`
- **Expected Output:** Use% below 80%

### Step 6
- **Type:** SAFE
- **Description:** Final check of filesystem health
- **Command:** `df -h`
- **Expected Output:** System stable

```

### File: `runbooks/nginx_down.md`
```markdown
# Runbook: Nginx Server Down
## Failure Type: nginx_down
## Severity: Critical
## Estimated Resolution: 4 minutes
## Description: This runbook handles cases where the Nginx web server is inactive or failing to bind to ports.

## Steps

### Step 1
- **Type:** SAFE
- **Description:** Check nginx process status
- **Command:** `systemctl status nginx`
- **Expected Output:** Process should be active (running)

### Step 2
- **Type:** SAFE
- **Description:** Check nginx error logs for binding or configuration errors
- **Command:** `tail -n 20 /var/log/nginx/error.log`
- **Expected Output:** No critical errors about port binding

### Step 3
- **Type:** SAFE
- **Description:** Check if port 80 is available or occupied
- **Command:** `curl -I http://localhost`
- **Expected Output:** HTTP 200 OK

### Step 4
- **Type:** RISKY
- **Description:** Restart nginx service to restore connectivity
- **Command:** `systemctl restart nginx`
- **Expected Output:** Status OK
- **Risk:** This will briefly interrupt any active web traffic during the restart.

### Step 5
- **Type:** SAFE
- **Description:** Verify nginx responding after restart
- **Command:** `systemctl status nginx`
- **Expected Output:** Process is active (running)

### Step 6
- **Type:** SAFE
- **Description:** Final uptime check
- **Command:** `uptime`
- **Expected Output:** System stable

```

