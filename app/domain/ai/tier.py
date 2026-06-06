"""AI 能力分级 (P1/P2) 与受限工具判定。

Phase 3 从 ``app.legacy.ai_tier`` 迁入。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException, Request

P1_BLOCKED_TOOL_NAMES: frozenset[str] = frozenset({"products_bulk_import"})


def _header(request: Request | None, name: str) -> str:
    if request is None:
        return ""
    return (request.headers.get(name) or "").strip()


def resolve_ai_tier(request: Request | None) -> str:
    claimed = _header(request, "X-XCAGI-AI-Tier").lower()
    if claimed != "p2":
        return "p1"
    secret = (os.environ.get("FHD_AI_ELEVATED_TOKEN") or "").strip()
    token = _header(request, "X-XCAGI-Elevated-Token")
    if secret and token and token == secret:
        return "p2"
    return "p1"


def assert_p2_elevated_claim_or_raise(request: Request | None) -> None:
    claimed = _header(request, "X-XCAGI-AI-Tier").lower()
    strict = (os.environ.get("FHD_AI_TIER_STRICT") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if claimed == "p2" and strict and resolve_ai_tier(request) != "p2":
        raise HTTPException(status_code=403, detail="p2 elevated token invalid")


def runtime_context_with_tier(
    runtime_context: Mapping[str, Any] | None, tier: str
) -> dict[str, Any]:
    out = dict(runtime_context or {})
    out["ai_tier"] = "p2" if tier == "p2" else "p1"
    return out


__all__ = [
    "P1_BLOCKED_TOOL_NAMES",
    "resolve_ai_tier",
    "assert_p2_elevated_claim_or_raise",
    "runtime_context_with_tier",
]
