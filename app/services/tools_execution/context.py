from __future__ import annotations

import logging
from contextvars import ContextVar

from app.http.json_response import json_response

logger = logging.getLogger(__name__)

_tool_execute_headers: ContextVar[dict[str, str] | None] = ContextVar(
    "tool_execute_headers", default=None
)


def set_tool_execute_headers(headers: dict[str, str] | None) -> None:
    _tool_execute_headers.set(headers)


def _hdr(name: str, default: str = "") -> str:
    h = _tool_execute_headers.get()
    if not h:
        return default
    for k, v in h.items():
        if k.lower() == name.lower():
            return str(v) if v is not None else default
    return default


def _j(data: dict, status: int = 200):
    return json_response(data, status)
