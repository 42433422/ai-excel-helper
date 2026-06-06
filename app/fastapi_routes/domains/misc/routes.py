"""
XCAGI 前端兼容 API — 系统 / 认证 / 偏好 / 工具目录等杂项路由。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, HTTPException, Query, Request

from app.domain.ai.tools_directory import get_tool_categories_payload, get_tools_payload
from app.infrastructure.auth.db_token import (
    configured_db_write_token,
    effective_db_read_token,
)
from app.infrastructure.db.sync_engine import (
    get_db_status,
    resolve_mode,
    switch_to_production_mode,
    switch_to_test_mode,
)

router = APIRouter(tags=["xcagi-compat"])
logger = logging.getLogger(__name__)


@router.post("/fhd/db-write-token/verify")
def fhd_db_write_token_verify(body: dict = Body(default_factory=dict)) -> dict:
    expected = configured_db_write_token()
    if not expected:
        return {"success": True, "valid": True, "write_token_required": False}
    tok = str(body.get("token") or "").strip()
    return {"success": True, "valid": tok == expected, "write_token_required": True}


@router.post("/fhd/db-read-token/verify")
def fhd_db_read_token_verify(request: Request, body: dict = Body(default_factory=dict)) -> dict:
    from app.fastapi_routes.domains.conversation.helpers import (
        _CHAT_DB_READ_GRACE_SEC,
        _touch_chat_db_read_grace,
    )

    expected = effective_db_read_token()
    if not expected:
        return {"success": True, "valid": True, "read_token_required": False, "grace_seconds": 0}
    tok = str(body.get("token") or "").strip()
    ok = tok == expected
    if ok:
        _touch_chat_db_read_grace(request)
    return {
        "success": True,
        "valid": ok,
        "read_token_required": True,
        "grace_seconds": _CHAT_DB_READ_GRACE_SEC if ok else 0,
    }


# 行业接口由 ``app.fastapi_routes.system_routes`` 提供（须在 xcagi_compat 之前注册）。
# 此处若再挂 ``/system/industry*`` 会与真实路由重复并在部分匹配顺序下导致 404。


@router.get("/system/openapi")
def system_openapi(request: Request) -> dict:
    return request.app.openapi()


def _test_db_toggle_from_body(body: dict) -> bool | None:
    for key in (
        "enabled",
        "enable",
        "on",
        "test_mode",
        "test_db_enabled",
        "testDbEnabled",
        "value",
    ):
        if key not in body:
            continue
        v = body[key]
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(int(v))
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("true", "1", "yes", "on"):
                return True
            if s in ("false", "0", "no", "off"):
                return False
    return None


def _compat_current_db_display_label(info: dict) -> str:
    mode = info["mode"]
    if info.get("backend") == "postgresql":
        summ = info.get("postgresql_summary") or {}
        dbn = str(summ.get("database_name") or "").strip()
        hp = str(summ.get("host_port") or "").strip()
        if dbn and hp:
            core = f"{dbn} @ {hp}"
        else:
            core = dbn or hp or "PostgreSQL"
        return f"{core}（PostgreSQL · 与 XCAGI / Mod 共用 DATABASE_URL）"
    return f"{info['current_db_name']}（{'测试' if mode == 'test' else '真实'}）"


@router.get("/system/test-db/status")
@router.get("/system/test-db/status/", include_in_schema=False)
def system_test_db_status() -> dict:
    info = get_db_status()
    mode = info["mode"]
    label = _compat_current_db_display_label(info)
    return {
        "success": True,
        "data": {
            "enabled": mode == "test",
            "test_mode": mode == "test",
            "test_db_enabled": mode == "test",
            "current_db_display": label,
            **info,
        },
    }


@router.post("/system/test-db/enable")
@router.post("/system/test-db/enable/", include_in_schema=False)
def system_test_db_enable(body: dict | None = Body(default=None)) -> dict:
    body = body if isinstance(body, dict) else {}
    want = _test_db_toggle_from_body(body)
    if want is None:
        want = resolve_mode() == "production"
    if want:
        result = switch_to_test_mode()
    else:
        result = switch_to_production_mode()
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result.get("message", str(result)))
    info = get_db_status()
    label = _compat_current_db_display_label(info)
    return {
        "success": True,
        "data": {
            "enabled": info["mode"] == "test",
            "test_mode": info["mode"] == "test",
            "test_db_enabled": info["mode"] == "test",
            "current_db_display": label,
            **info,
            "switch": result,
        },
    }


@router.post("/system/test-db/disable")
@router.post("/system/test-db/disable/", include_in_schema=False)
async def system_test_db_disable(body: dict | None = Body(default=None)) -> dict:
    merged: dict = dict(body) if isinstance(body, dict) else {}
    merged["enabled"] = False
    merged["test_db_enabled"] = False
    return system_test_db_enable(merged)


@router.get("/preferences")
@router.get("/preferences/", include_in_schema=False)
def preferences_get(user_id: str = Query(default="default")) -> dict:
    return {
        "success": True,
        "data": {"user_id": user_id, "preferences": {}},
    }


@router.post("/preferences")
@router.post("/preferences/", include_in_schema=False)
def preferences_post(body: dict = Body(default_factory=dict)) -> dict:
    return {"success": True, "data": body or {}}


@router.get("/distillation/versions")
@router.get("/distillation/versions/", include_in_schema=False)
def distillation_versions() -> dict:
    return {"success": True, "data": []}


def _intent_packages_list_payload() -> dict:
    return {"success": True, "data": []}


@router.get("/intent-packages", operation_id="compat_intent_packages_hyphen")
def compat_intent_packages_hyphen() -> dict:
    return _intent_packages_list_payload()


@router.get(
    "/intent-packages/", operation_id="compat_intent_packages_hyphen_slash", include_in_schema=False
)
def compat_intent_packages_hyphen_slash() -> dict:
    return _intent_packages_list_payload()


@router.get(
    "/intent_packages", operation_id="compat_intent_packages_underscore", include_in_schema=False
)
def compat_intent_packages_underscore() -> dict:
    return _intent_packages_list_payload()


@router.get(
    "/intent_packages/",
    operation_id="compat_intent_packages_underscore_slash",
    include_in_schema=False,
)
def compat_intent_packages_underscore_slash() -> dict:
    return _intent_packages_list_payload()


@router.get("/tools", summary="工具表目录（与 XCAGI ToolsView / pro-mode 对齐）")
@router.get("/tools/", summary="工具表目录（尾斜杠）", include_in_schema=False)
def compat_tools_list(role: str | None = Query(default=None)) -> dict:
    payload = get_tools_payload()
    if role:
        tools = payload.get("tools") or []
        filtered = [t for t in tools if not t.get("roles") or role in t.get("roles", [])]
        payload = {**payload, "tools": filtered}
    return payload


@router.get("/db-tools", summary="工具表目录别名（前端优先请求）")
@router.get("/db-tools/", summary="工具表目录别名（尾斜杠）", include_in_schema=False)
def compat_db_tools_list(role: str | None = Query(default=None)) -> dict:
    payload = get_tools_payload()
    if role:
        tools = payload.get("tools") or []
        filtered = [t for t in tools if not t.get("roles") or role in t.get("roles", [])]
        payload = {**payload, "tools": filtered}
    return payload


@router.get("/tool-categories", summary="工具分类列表")
@router.get("/tool-categories/", summary="工具分类列表（尾斜杠）", include_in_schema=False)
def compat_tool_categories_list() -> dict:
    return get_tool_categories_payload()


# /api/market/llm-catalog 仅由 app.fastapi_routes.market_account 提供（见 register_all_routes 中优先挂载）。
