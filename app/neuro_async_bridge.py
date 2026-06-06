"""
Bridge sync call sites (e.g. sync FastAPI deps, threadpool routes) to the app's asyncio loop
so NeuroBus command/reply can complete on the same loop that runs the bus consumer.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from collections.abc import Coroutine
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_neuro_main_loop: asyncio.AbstractEventLoop | None = None


def set_neuro_main_loop(loop: asyncio.AbstractEventLoop | None = None) -> None:
    global _neuro_main_loop
    _neuro_main_loop = loop or asyncio.get_running_loop()


def get_neuro_main_loop() -> asyncio.AbstractEventLoop | None:
    return _neuro_main_loop


def run_coroutine_on_neuro_loop(coro: Coroutine[Any, Any, T], timeout: float = 120.0) -> T:
    """
    Run ``coro`` on the Neuro/FastAPI main loop. Safe from worker threads (e.g. sync route threadpool).
    """
    loop = _neuro_main_loop
    if loop is None:
        return asyncio.run(coro)
    if loop.is_running():
        fut = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return fut.result(timeout=timeout)
        except concurrent.futures.TimeoutError as e:
            fut.cancel()
            raise TimeoutError("neuro loop coroutine timed out") from e
    return loop.run_until_complete(coro)
