import os

files_to_doc = [
    "requirements.txt",
    "README.md",
    "runbook_agent/__init__.py",
    "runbook_agent/main.py",
    "runbook_agent/database.py",
    "runbook_agent/agent_runner.py",
    "runbook_agent/mcp_tool.py",
    "runbook_agent/runbook_parser.py",
    "frontend/index.html",
    "runbooks/high_cpu.md",
    "runbooks/database_failure.md",
    "runbooks/disk_full.md",
    "runbooks/nginx_down.md"
]

output_path = "project_documentation.md"

with open(output_path, "w", encoding="utf-8") as out:
    out.write("# RunBook AI Agent - Complete Project Documentation\n\n")
    out.write("This document contains the entire folder structure and source code needed to rebuild this project from scratch.\n\n")
    
    out.write("## Folder Structure\n")
    out.write("```text\n")
    out.write("project/\n")
    out.write("├── requirements.txt\n")
    out.write("├── README.md\n")
    out.write("├── frontend/\n")
    out.write("│   └── index.html\n")
    out.write("├── runbook_agent/\n")
    out.write("│   ├── __init__.py\n")
    out.write("│   ├── main.py\n")
    out.write("│   ├── database.py\n")
    out.write("│   ├── agent_runner.py\n")
    out.write("│   ├── mcp_tool.py\n")
    out.write("│   └── runbook_parser.py\n")
    out.write("└── runbooks/\n")
    out.write("    ├── database_failure.md\n")
    out.write("    ├── disk_full.md\n")
    out.write("    ├── high_cpu.md\n")
    out.write("    └── nginx_down.md\n")
    out.write("```\n\n")
    
    out.write("## Source Code Files\n\n")
    
    for fpath in files_to_doc:
        full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), fpath)
        if os.path.exists(full_path):
            out.write(f"### File: `{fpath}`\n")
            
            ext = fpath.split('.')[-1]
            if ext == 'py': lang = 'python'
            elif ext == 'html': lang = 'html'
            elif ext == 'md': lang = 'markdown'
            else: lang = 'text'
            
            out.write(f"```{lang}\n")
            with open(full_path, "r", encoding="utf-8") as f:
                out.write(f.read())
            out.write("\n```\n\n")
        else:
            print(f"Warning: {fpath} not found")

print(f"Successfully generated {output_path}")
