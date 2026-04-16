"""HTTP 请求内「仅暴露单个扩展包」的 mod id（请求头 + 进程内 ContextVar）。"""

from __future__ import annotations

import re
from contextvars import ContextVar, Token

_request_active_mod_id: ContextVar[str | None] = ContextVar("request_active_mod_id", default=None)

_MOD_ID_SAFE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")


def get_request_active_mod_id() -> str | None:
    return _request_active_mod_id.get()


def set_request_active_mod_id(mod_id: str | None) -> Token:
    v = (mod_id or "").strip() or None
    if v is not None and not _MOD_ID_SAFE.match(v):
        v = None
    return _request_active_mod_id.set(v)


def reset_request_active_mod_id(token: Token) -> None:
    _request_active_mod_id.reset(token)


def parse_active_mod_header(headers_lower: dict[str, str]) -> str | None:
    """解析 ASGI/FastAPI 已规范为小写键名的 headers 映射。"""
    for hk in ("x-xcagi-active-mod-id", "x-xcagi-single-mod-id"):
        raw = str(headers_lower.get(hk, "")).strip()
        if not raw:
            continue
        if _MOD_ID_SAFE.match(raw):
            return raw
    return None
