import asyncio
from datetime import timedelta
from temporalio import activity, workflow


@activity.defn
async def simple_activity() -> str:
    """Simple activity that sleeps for 0.1 seconds."""
    await asyncio.sleep(0.1)
    return "Activity completed"


@workflow.defn
class SimpleWorkflow:
    """Simple workflow that executes a single activity in a separate task queue."""

    @workflow.run
    async def run(self) -> str:
        result = await workflow.execute_activity(
            simple_activity,
            start_to_close_timeout=timedelta(minutes=5),
            task_queue="activities",
        )
        return result
