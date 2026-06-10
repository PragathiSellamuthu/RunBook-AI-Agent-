# RUNBOOK AGENT — Prompt Documentation

## Prompt 1: Step Classification Prompt
Used in `agent_runner.py` to decide if a step is SAFE or RISKY.

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

## Prompt 2: How AI Coding Assistant Was Used
Built using Antigravity AI to:
- Generate the high-performance FastAPI backend structure.
- Design the premium dark-themed dashboard with pure vanilla CSS and JS.
- Implement the complex agent loop with human-in-the-loop logic and multi-threading.
- Create realistic simulated command outputs for the MCP tool.
- Standardize the operational runbook markdown format.

## Prompt 3: Testing Prompts
- "Verify that the agent correctly pauses on RISKY steps and waits for the thread event."
- "Ensure the Discord notification payload is robust and includes incident metadata."
- "Refine the CSS animations for the server failure shake effect."
