from __future__ import annotations

import pytest
from fastapi import HTTPException, Request

from backend.ai_tier import (
    assert_p2_elevated_claim_or_raise,
    filter_tools_for_tier,
    resolve_ai_tier,
    runtime_context_with_tier,
)


def _req(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "path": "/api/ai/unified_chat",
        "raw_path": b"/api/ai/unified_chat",
        "root_path": "",
        "scheme": "http",
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": ("127.0.0.1", 1234),
        "server": ("test", 80),
    }
    return Request(scope)


def test_resolve_default_p1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FHD_AI_ELEVATED_TOKEN", raising=False)
    r = _req({})
    assert resolve_ai_tier(r) == "p1"


def test_resolve_p2_with_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FHD_AI_ELEVATED_TOKEN", "sekrit")
    r = _req({"x-xcagi-ai-tier": "p2", "x-xcagi-elevated-token": "sekrit"})
    assert resolve_ai_tier(r) == "p2"


def test_resolve_p2_bad_token_downgrades(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FHD_AI_ELEVATED_TOKEN", "sekrit")
    r = _req({"x-xcagi-ai-tier": "p2", "x-xcagi-elevated-token": "wrong"})
    assert resolve_ai_tier(r) == "p1"


def test_strict_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FHD_AI_ELEVATED_TOKEN", "sekrit")
    monkeypatch.setenv("FHD_AI_TIER_STRICT", "1")
    r = _req({"x-xcagi-ai-tier": "p2", "x-xcagi-elevated-token": "nope"})
    with pytest.raises(HTTPException) as ei:
        assert_p2_elevated_claim_or_raise(r)
    assert ei.value.status_code == 403


def test_filter_tools_p1() -> None:
    tools = [
        {"type": "function", "function": {"name": "excel_analysis", "description": "x"}},
        {"type": "function", "function": {"name": "products_bulk_import", "description": "y"}},
    ]
    out = filter_tools_for_tier(tools, "p1")
    names = [t["function"]["name"] for t in out]
    assert "excel_analysis" in names
    assert "products_bulk_import" not in names


def test_runtime_context_with_tier() -> None:
    d = runtime_context_with_tier({"a": 1}, "p2")
    assert d["a"] == 1
    assert d["_fhd_ai_tier"] == "p2"
