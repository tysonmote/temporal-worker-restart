import argparse
import asyncio
import logging
import multiprocessing
import random
import signal
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from temporalio.client import Client
from temporalio.worker import Worker
from workflows import simple_activity

# Configure logging with timestamp format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d - %(message)s",
    datefmt="%H:%M:%S",
)


def sigint_handler(signum, frame):
    """Handle SIGINT by printing all thread stacks and exiting."""
    logging.info("SIGINT received, printing all thread stacks:")
    for thread_id, thread_frame in sys._current_frames().items():
        print("Stack for thread {}".format(thread_id))
        traceback.print_stack(thread_frame)
        print("")
    sys.exit(0)


async def main(interval: float, graceful_shutdown_timeout: float):
    client = await Client.connect("localhost:7233")

    restart_count = 0
    while True:
        restart_count += 1

        worker = Worker(
            client,
            task_queue="activities",
            activities=[simple_activity],
            activity_executor=ThreadPoolExecutor(max_workers=1),
            max_concurrent_activities=1,
            graceful_shutdown_timeout=timedelta(seconds=graceful_shutdown_timeout),
        )

        logging.info(
            f"[Restart #{restart_count}] Worker starting (max 1 concurrent activity, restart interval: {interval}s, graceful timeout: {graceful_shutdown_timeout}s)"
        )

        # Run worker in background
        run_task = asyncio.create_task(worker.run())

        try:
            # Wait before shutting down (with ±10% jitter to spread out worker restarts)
            jittered_interval = interval * random.uniform(0.9, 1.1)
            await asyncio.sleep(jittered_interval)

            # Initiate graceful shutdown
            logging.info(f"[Restart #{restart_count}] Worker shutdown() called")
            shutdown_start = time.time()

            await worker.shutdown()

            shutdown_duration = time.time() - shutdown_start
            logging.info(
                f"[Restart #{restart_count}] Worker shutdown() returned (took {shutdown_duration:.3f}s)"
            )

            await run_task
            logging.info(f"[Restart #{restart_count}] Worker done (run() returned)")

        except asyncio.CancelledError:
            logging.info(
                f"[Restart #{restart_count}] Worker cancelled during shutdown (expected)"
            )
        except Exception as e:
            logging.error(f"[Restart #{restart_count}] Error during shutdown: {e}")


def run_worker_process(worker_id: int, interval: float, graceful_shutdown_timeout: float):
    """Entry point for a worker sub-process."""
    # Reconfigure logging to include worker ID
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s.%(msecs)03d - [Worker {worker_id}] %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )
    signal.signal(signal.SIGINT, sigint_handler)
    asyncio.run(main(interval, graceful_shutdown_timeout))


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
    parser.add_argument(
        "--graceful-shutdown-timeout",
        type=float,
        default=5.0,
        help="Graceful shutdown timeout in seconds (default: 5.0)",
    )
    parser.add_argument(
        "-n",
        type=int,
        default=1,
        help="Number of workers to run in sub-processes (default: 1)",
    )
    args = parser.parse_args()

    if args.n <= 1:
        signal.signal(signal.SIGINT, sigint_handler)
        asyncio.run(main(args.interval, args.graceful_shutdown_timeout))
    else:
        processes = []
        for i in range(args.n):
            p = multiprocessing.Process(
                target=run_worker_process,
                args=(i + 1, args.interval, args.graceful_shutdown_timeout),
            )
            p.start()
            processes.append(p)
            logging.info(f"Started worker process {i + 1} (PID: {p.pid})")

        try:
            for p in processes:
                p.join()
        except KeyboardInterrupt:
            logging.info("Terminating all worker processes...")
            for p in processes:
                p.terminate()
            for p in processes:
                p.join()
