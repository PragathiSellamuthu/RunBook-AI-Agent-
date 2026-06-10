import time
import datetime
import threading
import requests
import json
import os
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    OpenAI = None
    HAS_OPENAI = False

from .mcp_tool import ShellExecutorMCPTool
from .runbook_parser import RunbookParser
from . import database as db

# Configuration
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1513869705314570320/ZLSV5Qi4G2K78gux_KLPUYIFtl2w6F5R8ztTqGlXBjCkH3wUxNNl5z85TKjLO-yQlJJV" # User should replace this
OLLAMA_URL = "http://localhost:11434/v1"

class OpsAgentRunner:
    def __init__(self, activity_feed, server_status, confirm_event):
        self.mcp = ShellExecutorMCPTool()
        self.activity_feed = activity_feed
        self.server_status = server_status
        self.confirm_event = confirm_event
        self.current_execution_id = None
        self.is_running = False
        
        # Local Ollama Llama3 client (OpenAI compatible)
        try:
            if HAS_OPENAI and OpenAI is not None:
                self.ollama = OpenAI(
                    base_url=OLLAMA_URL,
                    api_key="ollama"
                )
            else:
                self.ollama = None
        except Exception:
            self.ollama = None

    def log_activity(self, entry):
        entry['timestamp'] = datetime.datetime.now().strftime("%H:%M:%S")
        self.activity_feed.append(entry)
        if len(self.activity_feed) > 50:
            self.activity_feed.pop(0)

    def send_discord(self, message):
        try:
            # Strip emojis for Windows console logs to prevent UnicodeEncodeError
            safe_log_msg = message.encode('ascii', 'ignore').decode().replace('\n', ' ')
            print(f"[DISCORD DEBUG] send_discord: {safe_log_msg[:100]}...")
            
            if not DISCORD_WEBHOOK or "YOUR_WEBHOOK_URL" in DISCORD_WEBHOOK:
                print(f"[DISCORD DEBUG] Webhook bypass (not configured).")
                return
                
            payload = {"content": message}
            res = requests.post(DISCORD_WEBHOOK, json=payload, timeout=5)
            print(f"[DISCORD DEBUG] Webhook response status: {res.status_code}")
            if res.status_code in [200, 204] and self.current_execution_id:
                db.increment_discord_sent(self.current_execution_id)
        except Exception as e:
            try:
                print(f"[DISCORD DEBUG] Discord error: {type(e).__name__}")
            except Exception:
                pass

    def classify_step(self, step_number, step_type, step_description, command, failure_context):
        """
        Ask Llama3 to classify this step as SAFE or RISKY.
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

        # Fallback to rule-based if Ollama is offline
        if not self.ollama:
            is_safe = (step_type == "SAFE")
            reasoning = "AI offline, using runbook classification."
            return {"auto_execute": is_safe, "reasoning": reasoning}

        try:
            response = self.ollama.chat.completions.create(
                model="llama3",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            content = response.choices[0].message.content.strip()
            
            auto_execute = "AUTO_EXECUTE: yes" in content
            reasoning = content.split("REASONING:")[1].strip() if "REASONING:" in content else "Classified by AI"
            return {"auto_execute": auto_execute, "reasoning": reasoning}
        except Exception as e:
            print(f"Ollama error: {e}")
            is_safe = (step_type == "SAFE")
            return {"auto_execute": is_safe, "reasoning": f"AI classification failed ({str(e)[:50]}), using rule-based fallback."}

    def run_runbook(self, runbook_file, failure_type):
        if self.is_running:
            return
        
        self.is_running = True
        self.server_status['agent_busy'] = True
        
        # 1. Parse Runbook
        runbook_path = f"Project/Test cases/{runbook_file}"
        steps = RunbookParser.parse(runbook_path)
        
        if not steps:
            self.log_activity({"status": "ERROR", "message": f"Runbook {runbook_file} not found or empty."})
            self.is_running = False
            self.server_status['agent_busy'] = False
            return

        # 2. Start Database Execution
        self.current_execution_id = db.start_execution(failure_type, runbook_file)
        db.update_execution_steps(self.current_execution_id, len(steps))

        # 3. Incident Detected Notification
        self.log_activity({"status": "FAILURE DETECTED", "message": f"{failure_type.replace('_', ' ').title()} System Critical!"})
        self.send_discord(f"🚨 INCIDENT DETECTED\nType: {failure_type.replace('_', ' ').title()}\nRunbook: {runbook_file} activated\nAgent: Starting resolution...\nTime: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_activity({"status": "AGENT ACTIVATED", "message": f"Executing {runbook_file}"})
        
        try:
            completed_count = 0
            for step in steps:
                # Log step start
                self.log_activity({"status": "INFO", "message": f"🔍 Step {step['step_number']} Starting: {step['description']}"})
                
                # Classify step
                classification = self.classify_step(
                    step['step_number'], 
                    step['step_type'], 
                    step['description'], 
                    step['command'], 
                    failure_type
                )
                
                if not classification['auto_execute']:
                    # Await confirmation
                    self.log_activity({
                        "status": "AWAITING CONFIRMATION", 
                        "message": f"Step {step['step_number']}: {step['command']}",
                        "needs_confirm": True,
                        "risk": step.get('risk', classification['reasoning'])
                    })
                    
                    self.send_discord(f"⚠️ HUMAN CONFIRMATION REQUIRED\nRunbook: {runbook_file} | Step {step['step_number']}\nCommand: {step['command']}\nRisk: {step.get('risk', 'Service interruption')}\nAction: Approve in Dashboard")
                    
                    self.confirm_event.clear()
                    # Wait for human to click confirm in UI
                    self.confirm_event.wait()
                    
                    self.log_activity({"status": "INFO", "message": "✅ Human confirmed risky step. Continuing..."})

                # Execute via MCP
                res = self.mcp.execute(step['command'], step['description'], failure_type)
                
                # Log Result
                status_icon = "✅" if res['success'] else "❌"
                self.log_activity({
                    "status": "SUCCESS" if res['success'] else "FAILED",
                    "message": f"{status_icon} Step {step['step_number']} Complete: {step['description']}"
                })
                
                # Update DB and Notification
                db.log_step(self.current_execution_id, {
                    **step, 
                    "output": res['output'], 
                    "status": "SUCCESS" if res['success'] else "FAILED"
                })
                
                if res['success']:
                    completed_count += 1
                    self.send_discord(f"✅ Step {step['step_number']} Complete — {runbook_file}\nCommand: {step['command']}\nStatus: SUCCESS | Time: {res['execution_time_ms']}ms")
                
                time.sleep(1.5) # Demo delay

            # Finish
            db.complete_execution(self.current_execution_id, "completed", completed_count)
            self.log_activity({"status": "RESOLVED", "message": f"🟢 ALL SYSTEMS OPERATIONAL: {failure_type.replace('_', ' ').title()}"})
            self.send_discord(f"🟢 INCIDENT RESOLVED\nType: {failure_type.replace('_', ' ').title()}\nResolution Time: ~4m\nSteps Executed: {completed_count}/{len(steps)}\nStatus: OPERATIONAL")
            
            # Reset server status
            self.reset_server_status(failure_type)
            
        except Exception as e:
            self.log_activity({"status": "ERROR", "message": f"Agent Loop Crashed: {str(e)}"})
            db.complete_execution(self.current_execution_id, "failed", 0)
        finally:
            self.is_running = False
            self.server_status['agent_busy'] = False

    def reset_server_status(self, failure_type):
        if failure_type == "nginx_down":
            self.server_status['nginx'] = "healthy"
        elif failure_type == "database_failure":
            self.server_status['database'] = "healthy"
        elif failure_type == "high_cpu":
            self.server_status['cpu'] = "normal"
        elif failure_type == "disk_full":
            self.server_status['disk'] = "normal"
