import logging
import time
from datetime import datetime, timedelta
from temporalio import activity, workflow
from temporalio.common import RetryPolicy

# Configure logging with timestamp format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d - %(message)s',
    datefmt='%H:%M:%S'
)


@activity.defn
def simple_activity(sleep_seconds: float) -> str:
    """Simple activity that sleeps for a configurable duration."""
    activity_info = activity.info()
    activity_id = activity_info.activity_id

    logging.info(f"[{activity_id}] Activity start (sleep: {sleep_seconds}s)")

    try:
        time.sleep(sleep_seconds)
        logging.info(f"[{activity_id}] Activity success")
        return f"Activity completed after {sleep_seconds}s"
    except Exception as e:
        logging.error(f"[{activity_id}] Activity exception: {e}")
        raise


@workflow.defn
class SimpleWorkflow:
    """Simple workflow that executes a single activity in a separate task queue."""

    @workflow.run
    async def run(self, activity_timeout_seconds: float, activity_sleep_seconds: float) -> str:
        result = await workflow.execute_activity(
            simple_activity,
            activity_sleep_seconds,
            start_to_close_timeout=timedelta(seconds=activity_timeout_seconds),
            task_queue="activities",
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
        return result
