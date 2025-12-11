import logging
import time
from datetime import timedelta
from temporalio import activity, workflow
from temporalio.common import RetryPolicy

# Configure logging with timestamp format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d - %(message)s",
    datefmt="%H:%M:%S",
)


@activity.defn
def simple_activity(sleep_seconds: float) -> str:
    """Simple activity that sleeps for a configurable duration."""
    activity_info = activity.info()
    activity_id = activity_info.activity_id
    activity_start = time.time()

    try:
        if sleep_seconds > 0:
            elapsed = 0.0
            while elapsed < sleep_seconds:
                time.sleep(0.1)
                elapsed = time.time() - activity_start
            activity_duration = time.time() - activity_start
            logging.info(f"[{activity_id}] Activity success after {activity_duration}s")
    except Exception as e:
        activity_duration = time.time() - activity_start
        logging.error(
            f"[{activity_id}] Activity exception after {activity_duration}s: {e}"
        )
        raise


@workflow.defn
class SimpleWorkflow:
    """Simple workflow that executes a single activity in a separate task queue."""

    @workflow.run
    async def run(
        self,
        activity_timeout_seconds: float,
        activity_sleep_seconds: float,
    ) -> str:
        activity_options = {
            "start_to_close_timeout": timedelta(seconds=activity_timeout_seconds),
            "task_queue": "activities",
            "retry_policy": RetryPolicy(maximum_attempts=1),
        }

        result = await workflow.execute_activity(
            simple_activity,
            activity_sleep_seconds,
            **activity_options,
        )
        return result
