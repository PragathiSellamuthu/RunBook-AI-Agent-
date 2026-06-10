# Runbook: Nginx Server Down
## Failure Type: nginx_down
## Severity: Critical
## Estimated Resolution: 4 minutes
## Description: This runbook handles cases where the Nginx web server is inactive or failing to bind to ports.

## Steps

### Step 1
- **Type:** SAFE
- **Description:** Check nginx process status
- **Command:** `systemctl status nginx`
- **Expected Output:** Process should be active (running)

### Step 2
- **Type:** SAFE
- **Description:** Check nginx error logs for binding or configuration errors
- **Command:** `tail -n 20 /var/log/nginx/error.log`
- **Expected Output:** No critical errors about port binding

### Step 3
- **Type:** SAFE
- **Description:** Check if port 80 is available or occupied
- **Command:** `curl -I http://localhost`
- **Expected Output:** HTTP 200 OK

### Step 4
- **Type:** RISKY
- **Description:** Restart nginx service to restore connectivity
- **Command:** `systemctl restart nginx`
- **Expected Output:** Status OK
- **Risk:** This will briefly interrupt any active web traffic during the restart.

### Step 5
- **Type:** SAFE
- **Description:** Verify nginx responding after restart
- **Command:** `systemctl status nginx`
- **Expected Output:** Process is active (running)

### Step 6
- **Type:** SAFE
- **Description:** Final uptime check
- **Command:** `uptime`
- **Expected Output:** System stable
