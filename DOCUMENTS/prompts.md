# RunBook Agent — Prompt Documentation

This document logs all the prompt engineering work done to build, test, and run the **RunBook Agent** AI operations engine.

---

## Prompt 1: Step Classification Prompt

This prompt is sent to the local Ollama instance (running `llama3`) or the Groq fallback API (`llama3-8b-8192`) to decide if a given runbook recovery step should execute autonomously or hold for a human confirmation.

### Prompt Template

```text
You are an expert IT operations AI agent.
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

### Prompt Rationale
- **Structured Outputs constraint**: By requesting `AUTO_EXECUTE: yes/no` and `REASONING: [text]` on separate lines, we avoid verbose chat-style introductions, allowing simple string splitting or regex parsing in the Python runner loop.
- **Rule alignment**: We provide explicit examples of "SAFE" vs "RISKY" operations (e.g. killing processes, restarting servers, deleting files) to calibrate the agent’s risk-tolerance.

---

## Prompt 2: How AI Coding Assistant Was Used

During the development of **RunBook Agent**, the AI coding assistant was used to:
1. **Design and write the simulated Outputs**: Crafted extremely detailed command execution blocks (e.g., systemd status output, pg_isready, df, uptime tables) matching the simulated operating system states.
2. **Handle Multi-threading synchronization**: Implemented a thread-safe pattern using `threading.Event` to pause/resume the background thread runbook execution during a RISKY step, ensuring the FastAPI server responds immediately while the agent waits.
3. **Graceful Fallbacks**: Created a multi-tier fallback mechanism where if local Ollama LLaMA3 is down, it attempts the Groq API, and finally defaults to rule-based evaluation if both APIs are offline.

---

## Prompt 3: Testing Prompts

Below are the prompts used during development to verify and refine classification responses.

### Test Scenario A: CPU Process Killer
*Input command*: `kill -9 1234`
*Expected Output*:
```text
AUTO_EXECUTE: no
REASONING: Forcefully killing a process (PID 1234) is a risky operation that can cause application instability or data loss.
```

### Test Scenario B: Disk Space Free Checker
*Input command*: `df -h /`
*Expected Output*:
```text
AUTO_EXECUTE: yes
REASONING: Checking disk usage with df is a read-only command and is safe to execute automatically.
```
