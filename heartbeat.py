import asyncio
import logging
from functools import wraps
from threading import Timer
from typing import Any, Callable, TypeVar, cast

from temporalio import activity

# Configure logging with timestamp format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d - %(message)s",
    datefmt="%H:%M:%S",
)

F = TypeVar("F", bound=Callable[..., Any])


class RepeatingTimer(Timer):
    def run(self) -> None:
        # No need to send heartbeat immediately
        self.finished.wait(self.interval)
        while not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
            self.finished.wait(self.interval)


def heartbeat_in_thread(fn: F) -> F:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        activity_info = activity.info()
        activity_id = activity_info.activity_id
        heartbeat_timeout = activity_info.heartbeat_timeout
        heartbeat_timer = None
        if heartbeat_timeout:
            heartbeat_interval = heartbeat_timeout.total_seconds() / 2
            logging.info(
                f"[{activity_id}] Starting heartbeat timer (interval: {heartbeat_interval}s)"
            )
            heartbeat_timer = RepeatingTimer(
                heartbeat_interval,
                _heartbeat,
                args=[activity._Context.current().heartbeat, activity_id],
            )
            heartbeat_timer.start()
        try:
            return fn(*args, **kwargs)
        finally:
            if heartbeat_timer:
                logging.info(f"[{activity_id}] Stopping heartbeat timer")
                heartbeat_timer.cancel()

    return cast(F, wrapper)


def _heartbeat(heartbeat_fn, activity_id: str) -> None:
    try:
        heartbeat_fn()
        logging.info(f"[{activity_id}] Heartbeat sent")
    except Exception as e:
        logging.error(f"[{activity_id}] Heartbeat error: {e}")
        raise


def async_heartbeat(fn: F) -> F:
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        activity_info = activity.info()
        activity_id = activity_info.activity_id
        heartbeat_timeout = activity_info.heartbeat_timeout
        heartbeat_task = None

        if heartbeat_timeout:
            heartbeat_interval = heartbeat_timeout.total_seconds() / 2
            logging.info(
                f"[{activity_id}] Starting async heartbeat (interval: {heartbeat_interval}s)"
            )

            async def heartbeat_loop():
                await asyncio.sleep(heartbeat_interval)
                while True:
                    try:
                        activity.heartbeat()
                        logging.info(f"[{activity_id}] Heartbeat sent")
                    except:
                        logging.error(
                            f"[{activity_id}] Heartbeat error:", exc_info=True
                        )
                        raise
                    await asyncio.sleep(heartbeat_interval)

            heartbeat_task = asyncio.create_task(heartbeat_loop())

        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        except:
            logging.error(f"[{activity_id}] Activity exception:", exc_info=True)
            raise
        finally:
            if heartbeat_task:
                logging.info(f"[{activity_id}] Stopping async heartbeat")
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

    return cast(F, wrapper)
