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

def get_execution_steps(execution_id: int):
    """Fetches all steps for a given execution."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT step_number, step_type, description, command, output, status, executed_at
    FROM steps
    WHERE execution_id = ?
    ORDER BY step_number ASC
    """, (execution_id,))
    rows = cursor.fetchall()
    
    steps = []
    for r in rows:
        steps.append({
            "step_number": r["step_number"],
            "step_type": r["step_type"],
            "description": r["description"],
            "command": r["command"],
            "output": r["output"],
            "status": r["status"],
            "executed_at": r["executed_at"]
        })
    conn.close()
    return steps

def delete_history(execution_id: int):
    """Deletes an execution and its steps."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM steps WHERE execution_id = ?", (execution_id,))
    cursor.execute("DELETE FROM executions WHERE id = ?", (execution_id,))
    conn.commit()
    conn.close()

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
