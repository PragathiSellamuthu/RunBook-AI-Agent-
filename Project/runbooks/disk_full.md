# Runbook: Disk Space Critical (>90%)
## Failure Type: disk_full
## Severity: High
## Estimated Resolution: 5 minutes
## Description: Frees up space on the primary partition to prevent system lockup.

## Steps

### Step 1
- **Type:** SAFE
- **Description:** Check current disk usage
- **Command:** `df -h`
- **Expected Output:** Use% should be below 90%

### Step 2
- **Type:** SAFE
- **Description:** Find largest directories in /var/log
- **Command:** `du -sh /var/log/*`
- **Expected Output:** List of large log folders

### Step 3
- **Type:** SAFE
- **Description:** Check specific nginx log file sizes
- **Command:** `ls -lh /var/log/nginx`
- **Expected Output:** Identify bloated access.log files

### Step 4
- **Type:** RISKY
- **Description:** Archive and compress old logs to free space
- **Command:** `tar -czf /backup/logs_$(date +%F).tar.gz /var/log/nginx/*.log`
- **Expected Output:** Archive created
- **Risk:** Log rotation/cleanup might make troubleshooting recent history more difficult.

### Step 5
- **Type:** SAFE
- **Description:** Verify disk space freed
- **Command:** `df -h`
- **Expected Output:** Use% below 80%

### Step 6
- **Type:** SAFE
- **Description:** Final check of filesystem health
- **Command:** `df -h`
- **Expected Output:** System stable
