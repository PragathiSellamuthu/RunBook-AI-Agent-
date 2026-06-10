# 🤖 RUNBOOK AGENT — Autonomous Infrastructure Resolution Agent

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/Ollama-Llama3-orange?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com)
[![SQLite](https://img.shields.io/badge/SQLite-Database-blue?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Discord](https://img.shields.io/badge/Discord-Alerts-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com)

[![Watch the Demo Explanation](https://img.shields.io/badge/Watch-Demo%20Video-red?style=for-the-badge&logo=googledrive)](https://drive.google.com/drive/folders/1BX5-v6IP2rZ9mvcntu_ihYKvY_68ao-P?usp=sharing)

**RUNBOOK AGENT** is a real-time, autonomous AI operations (AIOps) agent designed to detect, diagnose, and resolve critical cloud and system infrastructure failures. It bridges the gap between high-level reasoning and physical system execution using a secure Model Context Protocol (MCP) execution design and local LLM evaluation.

> [!NOTE]
> This system is built for SREs and Devops engineers. It automates standard operating procedures (runbooks) while maintaining a strict security envelope and Human-in-the-Loop (HITL) authorization protocols.

---

## ✨ Key Features

- **🔄 Autonomous Execution Loop**: Parses markdown-formatted operational runbooks and executes diagnostic/remediative steps sequentially.
- **🛡️ MCP Sandboxed Execution Layer**: Uses a custom [ShellExecutorMCPTool](file:///e:/run/backend/mcp_tool.py#L4) with a strict command allowlist to simulate terminal inputs and return realistic Linux execution output.
- **🧠 Local AI Step Classification**: Integrates with a local Llama3 instance running on Ollama to decide if a remediation command is `SAFE` (execute immediately) or `RISKY` (restart/terminate services).
- **👥 Human-in-the-Loop Safeguards**: Automatically pauses execution on risky commands, alerts the SRE team, and requests confirmation in the dashboard before proceeding.
- **📊 Real-time Operations Dashboard**: Single-page dark mode UI reporting live feed activity, status gauges, execution analytics, and incident histories.
- **🔔 Live Discord Notifications**: Instantly pushes webhook alerts for incident detection, authorization alerts, step compliance metrics, and resolutions.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11, [FastAPI](file:///e:/run/backend/main.py) (Asynchronous router), [Uvicorn](file:///e:/run/requirements.txt) (ASGI server)
- **Database**: [SQLite](file:///e:/run/backend/database.py) (Persistent historical logs)
- **AI Brain**: Ollama Llama3 (Local LLM endpoint)
- **Frontend**: [index.html](file:///e:/run/frontend/index.html) (HTML5, Vanilla CSS, JS Fetch API)
- **Alerting**: Discord Webhooks integration

---

## 📂 Project Workspace Map

Click on any file to view its implementation details:

- **[`backend/`](file:///e:/run/backend/)**: Core application logic.
  - [main.py](file:///e:/run/backend/main.py) — FastAPI routing configurations & backend entry point.
  - [agent_runner.py](file:///e:/run/backend/agent_runner.py) — Main autonomous state machine and Ollama model connector.
  - [mcp_tool.py](file:///e:/run/backend/mcp_tool.py) — Simulated Model Context Protocol tool with command security allowlist.
  - [runbook_parser.py](file:///e:/run/backend/runbook_parser.py) — Regex-based parser transforming markdown files to JSON step definitions.
  - [database.py](file:///e:/run/backend/database.py) — SQLite logging client and dashboard performance metrics calculator.
- **[`frontend/`](file:///e:/run/frontend/)**: User interfaces.
  - [index.html](file:///e:/run/frontend/index.html) — Single-page real-time administration dashboard.
- **[`runbooks/`](file:///e:/run/runbooks/)**: Operational knowledge-bases.
  - [nginx_down.md](file:///e:/run/runbooks/nginx_down.md) — Remediation steps for dead web servers.
  - [database_failure.md](file:///e:/run/runbooks/database_failure.md) — Remediation steps for database connectivity failures.
  - [high_cpu.md](file:///e:/run/runbooks/high_cpu.md) — System monitoring and resource mitigation guidelines.
  - [disk_full.md](file:///e:/run/runbooks/disk_full.md) — Disk capacity checks and log archival strategies.
- **Root configurations**:
  - [requirements.txt](file:///e:/run/requirements.txt) — Project dependencies manifest.
  - [prompts.md](file:///e:/run/prompts.md) — AI instruction sets.
  - [DOCUMENTATION.md](file:///e:/run/DOCUMENTATION.md) — System architecture manual and developer instructions.

---

## 🚀 Setup & Launch (Windows)

Follow these steps to set up and run the RUNBOOK AGENT locally:

### 1. Install Dependencies
Ensure you have Python 3.11+ installed. Execute the following in PowerShell:
```powershell
pip install -r requirements.txt
```

### 2. Configure Local AI (Ollama)
1. Download and install [Ollama](https://ollama.com/).
2. Start the service.
3. Pull the target model in your console:
   ```powershell
   ollama pull llama3
   ```

### 3. Setup Slack/Discord Notifications (Optional)
If you want to receive instant alerts:
1. Open [backend/agent_runner.py](file:///e:/run/backend/agent_runner.py#L19).
2. Replace `DISCORD_WEBHOOK` with your channel webhook URL.
   *(If left unchanged or empty, the app will bypass notifications and log metrics offline.)*

### 4. Boot the Web Server
Launch the FastAPI environment:
```powershell
python -m uvicorn backend.main:app --reload --port 8000
```

### 5. Access the Administration Dashboard
Open your web browser and navigate to:
👉 **[http://localhost:8000](https://runbook.onrender.com/)**

---

## 🎬 5-Minute Demonstration Walkthrough

Follow this script to demonstrate the RUNBOOK AGENT's features:

- **Minute 1: Introduction**
  Show the dark mode dashboard. Highlight the Infrastructure Status gauges showing **HEALTHY** metrics, and show the empty execution log feed.
- **Minute 2: Incident Detection**
  Click **"🔴 TRIGGER"** next to **Nginx Server Down**. Watch the Nginx status card flash red with a shake animation, its status shift to **DOWN**, and the Agent feed initiate.
- **Minute 3: Diagnostic Gathering**
  Watch the Agent run `systemctl status nginx` and `tail -n 20 /var/log/nginx/error.log` sequentially. The step results are added in real-time to the agent feed, and notifications are sent to Discord.
- **Minute 4: Safety Evaluation & Intervention**
  The agent reaches **Step 4: Restart nginx**. The Ollama LLM flags `systemctl restart nginx` as **RISKY**. The dashboard shows a yellow confirmation prompt, and Discord notifications request SRE review. Click **"✅ Confirm & Execute"** to authorize.
- **Minute 5: Resolution & Reporting**
  The agent completes the step, verifies service restoration, updates the status back to **HEALTHY**, and registers the execution entry in the History Table. Click **"Export CSV"** to save the log data.

---

## 📖 System Architecture & Details

For a detailed breakdown of database structures, API routes, security considerations, and troubleshooting guidelines, please refer to the core **[DOCUMENTATION.md](file:///e:/run/DOCUMENTATION.md)**.
