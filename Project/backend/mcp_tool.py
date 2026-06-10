import datetime
import time

class ShellExecutorMCPTool:
    """
    MODEL CONTEXT PROTOCOL TOOL
    
    Execution layer for OpsBot AI.
    Simulates Linux commands on Windows with realistic outputs.
    """
    
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
    
    def __init__(self):
        self.start_time = datetime.datetime.now()

    def get_simulated_output(self, command, failure_context=None):
        timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        
        if "systemctl status nginx" in command:
            if failure_context == "nginx_down":
                return f"""● nginx.service - A high performance web server and a reverse proxy server
   Loaded: loaded (/lib/systemd/system/nginx.service; enabled; vendor preset: enabled)
   Active: inactive (dead) since {timestamp}; 5min ago
     Docs: man:nginx(8)
 Main PID: 1234 (code=exited, status=0/SUCCESS)"""
            else:
                return f"""● nginx.service - A high performance web server and a reverse proxy server
   Loaded: loaded (/lib/systemd/system/nginx.service; enabled; vendor preset: enabled)
   Active: active (running) since {self.start_time.strftime("%a %Y-%m-%d %H:%M:%S")}; 2h 15min ago
 Main PID: 4567 (nginx)
    Tasks: 2 (limit: 4915)
   Memory: 8.2M
   CGroup: /system.slice/nginx.service
           ├─4567 nginx: master process /usr/sbin/nginx -g daemon on; master_process on;
           └─4568 nginx: worker process"""

        if "systemctl restart nginx" in command:
            return "Stopping nginx: [  OK  ]\nStarting nginx: [  OK  ]"

        if "tail -n 20 /var/log/nginx/error.log" in command:
            if failure_context == "nginx_down":
                return f"""{timestamp} [alert] 4567#0: *123 worker process 4568 exited on signal 9
{timestamp} [error] 4567#0: *124 open() "/var/www/html/index.html" failed (2: No such file or directory)
{timestamp} [emerg] 4567#0: bind() to 0.0.0.0:80 failed (98: Address already in use)
{timestamp} [error] 1234#0: *125 upstream timed out (110: Connection timed out) while connecting to upstream"""
            return f"{timestamp} [notice] 4567#0: signal process started"

        if "top -bn1 | grep 'Cpu'" in command:
            if failure_context == "high_cpu":
                return "Cpu(s): 94.3 us, 3.1 sy, 0.0 ni, 1.2 id, 0.8 wa, 0.4 hi, 0.2 si, 0.0 st"
            return "Cpu(s): 12.5 us, 2.1 sy, 0.0 ni, 85.0 id, 0.2 wa, 0.1 hi, 0.1 si, 0.0 st"

        if "ps aux --sort=-%cpu | head -10" in command:
            if failure_context == "high_cpu":
                return """USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root      8812 87.4  4.2 1284560 342100 ?      Sl   10:00   5:23 /usr/bin/java -jar /apps/analytics-engine.jar
nginx     4567  2.1  0.5  158220  12440 ?      S    08:00   0:15 nginx: worker process
postgres  5432  1.8  2.1  456120  89120 ?      S    08:00   0:12 postgres: writer process"""
            return """USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
nginx     4567  0.5  0.5  158220  12440 ?      S    08:00   0:05 nginx: worker process
postgres  5432  0.4  2.1  456120  89120 ?      S    08:00   0:08 postgres: writer process"""

        if "df -h" in command:
            if failure_context == "disk_full":
                return """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        40G   37G  1.2G  91% /
tmpfs           7.8G     0  7.8G   0% /dev/shm
/dev/sdb1       100G   20G   75G  21% /data"""
            return """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        40G   15G   23G  40% /
tmpfs           7.8G     0  7.8G   0% /dev/shm
/dev/sdb1       100G   20G   75G  21% /data"""

        if "systemctl status postgresql" in command:
            if failure_context == "database_failure":
                return f"""● postgresql.service - PostgreSQL RDBMS
   Loaded: loaded (/lib/systemd/system/postgresql.service; enabled; vendor preset: enabled)
   Active: failed (Result: exit-code) since {timestamp}; 2min ago
  Process: 9912 ExecStart=/usr/lib/postgresql/15/bin/pg_ctl start -D /var/lib/postgresql/15/main -l /var/log/postgresql/postgresql-15-main.log (code=exited, status=1/FAILURE)"""
            return f"""● postgresql.service - PostgreSQL RDBMS
   Loaded: loaded (/lib/systemd/system/postgresql.service; enabled; vendor preset: enabled)
   Active: active (running) since {self.start_time.strftime("%a %Y-%m-%d %H:%M:%S")}; 2h 14min ago
 Main PID: 5432 (postgres)"""

        if "pg_isready" in command:
            if failure_context == "database_failure":
                return "localhost:5432 - no response"
            return "localhost:5432 - accepting connections"

        return f"Executed command: {command}\nStatus: SUCCESS\nOutput: [Simulated standard output for {command}]"

    def execute(self, command, step_description, failure_context):
        # Security check
        is_allowed = any(cmd in command for cmd in self.ALLOWED_COMMANDS)
        
        if not is_allowed:
            return {
                "success": False,
                "command": command,
                "output": f"ERROR: Command '{command}' is not in the security allowlist.",
                "error": "Permission Denied",
                "timestamp": datetime.datetime.now().isoformat(),
                "simulated": True,
                "execution_time_ms": 5
            }
        
        # Simulate execution time
        time.sleep(0.5) 
        
        output = self.get_simulated_output(command, failure_context)
        
        return {
            "success": True,
            "command": command,
            "output": output,
            "error": None,
            "timestamp": datetime.datetime.now().isoformat(),
            "simulated": True,
            "execution_time_ms": 520
        }

if __name__ == "__main__":
    mcp = ShellExecutorMCPTool()
    res = mcp.execute("systemctl status nginx", "Check nginx status", "nginx_down")
    print(res["output"])
