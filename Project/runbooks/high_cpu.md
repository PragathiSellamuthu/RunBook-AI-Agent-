# Runbook: High CPU Usage (>95%)
## Failure Type: high_cpu
## Severity: High
## Estimated Resolution: 5 minutes
## Description: Resolves performance degradation caused by runaway processes consuming system CPU.

## Steps

### Step 1
- **Type:** SAFE
- **Description:** Check current CPU usage breakdown
- **Command:** `top -bn1 | grep 'Cpu'`
- **Expected Output:** CPU idle percentage should be above 10%

### Step 2
- **Type:** SAFE
- **Description:** Find top CPU consuming processes
- **Command:** `ps aux --sort=-%cpu | head -10`
- **Expected Output:** Identify the offending process ID

### Step 3
- **Type:** SAFE
- **Description:** Check system load average
- **Command:** `uptime`
- **Expected Output:** Load average should be within CPUs count

### Step 4
- **Type:** RISKY
- **Description:** Kill the top consuming process to restore stability
- **Command:** `systemctl restart nginx`
- **Expected Output:** Success message
- **Risk:** Terminating a process may result in data loss for that specific application.

### Step 5
- **Type:** SAFE
- **Description:** Verify CPU usage has normalized
- **Command:** `top -bn1 | grep 'Cpu'`
- **Expected Output:** Usage below 50%

### Step 6
- **Type:** SAFE
- **Description:** Check filesystem impact
- **Command:** `df -h`
- **Expected Output:** Normal disk I/O
