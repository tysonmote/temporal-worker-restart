import argparse
import asyncio
from temporalio.client import Client
from workflows import SimpleWorkflow


async def main(
    count: int,
    activity_timeout_seconds: float,
    activity_sleep_seconds: float,
):
    client = await Client.connect("localhost:7233")

    print(
        f"Starting {count} workflows (activity timeout: {activity_timeout_seconds}s, activity sleep: {activity_sleep_seconds}s)..."
    )

    tasks = []
    for i in range(count):
        workflow_id = f"simple-workflow-{i}"
        task = client.start_workflow(
            SimpleWorkflow.run,
            args=(
                activity_timeout_seconds,
                activity_sleep_seconds,
            ),
            id=workflow_id,
            task_queue="workflows",
        )
        tasks.append(task)

        if (i + 1) % 100 == 0:
            print(f"Started {i + 1} workflows...")

    await asyncio.gather(*tasks)
    print(f"All {count} workflows started successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start Temporal workflows")
    parser.add_argument(
        "count",
        type=int,
        nargs="?",
        default=10,
        help="Number of workflows to start (default: 10)",
    )
    parser.add_argument(
        "--activity-timeout",
        type=float,
        default=5.0,
        help="Activity start-to-close timeout in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--activity-sleep",
        type=float,
        default=0.1,
        help="Activity sleep duration in seconds (default: 0.1)",
    )
    args = parser.parse_args()

    asyncio.run(
        main(
            args.count,
            args.activity_timeout,
            args.activity_sleep,
        )
    )
