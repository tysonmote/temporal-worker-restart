This repo is a minimal reproduction of an issue where graceful Temporal worker restarts will cause some activity tasks to get dropped.

## Prerequisites

- Docker and Docker Compose
- Python 3.8+
- pip

## Setup

```bash
pip install -r requirements.txt
docker-compose up -d
```

Wait a few moments for Temporal to initialize. You can access the Temporal UI at http://localhost:8080

## Running the Test

Run these three commands in separate terminals:

```bash
python workflow_worker.py
```

```bash
# Specify the restart interval in seconds (e.g., 1.0 second)
python activity_worker.py 1.0

# Optionally run N workers
python activity_worker.py -n 10 1.0
```

```bash
# Specify the number of workflows to start (e.g., 500)
python start_workflows.py 500
```

## Project Structure

- `docker-compose.yml` - Temporal server configuration (PostgreSQL backend)
- `workflows.py` - Workflow and activity definitions (activity sleeps 0.1s)
- `workflow_worker.py` - Worker for processing workflows (runs continuously)
- `activity_worker.py` - Chaos worker for processing activities (restarts every N seconds)
- `start_workflows.py` - Script to start N workflows (default: 100)
- `requirements.txt` - Python dependencies (temporalio SDK)

## Issues

### Lost activity tasks on worker restart

```bash
# Start 1,000 workflows
python start_workflows.py --activity_sleep 0 1000

# Start workflow worker
python workflow_worker.py

# Run 1 activity worker that restarts every 0.5 seconds
python activity_worker.py 0.5
```

Different restart intervals will yield different activity task loss rates:

| Restart Interval (s) | Lost Activities (%) |
|----------------------|---------------------|
| 0.1                  | 2.6%                |
| 0.25                 | 1.3%                |
| 0.5                  | 1.0%                |
| 1.0                  | 0.8%                |
| 2.0                  | 0.1%                |
| 4.0                  | 0.1%                |
| 8.0                  | 0.1%                |

Running 10 workers instead of 1 yields similar loss rates:

| Restart Interval (s) | Lost Activities (%) |
|----------------------|---------------------|
| 0.1                  | 4.2%                |
| 0.25                 | 1.5%                |
| 0.5                  | 0.9%                |
| 1.0                  | 0.6%                |
| 2.0                  | 0.1%                |
| 4.0                  | 0.2%                |
| 8.0                  | 0.1%                |

### Worker shutdown hangs in Python 3.11.8

**NOTE:** Fixed in temporalio >= 1.18.1

This issue affects Python 3.11.8 specifically but appears to be resolved in
Python 3.11.9 and later.

If the activity throws `temporalio.exceptions.CancelledError: Cancelled` due to
a start-to-close timeout or heartbeat timeout during a graceful shutdown, the
worker shutdown will hang indefinitely.

All tests done with 10s graceful shutdown timeout:

```bash
python activity_worker.py --graceful-shutdown-timeout 10
```

Tests:

```bash
# If activity duration > graceful shutdown timeout AND start-to-close timeout is
# hit, shutdown hangs forever:
GOOD   python start_workflows.py --activity-timeout 5 --activity-sleep 8 1
GOOD   python start_workflows.py --activity-timeout 15 --activity-sleep 11 1
BAD    python start_workflows.py --activity-timeout 5 --activity-sleep 11 1

# If heartbeats are enabled and activity duration > start-to-close timeout,
# shutdown hangs forever:
GOOD   python start_workflows.py --activity-timeout 9 --activity-sleep 8 --activity-heartbeat-timeout 2 1
BAD    python start_workflows.py --activity-timeout 7 --activity-sleep 8 --activity-heartbeat-timeout 2 1
```
