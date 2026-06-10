# Runbook: Database Connection Failed
## Failure Type: database_failure
## Severity: Critical
## Estimated Resolution: 6 minutes
## Description: Restores PostgreSQL database availability when connections are refused.

## Steps

### Step 1
- **Type:** SAFE
- **Description:** Check database process status
- **Command:** `systemctl status postgresql`
- **Expected Output:** Process should be active (running)

### Step 2
- **Type:** SAFE
- **Description:** Check database port 5432 status
- **Command:** `pg_isready -h localhost`
- **Expected Output:** Accepting connections

### Step 3
- **Type:** SAFE
- **Description:** Check database error logs
- **Command:** `tail -n 20 /var/log/postgresql/postgresql-15-main.log`
- **Expected Output:** No 'fatal' or 'panic' messages

### Step 4
- **Type:** SAFE
- **Description:** Test database connectivity
- **Command:** `uptime`
- **Expected Output:** System healthy

### Step 5
- **Type:** RISKY
- **Description:** Restart database service to clear locked sessions
- **Command:** `systemctl restart postgresql`
- **Expected Output:** Success message
- **Risk:** Existing database connections will be dropped, and pending transactions may roll back.

### Step 6
- **Type:** SAFE
- **Description:** Verify connections restored after restart
- **Command:** `pg_isready -h localhost`
- **Expected Output:** Accepting connections
