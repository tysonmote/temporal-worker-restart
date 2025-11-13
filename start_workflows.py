import argparse
import asyncio
from temporalio.client import Client
from workflows import SimpleWorkflow


async def main(count: int):
    client = await Client.connect("localhost:7233")

    print(f"Starting {count} workflows...")

    tasks = []
    for i in range(count):
        workflow_id = f"simple-workflow-{i}"
        task = client.start_workflow(
            SimpleWorkflow.run,
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
        default=100,
        help="Number of workflows to start (default: 100)",
    )
    args = parser.parse_args()

    asyncio.run(main(args.count))
