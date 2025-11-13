import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from workflows import SimpleWorkflow


async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="workflows",
        workflows=[SimpleWorkflow],
    )

    print("Workflow worker started on 'workflows' task queue")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
