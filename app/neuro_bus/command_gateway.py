"""
Request-reply on NeuroBus: HTTP/command facades publish an event and await handler result.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from app.neuro_bus.events.base import NeuroEvent

logger = logging.getLogger(__name__)

_COMMAND_REPLY_KEY = "_command_reply_id"

_gateway: CommandGateway | None = None


class CommandGateway:
    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Future[Any]] = {}

    def prepare_command_event(self, event: NeuroEvent) -> str:
        rid = str(uuid.uuid4())
        event.payload[_COMMAND_REPLY_KEY] = rid
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError as e:
            raise RuntimeError(
                "CommandGateway.prepare_command_event requires a running event loop"
            ) from e
        self._pending[rid] = loop.create_future()
        return rid  # same as event.payload[_COMMAND_REPLY_KEY]

    async def wait_for_result(self, reply_id: str, timeout: float) -> Any:
        fut = self._pending.get(reply_id)
        if fut is None:
            raise KeyError(f"unknown command reply_id: {reply_id}")
        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except TimeoutError:
            self._pending.pop(reply_id, None)
            if not fut.done():
                fut.cancel()
            raise
        finally:
            self._pending.pop(reply_id, None)

    def cancel_pending(self, reply_id: str) -> None:
        fut = self._pending.pop(reply_id, None)
        if fut and not fut.done():
            fut.cancel()

    def resolve(
        self, event: NeuroEvent, result: Any = None, error: BaseException | None = None
    ) -> None:
        rid = event.payload.get(_COMMAND_REPLY_KEY)
        if not rid:
            return
        fut = self._pending.pop(rid, None)
        if fut is None or fut.done():
            if rid:
                logger.debug("Command reply late or unknown reply_id=%s", rid)
            return
        if error is not None:
            fut.set_exception(error)
        else:
            fut.set_result(result)


def get_command_gateway() -> CommandGateway:
    global _gateway
    if _gateway is None:
        _gateway = CommandGateway()
    return _gateway


def try_complete_command_reply(
    event: NeuroEvent,
    result: Any = None,
    error: BaseException | None = None,
) -> None:
    get_command_gateway().resolve(event, result=result, error=error)
