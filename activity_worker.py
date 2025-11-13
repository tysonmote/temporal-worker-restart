import argparse
import asyncio
from datetime import timedelta
from temporalio.client import Client
from temporalio.worker import Worker
from workflows import simple_activity


async def main(interval: float):
    client = await Client.connect("localhost:7233")

    restart_count = 0
    while True:
        restart_count += 1
        print(
            f"\n[Restart #{restart_count}] Starting activity worker (max 1 concurrent activity, restart interval: {interval}s)"
        )

        worker = Worker(
            client,
            task_queue="activities",
            activities=[simple_activity],
            max_concurrent_activities=1,
            graceful_shutdown_timeout=timedelta(seconds=10),
        )

        # Run worker in background
        run_task = asyncio.create_task(worker.run())

        try:
            # Wait before shutting down
            await asyncio.sleep(interval)

            # Initiate graceful shutdown
            print(
                f"[Restart #{restart_count}] Shutting down worker gracefully (timeout: 10s)..."
            )

            await worker.shutdown()
            await run_task

        except Exception as e:
            print(f"[Restart #{restart_count}] Error during shutdown: {e}")

        print(f"[Restart #{restart_count}] Worker shutdown complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Temporal activity worker with periodic restarts"
    )
    parser.add_argument(
        "interval",
        type=float,
        nargs="?",
        default=1.0,
        help="Shutdown interval in seconds (default: 1.0)",
    )
    args = parser.parse_args()

    asyncio.run(main(args.interval))
