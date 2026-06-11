import os
import sys

sys.path.append('e:/INFINITE USE CASE BACKUP/project')
from runbook_agent.runbook_parser import RunbookParser
from runbook_agent.mcp_tool import ShellExecutorMCPTool

mcp = ShellExecutorMCPTool()
rbs = [f for f in os.listdir('e:/INFINITE USE CASE BACKUP/project/runbooks') if f.endswith('.md')]
fails = []

for rb in rbs:
    steps = RunbookParser.parse(f'e:/INFINITE USE CASE BACKUP/project/runbooks/{rb}')
    for s in steps:
        cmd = s['command']
        allowed = any(c in cmd for c in mcp.ALLOWED_COMMANDS)
        if not allowed:
            fails.append((rb, cmd))

print('Failed commands:', fails)
