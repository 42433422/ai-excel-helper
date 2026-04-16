"""
P1 / P2 AI permission tier (server-side). Do not trust tier from JSON body.

P1: default; narrow tool list (e.g. hide products_bulk_import).
P2: only when header X-XCAGI-AI-Tier: p2 and X-XCAGI-Elevated-Token matches FHD_AI_ELEVATED_TOKEN.

Env:
  FHD_AI_ELEVATED_TOKEN - shared secret with trusted clients (Settings UI).
  FHD_AI_TIER_STRICT=1 - if client claims p2 with bad token, HTTP 403 (else downgrade to p1).
"""

from __future__ import annotations

import json
import os
from typing import Any, Mapping

from fastapi import HTTPException, Request

P1_BLOCKED_TOOL_NAMES: frozenset[str] = frozenset({"products_bulk_import"})


def _header(request: Request | None, name: str) -> str:
    if request is None:
        return ""
    v = request.headers.get(name)
    return (v or "").strip()


def resolve_ai_tier(request: Request | None) -> str:
    want = _header(request, "x-xcagi-ai-tier").lower()
    secret = os.environ.get("FHD_AI_ELEVATED_TOKEN", "").strip()
    token = _header(request, "x-xcagi-elevated-token")
    if want == "p2":
        if secret and token == secret:
            return "p2"
        return "p1"
    return "p1"


def assert_p2_elevated_claim_or_raise(request: Request | None) -> None:
    want = _header(request, "x-xcagi-ai-tier").lower()
    if want != "p2":
        return
    secret = os.environ.get("FHD_AI_ELEVATED_TOKEN", "").strip()
    token = _header(request, "x-xcagi-elevated-token")
    strict = os.environ.get("FHD_AI_TIER_STRICT", "").strip().lower() in ("1", "true", "yes", "on")
    if not strict:
        return
    if secret and token == secret:
        return
    raise HTTPException(
        status_code=403,
        detail="P2 requires valid X-XCAGI-Elevated-Token (must match server FHD_AI_ELEVATED_TOKEN)",
    )


def runtime_context_with_tier(
    runtime_context: dict[str, Any] | None,
    tier: str,
) -> dict[str, Any]:
    base: dict[str, Any] = dict(runtime_context) if isinstance(runtime_context, dict) else {}
    t = (tier or "p1").strip().lower()
    base["_fhd_ai_tier"] = "p2" if t == "p2" else "p1"
    return base


def effective_tier_from_runtime(runtime_context: Mapping[str, Any] | None) -> str:
    raw = ""
    if isinstance(runtime_context, Mapping):
        raw = str(runtime_context.get("_fhd_ai_tier") or "").strip().lower()
    return "p2" if raw == "p2" else "p1"


def filter_tools_for_tier(tools: list[dict[str, Any]], tier: str) -> list[dict[str, Any]]:
    if (tier or "p1").strip().lower() == "p2":
        return list(tools)
    out: list[dict[str, Any]] = []
    for t in tools:
        fn = t.get("function") if isinstance(t, dict) else None
        name = ""
        if isinstance(fn, dict):
            name = str(fn.get("name") or "").strip()
        if name in P1_BLOCKED_TOOL_NAMES:
            continue
        out.append(t)
    return out


def tier_denied_tool_json(tool_name: str) -> str:
    return json.dumps(
        {
            "error": "tier_denied",
            "tool": tool_name,
            "message": "P1 session: this tool is disabled. Enable developer mode and matching elevated token in Settings.",
        },
        ensure_ascii=False,
    )
