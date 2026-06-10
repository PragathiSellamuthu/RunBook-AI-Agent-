import re

class RunbookParser:
    """
    Parses markdown runbooks to extract structured steps for the AI Agent.
    """
    
    @staticmethod
    def parse(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            steps = []
            # Find all step blocks (e.g., ### Step 1)
            step_blocks = re.split(r'### Step \d+', content)[1:]
            
            for i, block in enumerate(step_blocks):
                step_num = i + 1
                
                # Extract fields using regex
                type_match = re.search(r'- \*\*Type:\*\* (SAFE|RISKY)', block)
                desc_match = re.search(r'- \*\*Description:\*\* (.*)', block)
                cmd_match = re.search(r'- \*\*Command:\*\* `(.*?)`', block)
                expected_match = re.search(r'- \*\*Expected Output:\*\* (.*)', block)
                risk_match = re.search(r'- \*\*Risk:\*\* (.*)', block)
                
                steps.append({
                    "step_number": step_num,
                    "step_type": type_match.group(1) if type_match else "SAFE",
                    "description": desc_match.group(1) if desc_match else "",
                    "command": cmd_match.group(1) if cmd_match else "",
                    "expected_output": expected_match.group(1) if expected_match else "",
                    "risk": risk_match.group(1) if risk_match else None
                })
            
            return steps
        except Exception as e:
            print(f"Error parsing runbook {file_path}: {e}")
            return []

if __name__ == "__main__":
    # Test parser
    parser = RunbookParser()
    # Assuming the file exists for testing
    # res = parser.parse("../runbooks/nginx_down.md")
    # print(res)
    pass
