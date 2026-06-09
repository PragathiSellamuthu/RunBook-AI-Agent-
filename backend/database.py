import sqlite3
import json
from datetime import datetime
import os

DB_PATH = "opsbot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Executions table
    cursor.execute('''
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
    ''')
    
    # Steps table
    cursor.execute('''
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
    ''')
    
    conn.commit()
    conn.close()

def start_execution(failure_type, runbook_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    started_at = datetime.now().isoformat()
    cursor.execute('''
    INSERT INTO executions (failure_type, runbook_name, started_at, total_steps, completed_steps, status)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (failure_type, runbook_name, started_at, 0, 0, 'running'))
    exec_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return exec_id

def update_execution_steps(execution_id, total_steps):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE executions SET total_steps = ? WHERE id = ?', (total_steps, execution_id))
    conn.commit()
    conn.close()

def complete_execution(execution_id, status, completed_steps):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    completed_at = datetime.now().isoformat()
    cursor.execute('''
    UPDATE executions 
    SET status = ?, completed_at = ?, completed_steps = ? 
    WHERE id = ?
    ''', (status, completed_at, completed_steps, execution_id))
    conn.commit()
    conn.close()

def log_step(execution_id, step_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    executed_at = datetime.now().isoformat()
    cursor.execute('''
    INSERT INTO steps (execution_id, step_number, step_type, description, command, output, status, needs_confirm, confirmed_at, executed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        execution_id, 
        step_data.get('step_number'),
        step_data.get('step_type'),
        step_data.get('description'),
        step_data.get('command'),
        step_data.get('output'),
        step_data.get('status'),
        1 if step_data.get('needs_confirm') else 0,
        step_data.get('confirmed_at'),
        executed_at
    ))
    conn.commit()
    conn.close()

def increment_discord_sent(execution_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE executions SET discord_sent = discord_sent + 1 WHERE id = ?', (execution_id,))
    conn.commit()
    conn.close()

def get_history(limit=20):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM executions ORDER BY started_at DESC LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    history = [dict(row) for row in rows]
    conn.close()
    return history

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM executions WHERE status = "completed"')
    total_runs = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM steps WHERE status = "SUCCESS"')
    steps_today = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(discord_sent) FROM executions')
    discord_sent = cursor.fetchone()[0] or 0
    
    # Calculate avg resolution time in minutes
    cursor.execute('''
        SELECT AVG((strftime('%s', completed_at) - strftime('%s', started_at)) / 60.0) 
        FROM executions WHERE status = "completed" AND completed_at IS NOT NULL
    ''')
    avg_res = cursor.fetchone()[0] or 0
    
    conn.close()
    return {
        "total_runs": total_runs,
        "steps_today": steps_today,
        "discord_sent": discord_sent,
        "avg_resolution_mins": round(float(avg_res), 1)
    }

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
