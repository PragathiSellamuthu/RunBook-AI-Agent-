# 🤖 RUNBOOK AGENT — Autonomous Infrastructure Resolution Agent

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/Ollama-Llama3-orange?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com)
[![SQLite](https://img.shields.io/badge/SQLite-Database-blue?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Discord](https://img.shields.io/badge/Discord-Alerts-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com)

[![PROJECT EXPLANATION VIDEO](https://img.shields.io/badge/Watch-Demo%20Video-red?style=for-the-badge&logo=googledrive)](https://drive.google.com/drive/folders/1BX5-v6IP2rZ9mvcntu_ihYKvY_68ao-P?usp=sharing)

**RUNBOOK AGENT** is a real-time, autonomous AI operations (AIOps) agent designed to detect, diagnose, and resolve critical cloud and system infrastructure failures. It bridges the gap between high-level reasoning and physical system execution using a secure Model Context Protocol (MCP) execution design and local LLM evaluation.

> [!NOTE]
> This system is built for SREs and Devops engineers. It automates standard operating procedures (runbooks) while maintaining a strict security envelope and Human-in-the-Loop (HITL) authorization protocols.

---

## ✨ Key Features

- **🔄 Autonomous Execution Loop**: Parses markdown-formatted operational runbooks and executes diagnostic/remediative steps sequentially.
- **🛡️ MCP Sandboxed Execution Layer**: Uses a secure tool with a strict command allowlist to simulate terminal inputs and return realistic Linux execution output.
- **🧠 Local AI Step Classification**: Integrates with a local Llama3 instance running on Ollama to decide if a remediation command is `SAFE` (execute immediately) or `RISKY` (restart/terminate services).
- **👥 Human-in-the-Loop Safeguards**: Automatically pauses execution on risky commands, alerts the SRE team, and requests confirmation in the dashboard before proceeding.
- **📊 Real-time Operations Dashboard**: Single-page dark mode UI reporting live feed activity, status gauges, execution analytics, and incident histories.
- **🔔 Live Discord Notifications**: Instantly pushes webhook alerts for incident detection, authorization alerts, step compliance metrics, and resolutions.

---

## 📂 Project Structure

This repository is organized into the following directories:

### [`Project/`](Project/)
The core application workspace containing the RunBook Agent system.
- **`runbook_agent/`**: Core backend application logic (FastAPI server, AI state machine, MCP tool).
- **`frontend/`**: The frontend UI for the Real-time Operations Dashboard.
- **`runbooks/`**: Markdown-based operational knowledge bases (e.g., handling Nginx failures, high CPU, etc.).
- **`build_docs.py`**: Documentation builder script.

### [`DOCUMENTS/`](DOCUMENTS/)
Contains essential documentation and reference materials for the project.
- **`TECH_STACK.md`**: Detailed overview of the project's technology stack.
- **`project_documentation.md`**: Comprehensive architectural manual, API routes, and developer instructions.
- **`prompts.md`**: AI instruction sets and system prompts used by the LLM.
- **`requirements.txt`**: Project dependencies manifest.

---

## 🛠️ Quick Start

### 1. Install Dependencies
Navigate to the `Project/` directory or use the provided `requirements.txt`:
```bash
pip install -r DOCUMENTS/requirements.txt
```

### 2. Run Local LLaMA3 Model
Ensure [Ollama](https://ollama.com) is installed, then pull the model:
```bash
ollama pull llama3
```

### 3. Start the Server
Run the FastAPI backend using Uvicorn from the `Project/` directory:
```bash
cd Project
python -m uvicorn runbook_agent.main:app --reload --port 8000
```
Then open your browser to `http://localhost:8000` to access the dashboard.

---

## 🚀 Live Application & Community

- **Live Dashboard**: [https://runbook.onrender.com](https://ai-runbook-agent.onrender.com)
- **Discord Community**: [Join our Server](https://discord.com/invite/dQEXVDS5) to receive live incident alerts and notifications.

---

## 📖 Additional Documentation

For a detailed breakdown of database structures, API routes, security considerations, and troubleshooting guidelines, please refer to the **[Project Documentation](DOCUMENTS/project_documentation.md)** and **[Tech Stack](DOCUMENTS/TECH_STACK.md)**.
