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

You can trigger and test 4 scenarios from the dashboard control buttons:
- **Nginx Server Down**: Resolves service listening on port 80.
- **High CPU Usage**: Locates and kills the runaway processor thread.
- **Database Connection Failed**: Verifies ports and restarts PostgreSQL.
- **Disk Space Critical**: Cleans up files by compressing log archives.

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
