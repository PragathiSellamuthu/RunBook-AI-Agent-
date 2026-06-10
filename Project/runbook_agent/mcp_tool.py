import datetime
import time

class ShellExecutorMCPTool:
    """
    MODEL CONTEXT PROTOCOL TOOL
    
    Execution layer for RunBook Agent.
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
    
    def __init__(self, server_status_dict=None):
        self.start_time = datetime.datetime.now()
        # Reference to global status dict if provided
        self.server_status = server_status_dict or {
            "nginx": "healthy",
            "database": "healthy",
            "cpu": "normal",
            "disk": "normal"
        }

    def get_simulated_output(self, command, failure_context=None):
        timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        
        # STATE SYNC TRICK FOR NGINX
        if "systemctl restart nginx" in command:
            self.server_status["nginx"] = "healthy"
            # If we're executing high cpu runbook, restart nginx is the resolution step
            if failure_context == "high_cpu":
                self.server_status["cpu"] = "normal"
            return "Stopping nginx: [  OK  ]\nStarting nginx: [  OK  ]"

        if "systemctl status nginx" in command:
            # If server status shows down, return dead status
            if self.server_status.get("nginx") == "down" or failure_context == "nginx_down" and self.server_status.get("nginx") == "down":
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

        if "tail -n 20 /var/log/nginx/error.log" in command:
            if self.server_status.get("nginx") == "down" or failure_context == "nginx_down" and self.server_status.get("nginx") == "down":
                return f"""{timestamp} [alert] 4567#0: *123 worker process 4568 exited on signal 9
{timestamp} [error] 4567#0: *124 open() "/var/www/html/index.html" failed (2: No such file or directory)
{timestamp} [emerg] 4567#0: bind() to 0.0.0.0:80 failed (98: Address already in use)
{timestamp} [error] 1234#0: *125 upstream timed out (110: Connection timed out) while connecting to upstream"""
            return f"{timestamp} [notice] 4567#0: signal process started"

        if "curl -I http://localhost" in command:
            if self.server_status.get("nginx") == "down" or failure_context == "nginx_down" and self.server_status.get("nginx") == "down":
                return "curl: (7) Failed to connect to localhost port 80: Connection refused"
            return f"""HTTP/1.1 200 OK
Server: nginx/1.24.0
Date: {timestamp} GMT
Content-Type: text/html
Content-Length: 612
Connection: keep-alive"""

        # STATE SYNC TRICK FOR CPU
        if "top -bn1 | grep 'Cpu'" in command:
            if self.server_status.get("cpu") == "critical" or failure_context == "high_cpu" and self.server_status.get("cpu") == "critical":
                return "Cpu(s): 94.3 us, 3.1 sy, 0.0 ni, 1.2 id, 0.8 wa, 0.4 hi, 0.2 si, 0.0 st"
            return "Cpu(s): 12.5 us, 2.1 sy, 0.0 ni, 85.0 id, 0.2 wa, 0.1 hi, 0.1 si, 0.0 st"

        if "ps aux --sort=-%cpu | head -10" in command:
            if self.server_status.get("cpu") == "critical" or failure_context == "high_cpu" and self.server_status.get("cpu") == "critical":
                return """USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root      8812 87.4  4.2 1284560 342100 ?      Sl   10:00   5:23 /usr/bin/java -jar /apps/analytics-engine.jar
nginx     4567  2.1  0.5  158220  12440 ?      S    08:00   0:15 nginx: worker process
postgres  5432  1.8  2.1  456120  89120 ?      S    08:00   0:12 postgres: writer process"""
            return """USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
nginx     4567  0.5  0.5  158220  12440 ?      S    08:00   0:05 nginx: worker process
postgres  5432  0.4  2.1  456120  89120 ?      S    08:00   0:08 postgres: writer process"""

        # STATE SYNC TRICK FOR POSTGRESQL
        if "systemctl restart postgresql" in command:
            self.server_status["database"] = "healthy"
            return "Stopping postgresql: [  OK  ]\nStarting postgresql: [  OK  ]"

        if "systemctl status postgresql" in command:
            if self.server_status.get("database") == "down" or failure_context == "database_failure" and self.server_status.get("database") == "down":
                return f"""● postgresql.service - PostgreSQL RDBMS
   Loaded: loaded (/lib/systemd/system/postgresql.service; enabled; vendor preset: enabled)
   Active: failed (Result: exit-code) since {timestamp}; 2min ago
  Process: 9912 ExecStart=/usr/lib/postgresql/15/bin/pg_ctl start -D /var/lib/postgresql/15/main -l /var/log/postgresql/postgresql-15-main.log (code=exited, status=1/FAILURE)"""
            return f"""● postgresql.service - PostgreSQL RDBMS
   Loaded: loaded (/lib/systemd/system/postgresql.service; enabled; vendor preset: enabled)
   Active: active (running) since {self.start_time.strftime("%a %Y-%m-%d %H:%M:%S")}; 2h 14min ago
 Main PID: 5432 (postgres)"""

        if "pg_isready" in command:
            if self.server_status.get("database") == "down" or failure_context == "database_failure" and self.server_status.get("database") == "down":
                return "localhost:5432 - no response"
            return "localhost:5432 - accepting connections"

        if "tail -n 20 /var/log/postgresql/postgresql-15-main.log" in command:
            if self.server_status.get("database") == "down" or failure_context == "database_failure" and self.server_status.get("database") == "down":
                return f"""2026-06-10 14:02:11 UTC FATAL:  could not bind IPv4 address "0.0.0.0": Address already in use
2026-06-10 14:02:11 UTC HINT:   Is another postmaster already running on port 5432?
2026-06-10 14:02:12 UTC FATAL:  could not create shared memory segment: No space left on device
2026-06-10 14:02:12 UTC LOG:    database system is shut down"""
            return f"""2026-06-10 14:15:10 UTC LOG:    database system was shut down at 2026-06-10 14:14:50 UTC
2026-06-10 14:15:11 UTC LOG:    database system is ready to accept connections
2026-06-10 14:15:12 UTC LOG:    autovacuum launcher started"""

        # STATE SYNC TRICK FOR DISK
        if "tar -czf" in command:
            self.server_status["disk"] = "normal"
            return f"tar: Removing leading `/' from member names\nArchive /backup/logs_{timestamp.replace('/', '-').split(' ')[0]}.tar.gz created successfully."

        if "df -h" in command:
            if self.server_status.get("disk") == "critical" or failure_context == "disk_full" and self.server_status.get("disk") == "critical":
                return """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        40G   37G  1.2G  91% /
tmpfs           7.8G     0  7.8G   0% /dev/shm
/dev/sdb1       100G   20G   75G  21% /data"""
            return """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        40G   15G   23G  40% /
tmpfs           7.8G     0  7.8G   0% /dev/shm
/dev/sdb1       100G   20G   75G  21% /data"""

        if "du -sh /var/log/*" in command:
            return """16G     /var/log/nginx
4.5G    /var/log/syslog
1.2G    /var/log/postgresql
412M    /var/log/apt
124M    /var/log/journal"""

        if "ls -lh /var/log/nginx" in command:
            return """-rw-r----- 1 www-data adm 14G Jun 10 14:00 access.log.1
-rw-r----- 1 www-data adm 22M Jun 10 14:00 error.log
-rw-r----- 1 syslog   adm 4.5G Jun 10 14:02 syslog"""

        if "uptime" in command:
            return f" 14:15:10 up 2 days,  3:17,  1 user,  load average: { '11.45, 8.32, 4.10' if failure_context == 'high_cpu' else '0.22, 0.45, 0.51' }"

        if "free -m" in command:
            return """               total        used        free      shared  buff/cache   available
Mem:           15920        4812        8122         256        2986       10612
Swap:           2048         128        1920"""

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
