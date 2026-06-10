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
                    self.abort_pending_step = False
                    # Block waiting for human confirmation POST `/api/confirm` or `/api/abort`
                    self.confirm_event.wait()
                    
                    if getattr(self, 'abort_pending_step', False):
                        raise Exception("Execution aborted by user.")
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
            if "aborted by user" in str(e):
                self.log_activity({"status": "ABORTED", "message": "🛑 Aborted successfully"})
                self.send_discord("ABORTED — 🛑 Aborted successfully")
            else:
                print(f"[Agent Runner Crash] {e}")
                self.log_activity({"status": "ERROR", "message": f"Agent Loop Crashed: {str(e)}"})
            self._restore_server_status(failure_type)
            db.complete_execution(self.current_execution_id, "aborted", completed_count)
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
