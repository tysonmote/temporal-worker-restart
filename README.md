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

## Reproducible issues

### Hanging activity workers on graceful shutdown

```bash
# Start some activities that should time out after 2s every time
python start_workflows.py --activity-timeout 2 --activity-sleep 60 10

# Run workflow worker
python workflow_worker.py

# Run activity worker with 3s graceful shutdown timeout
python activity_worker.py --graceful-shutdown-timeout 3
```

Activity worker hangs until the synchronous activity returns, ignoring the start-to-close timeout and the graceful shutdown timeout:

```
16:28:27.285 - [Restart #1] Worker starting (max 1 concurrent activity, restart interval: 1.0s, graceful timeout: 3.0s)
16:28:27.298 - [1] Activity start (sleep: 60.0s)
16:28:28.287 - [Restart #1] Worker shutdown() called
16:28:28.287 - Beginning worker shutdown, will wait 0:00:03 before cancelling activities
16:29:27.301 - [1] Activity exception: Cancelled
2025-11-19T00:29:27.312388Z  WARN temporal_sdk_core::worker::activities: Activity not found on completion. This may happen if the activity has already been cancelled but completed anyway. task_token=TaskToken(CiRlYTYzNGM2My0yMGIzLTQ4NDEtYmQ1Yi01YThhNzQzODc1MTkSEXNpbXBsZS13b3JrZmxvdy04GiQwMTlhOTk4My0yM2U1LTc4OWEtOGQyZi1mMTM3ZDZmZGI0ODEgBSgBMgExQg9zaW1wbGVfYWN0aXZpdHlKCAgDEK6AQBgB) details=Status { code: NotFound, message: "workflow execution already completed", details: b"\x08\x05\x12$workflow execution already completed\x1aB\n@type.googleapis.com/temporal.api.errordetails.v1.NotFoundFailure", metadata: MetadataMap { headers: {"content-type": "application/grpc"} }, source: None }
16:29:27.319 - [Restart #1] Worker shutdown() returned (took 59.032s)
16:29:27.319 - [Restart #1] Worker done (run() returned)
```

