import logging
import time
from datetime import timedelta
from temporalio import activity, workflow
from temporalio.common import RetryPolicy
from heartbeat import heartbeat_in_thread, async_heartbeat

# Configure logging with timestamp format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d - %(message)s",
    datefmt="%H:%M:%S",
)


@activity.defn
@async_heartbeat
def simple_activity(sleep_seconds: float) -> str:
    """Simple activity that sleeps for a configurable duration."""
    activity_info = activity.info()
    activity_id = activity_info.activity_id
    heartbeat_timeout = activity_info.heartbeat_timeout

    logging.info(
        f"[{activity_id}] Activity start (sleep: {sleep_seconds}s, heartbeat_timeout: {heartbeat_timeout})"
    )

    try:
        time.sleep(sleep_seconds)
        logging.info(f"[{activity_id}] Activity success after {sleep_seconds}s")
        return f"Activity completed after {sleep_seconds}s"
    except Exception as e:
        logging.error(f"[{activity_id}] Activity exception: {e}")
        raise


@workflow.defn
class SimpleWorkflow:
    """Simple workflow that executes a single activity in a separate task queue."""

    @workflow.run
    async def run(
        self,
        activity_timeout_seconds: float,
        activity_sleep_seconds: float,
        heartbeat_timeout_seconds: float = 0,
    ) -> str:
        activity_options = {
            "start_to_close_timeout": timedelta(seconds=activity_timeout_seconds),
            "task_queue": "activities",
            "retry_policy": RetryPolicy(maximum_attempts=1),
        }

        if heartbeat_timeout_seconds > 0:
            activity_options["heartbeat_timeout"] = timedelta(
                seconds=heartbeat_timeout_seconds
            )

        result = await workflow.execute_activity(
            simple_activity,
            activity_sleep_seconds,
            **activity_options,
        )
        return result
