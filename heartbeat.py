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
        self.finished.wait(self.interval)

        while not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
            self.finished.wait(self.interval)


def heartbeat_in_thread(fn: F) -> F:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        activity_info = activity.info()
        activity_id = activity_info.activity_id
        heartbeat_timer = None
        if heartbeat_timeout := activity_info.heartbeat_timeout:
            interval = heartbeat_timeout.total_seconds() / 2
            logging.info(
                f"[{activity_id}] Starting heartbeat timer (interval: {interval}s)"
            )
            heartbeat_timer = RepeatingTimer(
                interval,
                _call,
                args=[activity._Context.current().heartbeat, activity_id],
            )
            heartbeat_timer.start()
        try:
            return fn(*args, **kwargs)
        finally:
            if heartbeat_timer:
                logging.info(f"[{activity_id}] Cancelling heartbeat timer")
                heartbeat_timer.cancel()

    return cast(F, wrapper)


def _call(fn, activity_id):
    logging.info(f"[{activity_id}] Sending heartbeat")
    try:
        fn()
    except:
        logging.error(f"[{activity_id}] Heartbeat failed", exc_info=True)
        raise
