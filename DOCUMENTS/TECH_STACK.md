# RunBook Agent - Tech Stack

The RunBook Agent is built using the following technologies:

## Core Backend
- **Python 3.11+**: The core programming language used for the backend logic and agent control flow.
- **FastAPI (v0.109.0)**: A modern, fast (high-performance) web framework for building APIs with Python 3.6+ based on standard Python type hints.
- **Uvicorn**: An ASGI web server implementation for Python.

## AI & Language Models
- **Ollama**: Used to run local large language models.
- **LLaMA3**: The primary open-source model used by the agent to classify steps, parse runbooks, and perform autonomous IT operations.

## Database
- **SQLite**: Used as the default lightweight, built-in database for recording execution logs, agent activities, and step states. (Can be upgraded to PostgreSQL for production environments).

## Alerts & Notifications
- **Discord Webhooks**: Used to send real-time alerts and incident status updates directly to a Discord channel.

## Frontend
- **HTML/CSS/JS (Vanilla)**: A lightweight, responsive, and dynamic web interface for the Operations Dashboard, featuring terminal-like logs, step tracking, and operator manual controls.
