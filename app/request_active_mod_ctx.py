from __future__ import annotations

import contextvars
import re
from collections.abc import Mapping

_active_mod_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "xcagi_request_active_mod_id",
    default="",
)

_MOD_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def normalize_active_mod_id(raw: str | None) -> str:
    v = str(raw or "").strip()
    if not v:
        return ""
    if not _MOD_ID_RE.match(v):
        return ""
    return v


def parse_active_mod_header(headers: Mapping[str, str]) -> str:
    for k in ("x-xcagi-active-mod-id", "X-XCAGI-Active-Mod-Id"):
        if k in headers:
            return normalize_active_mod_id(headers.get(k))
    return ""


def set_request_active_mod_id(active_mod_id: str | None):
    return _active_mod_id_ctx.set(normalize_active_mod_id(active_mod_id))


def reset_request_active_mod_id(token) -> None:
    _active_mod_id_ctx.reset(token)


def get_request_active_mod_id() -> str:
    return normalize_active_mod_id(_active_mod_id_ctx.get())


def has_request_active_mod_id() -> bool:
    return bool(get_request_active_mod_id())
