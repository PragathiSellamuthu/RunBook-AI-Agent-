# 📖 RUNBOOK AGENT — System Architecture & Technical Documentation

Welcome to the technical documentation for the **RUNBOOK AGENT** (Autonomous Runbook Execution Agent). This document details the internal design, component relationships, execution flows, and integration interfaces that power our autonomous operations dashboard.

---

## 🔍 System Architecture Overview

The **RUNBOOK AGENT** is structured around a central FastAPI backend web server and a multi-threaded Python agent runner loop. It bridges the gap between infrastructure diagnostics, AI decision-making (using a local Ollama Llama3 model), and system action via simulated Model Context Protocol (MCP) commands.

The entire system relies on three pillars:
1. **State Engine**: Fast polling from a client-side vanilla JavaScript dashboard to a FastAPI backend.
2. **AI Classification Layer**: Prompts sent to a local Llama3 instance to classify steps as `SAFE` (auto-execute) or `RISKY` (halt and wait for human confirmation).
3. **Execution Layer**: A sandboxed simulation engine ([ShellExecutorMCPTool](file:///e:/run/backend/mcp_tool.py#L4)) that executes Unix commands against a mock environment.

### 📐 High-Level Architecture Flow

The workflow diagram below illustrates the communication flow during incident resolution:

```mermaid
sequenceDiagram
    autonumber
    actor User as SRE / Operator
    participant UI as Frontend Dashboard
    participant API as FastAPI Backend
    participant Runner as OpsAgentRunner Loop
    participant AI as Local Ollama Llama3
    participant MCP as ShellExecutorMCPTool
    participant DB as SQLite Database
    participant Discord as Discord Webhook

    User->>UI: Triggers Incident (e.g. Nginx Down)
    UI->>API: POST /api/trigger/nginx_down
    API->>Runner: Spawn Async agent.run_runbook Task
    Runner->>Discord: Post "Incident Detected" alert
    Runner->>DB: Log execution start (Status: RUNNING)
    
    loop For Each Runbook Step
        Runner->>AI: Send classification prompt (SAFE/RISKY?)
        AI-->>Runner: Returns AUTO_EXECUTE: yes/no + Reason
        
        alt RISKY Step (needs confirmation)
            Runner->>Discord: Alert "Human Confirmation Required"
            Runner->>API: Set state to AWAITING CONFIRMATION
            API-->>UI: Poll updates & render confirmation panel
            User->>UI: Clicks "Confirm & Execute"
            UI->>API: POST /api/confirm
            API->>Runner: trigger confirm_event.set()
        end

        Runner->>MCP: execute(command)
        MCP-->>Runner: Returns simulated output & execution metrics
        Runner->>DB: log_step() details to sqlite
        Runner->>Discord: Alert Step Completed
        Runner->>API: Append feed entry to activity_feed
        UI->>API: Polls /api/agent/feed & /api/status (renders progress)
    end
    
    Runner->>DB: complete_execution(Status: COMPLETED)
    Runner->>Discord: Post "Incident Resolved" alert
    Runner->>API: Reset status to healthy / idle
    UI->>API: Refresh status & History table
```

---

## 📂 Component Breakdown

The project structure is organized cleanly into backend services, a single-page frontend, and operational runbook templates:

### ⚙️ 1. Backend Core (`/backend`)

The backend is written in Python 3.11 using FastAPI for non-blocking asynchronous requests, SQLite for historical persistence, and standard threading constructs for background execution.

- **[backend/main.py](file:///e:/run/backend/main.py)**:
  - Configures the FastAPI router.
  - Exposes REST API endpoints for dashboard interactions.
  - Spawns background tasks using FastAPI's `BackgroundTasks` to avoid blocking request threads.
  - Manages global, in-memory server health statuses (`server_status`).

- **[backend/agent_runner.py](file:///e:/run/backend/agent_runner.py)**:
  - Implements the [OpsAgentRunner](file:///e:/run/backend/agent_runner.py#L22) class.
  - Orchestrates the main execution loop: loading the parser, invoking the classification model, updating feed logs, sending Discord notifications, and waiting on the `confirm_event` thread lock for interactive interventions.
  - Implements a fallback rule-based classification if the local Ollama instance is unreachable.

- **[backend/mcp_tool.py](file:///e:/run/backend/mcp_tool.py)**:
  - Defines the [ShellExecutorMCPTool](file:///e:/run/backend/mcp_tool.py#L4).
  - Maintains a strict security allowlist of commands in `ALLOWED_COMMANDS`.
  - Simulates the stdout, stderr, and execution timings of standard Linux utilities (e.g. `systemctl`, `df`, `top`, `pg_isready`) based on the active failure context.

- **[backend/runbook_parser.py](file:///e:/run/backend/runbook_parser.py)**:
  - Implements the static [RunbookParser](file:///e:/run/backend/runbook_parser.py#L3).
  - Uses targeted regular expressions to extract structured metadata (type, description, command, expected output, and risk details) from Markdown files.

- **[backend/database.py](file:///e:/run/backend/database.py)**:
  - Handles the SQLite connection.
  - Initializes schemas for executions and individual steps.
  - Provides helper methods like [start_execution](file:///e:/run/backend/database.py#L48), [log_step](file:///e:/run/backend/database.py#L80), and [get_stats](file:///e:/run/backend/database.py#L121) to calculate real-time analytics.

---

### 🖥️ 2. Frontend Interface (`/frontend`)

- **[frontend/index.html](file:///e:/run/frontend/index.html)**:
  - A premium, dark-themed, glassmorphic Single Page Application.
  - Built using vanilla HTML5 semantic tags, custom CSS variables, keyframe animations, and FontAwesome indicators.
  - Features real-time state polling via async Javascript `fetch()` calls.
  - Includes interactive elements such as step execution terminals, trigger action controls, live status cards, and historical CSV exporting tools.

---

### 📓 3. Operational Intelligence (`/runbooks`)

Operational knowledge is declared declaratively in markdown files:
- **[runbooks/nginx_down.md](file:///e:/run/runbooks/nginx_down.md)**: Resolves web server binding failures by verifying system logs, sockets, and restarting the service.
- **[runbooks/database_failure.md](file:///e:/run/runbooks/database_failure.md)**: Resolves PostgreSQL service refusal.
- **[runbooks/high_cpu.md](file:///e:/run/runbooks/high_cpu.md)**: Inspects CPU profiles and terminates runaway background worker threads.
- **[runbooks/disk_full.md](file:///e:/run/runbooks/disk_full.md)**: Audits directories and compresses log archives.

---

## 🗄️ Database Schema Design

The SQLite database (`opsbot.db`) contains two tables in a one-to-many relationship, storing incident resolution records and command outcomes:

```mermaid
erDiagram
    executions ||--o{ steps : "executes"
    executions {
        INTEGER id PK "Auto Increment"
        TEXT failure_type "Failure category"
        TEXT runbook_name "Associated Markdown filename"
        TEXT started_at "ISO-8601 Timestamp"
        TEXT completed_at "ISO-8601 Timestamp (nullable)"
        INTEGER total_steps "Total steps parsed"
        INTEGER completed_steps "Successfully run steps count"
        TEXT status "running | completed | failed"
        INTEGER discord_sent "Counter for metrics"
    }
    steps {
        INTEGER id PK "Auto Increment"
        INTEGER execution_id FK "Refers to executions(id)"
        INTEGER step_number "Index of step"
        TEXT step_type "SAFE | RISKY"
        TEXT description "Step summary"
        TEXT command "Shell command"
        TEXT output "Console stdout/stderr"
        TEXT status "SUCCESS | FAILED"
        INTEGER needs_confirm "Boolean flag (0 or 1)"
        TEXT confirmed_at "ISO-8601 Timestamp (nullable)"
        TEXT executed_at "ISO-8601 Timestamp"
    }
```

---

## 📡 REST API Specifications

The FastAPI backend exposes the following endpoints for data querying and status mutations:

| Endpoint | Method | Description | Response Model |
| :--- | :---: | :--- | :--- |
| `/` | `GET` | Serves the HTML single-page dashboard app. | File (HTML) |
| `/api/status` | `GET` | Fetches the health state of services, CPU, disk, and agent activity. | JSON Object |
| `/api/trigger/{failure_type}` | `POST` | Sets a service status to failed and starts the agent runner in a background thread. | JSON Confirmation |
| `/api/agent/feed` | `GET` | Retrieves the latest terminal logs generated in the active loop. | Array of Entries |
| `/api/confirm` | `POST` | Releases the `confirm_event` event lock, authorizing the agent to run the risky step. | JSON Confirmation |
| `/api/skip` | `POST` | Releases the `confirm_event` event lock, ignoring the step and proceeding. | JSON Confirmation |
| `/api/runbooks/{name}` | `GET` | Reads and returns the raw Markdown runbook matching `{name}`. | JSON with raw text |
| `/api/history` | `GET` | Fetches the last 20 incident execution records from the database. | Array of Executions |
| `/api/stats` | `GET` | Aggregates database runs to return counts and average resolution times. | JSON Metrics |

---

## 🧠 AI Step Classification Prompt

The agent leverages local Ollama Llama3 to evaluate risks dynamically. It forwards contextual parameters to the LLM and demands a structured response.

### System Prompt & Formatting Rules

```text
You are an expert IT operations AI agent named RUNBOOK AGENT.
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
REASONING: one sentence why confirmation needed
```

> [!IMPORTANT]
> **Safety Fallback Mechanics**
> If Ollama is offline or experiences parsing timeouts, the system invokes a fallback classifier. This fallback automatically flags any step designated as `RISKY` in the markdown source runbook as a safety measure.

---

## 🛡️ Security Allowlist Controls

To prevent execution of arbitrary code and malicious actions, the [ShellExecutorMCPTool](file:///e:/run/backend/mcp_tool.py#L4) utilizes a strict whitelist model. Any command submitted to the agent is matched against `ALLOWED_COMMANDS`.

```python
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
```

> [!WARNING]
> Matched commands must exactly contain one of the whitelist signatures. Commands containing forbidden characters, pipe overrides, or parameters outside of this list will trigger a `Permission Denied` execution error (logged directly in the DB).

---

## 🛠️ Troubleshooting Guide

### 1. ConnectionRefusedError: Ollama Local Connection Failed
* **Cause**: Ollama service is not running on your host machine, or is running on a port other than `11434`.
* **Fix**: Ensure Ollama is launched (`ollama serve`) and the model is pulled locally with `ollama pull llama3`. If running on a non-standard port or hostname, modify `OLLAMA_URL` in [backend/agent_runner.py](file:///e:/run/backend/agent_runner.py#L20).

### 2. Discord Webhook Fails to Deliver Alerts
* **Cause**: Unconfigured webhook link or network firewall blocks outbox requests to Discord.
* **Fix**: Copy your Discord channel webhook URL and replace `DISCORD_WEBHOOK` in [backend/agent_runner.py](file:///e:/run/backend/agent_runner.py#L19). If you leave it empty or configured to `"YOUR_WEBHOOK_URL"`, the agent will gracefully bypass notifications and log a debug message.

### 3. Database Locking (`sqlite3.OperationalError: database is locked`)
* **Cause**: SQLite database is accessed simultaneously from multiple worker threads without write locks enabled.
* **Fix**: The backend automatically opens short-lived connections and calls `.close()` immediately inside database hooks. Avoid manually locking `opsbot.db` with separate DB explorers while a demo is active.

### 4. UnicodeEncodeError on Windows Terminal Logs
* **Cause**: The default Windows command prompt (cmd/powershell) lacks UTF-8 logging support, throwing errors when emojis are sent to standard output.
* **Fix**: [backend/agent_runner.py](file:///e:/run/backend/agent_runner.py) contains safe encoding loops (`.encode('ascii', 'ignore').decode()`) to strip emojis before logging commands locally. Ensure Python is launched with UTF-8 support if you plan to view logs containing full characters.

---

*For additional project support, please review the instructions outlined in the [README.md](file:///e:/run/README.md) or submit a ticket to the systems engineering team.*
