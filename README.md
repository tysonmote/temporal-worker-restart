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
python start_workflows.py --activity-timeout 2 --activity-sleep 30 10

# Run workflow worker
python workflow_worker.py

# Run activity worker with 10s graceful shutdown timeout
python activity_worker.py --graceful-shutdown-timeout 10
```

Activity worker hangs and doesn't process any further activities after completing activity as failed:

```
15:20:55.258 - [1] Activity start (sleep: 30.0s)
15:20:56.245 - [Restart #1] Worker shutdown() called
15:20:56.246 - Beginning worker shutdown, will wait 0:00:10 before cancelling activities
15:21:02.262 - Completing activity as failed ({'activity_id': '1', 'activity_type': 'simple_activity', 'attempt': 1, 'namespace': 'default', 'task_queue': 'activities', 'workflow_id': 'simple-workflow-6', 'workflow_run_id': '019a9945-557a-7d87-ba43-cca44c7e317c', 'workflow_type': 'SimpleWorkflow'})
Traceback (most recent call last):
  File "/Users/tyson/.pyenv/versions/3.11.8/lib/python3.11/site-packages/temporalio/worker/_activity.py", line 292, in _run_activity
    await self._execute_activity(start, running_activity, completion)
  File "/Users/tyson/.pyenv/versions/3.11.8/lib/python3.11/site-packages/temporalio/worker/_activity.py", line 568, in _execute_activity
    result = await impl.execute_activity(input)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/tyson/.pyenv/versions/3.11.8/lib/python3.11/site-packages/temporalio/worker/_activity.py", line 769, in execute_activity
    return await input.fn(*input.args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/tyson/Desktop/temporal-worker-restart/workflows.py", line 24, in simple_activity
    await asyncio.sleep(sleep_seconds)
  File "/Users/tyson/.pyenv/versions/3.11.8/lib/python3.11/asyncio/tasks.py", line 649, in sleep
    return await future
           ^^^^^^^^^^^^
asyncio.exceptions.CancelledError
```

It's notable that the CancelledError raised 7 seconds after activity start and 6 seconds after shutdown() is called despite the activity start-to-close timeout being set to 2 seconds and the graceful shutdown timeout being set to 10 seconds.
