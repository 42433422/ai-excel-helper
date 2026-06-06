"""Thread-backed task queue for desktop mode.

It is intentionally small: the goal is to remove the hard Redis/Celery runtime
dependency for single-user desktop deployments while keeping the existing task
submission contract usable.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="xcagi-desktop-task")


def submit_background(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Future[Any]:
    return _executor.submit(func, *args, **kwargs)


def shutdown_background_tasks(wait: bool = False) -> None:
    _executor.shutdown(wait=wait, cancel_futures=not wait)
