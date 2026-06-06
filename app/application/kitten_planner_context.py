"""Enrich planner/runtime context for 小猫分析 (Kitten) before legacy_chat_adapter.chat."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _session_key_from_context(rc: dict[str, Any]) -> str:
    raw = str(rc.get("kitten_session_id") or rc.get("session_id") or "").strip()
    if raw:
        return raw[:128]
    blob = str(rc.get("kitten_dataset") or "")[:2000]
    return hashlib.sha256(blob.encode("utf-8", errors="ignore")).hexdigest()[:24]


async def enrich_kitten_analyzer_runtime(
    runtime_context: dict[str, Any] | None,
    message: str,
) -> dict[str, Any]:
    """业务库快照 + 联网检索写入 runtime_context，供 merge_system_prompt 使用。"""
    rc = dict(runtime_context or {})
    if not rc.get("kitten_analyzer"):
        return rc

    if rc.get("kitten_include_business_db"):
        try:
            from app.services.kitten_business_snapshot import build_kitten_business_snapshot

            rc["kitten_business_snapshot"] = build_kitten_business_snapshot()
        except Exception as exc:
            logger.warning("kitten business snapshot (planner): %s", exc)
            rc["kitten_business_snapshot"] = {
                "success": False,
                "text": f"【业务数据库快照】生成失败：{exc}",
                "stats": {},
            }
    else:
        rc.pop("kitten_business_snapshot", None)

    if rc.get("kitten_web_search"):
        try:
            from app.infrastructure.web_search import kitten_web_search

            sk = _session_key_from_context(rc)
            result = await kitten_web_search((message or "").strip(), user_key=sk)
            rc["web_search_results"] = result.get("hits") if result.get("success") else []
            rc["web_search_meta"] = {
                "provider": result.get("provider"),
                "query": result.get("query"),
            }
            if not result.get("success"):
                rc["web_search_error"] = result.get("message") or "search failed"
            else:
                rc.pop("web_search_error", None)
        except Exception as exc:
            logger.warning("kitten web search (planner): %s", exc)
            rc["web_search_results"] = []
            rc["web_search_error"] = str(exc)
    else:
        rc.pop("web_search_results", None)
        rc.pop("web_search_meta", None)
        rc.pop("web_search_error", None)

    return rc


def kitten_reply_attachments(runtime_context: dict[str, Any] | None) -> dict[str, Any]:
    """挂到 _xcagi_compat_reply_payload 的 data 上，供前端导出与引用展示。"""
    rc = runtime_context or {}
    if not rc.get("kitten_analyzer"):
        return {}
    out: dict[str, Any] = {
        "web_search_results": list(rc.get("web_search_results") or []),
    }
    meta = rc.get("web_search_meta")
    if isinstance(meta, dict) and meta:
        out["web_search_meta"] = meta
    err = rc.get("web_search_error")
    if err:
        out["web_search_error"] = str(err)[:500]
    return out
