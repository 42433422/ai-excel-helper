"""Qclaw 路由与运行时状态。

Phase 2C 从 :mod:`app.fastapi_routes.archive_gap_batch1/2` 拆分而出,URL 保持不变:

- ``GET /api/ai/qclaw/routes`` / ``GET /api/ai/qclaw/panel``
- ``POST /api/ai/qclaw/wechat-gateway``
- ``POST /api/ai/qclaw/openclaw/config``
- ``POST /api/ai/qclaw/whitelist``
- ``POST /api/ai/qclaw/test-route``
- ``POST /api/ai/qclaw/openclaw/chat``

``_QCLOW_RUNTIME_STATE`` 原位于 ``archive_gap_batch1``,现统一搬迁至本模块,
其余仍需访问它的 batch2 代码(wechat 相关)通过 ``from app.fastapi_routes.ai_qclaw
import _QCLOW_RUNTIME_STATE`` 导入。
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai-qclaw"])


_QCLOW_RUNTIME_STATE: dict[str, Any] = {
    "wechat_open": True,
    "openclaw_base": "http://localhost:28789",
    "whitelist": {
        "/api/ai/chat": True,
        "/api/ai/unified_chat": True,
        "/api/wechat_contacts": True,
        "/api/shipment/orders": True,
        "/api/print/printers": True,
    },
}


@router.get("/api/ai/qclaw/routes")
def ai_qclaw_routes():
    return {
        "success": True,
        "source": "qclaw",
        "permissions": {
            "normal_routes": [
                "/api/ai/unified_chat",
                "/api/tools/execute",
                "/api/products/*",
                "/api/customers/*",
                "/api/materials/*",
            ],
            "pro_routes": [
                "/api/ai/chat",
                "/api/ai/chat/stream",
                "/api/wechat/*",
                "/api/wechat_contacts/*",
                "/api/shipment/*",
                "/api/print/*",
            ],
        },
        "note": "Qclaw 来源允许同时访问普通版与专业版主链路。",
    }


@router.get("/api/ai/qclaw/panel")
def ai_qclaw_panel():
    whitelist = _QCLOW_RUNTIME_STATE.get("whitelist", {})
    routes = [{"path": path, "enabled": bool(enabled)} for path, enabled in whitelist.items()]
    return {
        "success": True,
        "wechat_open": bool(_QCLOW_RUNTIME_STATE.get("wechat_open", False)),
        "openclaw_base": str(_QCLOW_RUNTIME_STATE.get("openclaw_base", "http://127.0.0.1:28789")),
        "routes": routes,
    }


@router.post("/api/ai/qclaw/wechat-gateway")
def ai_qclaw_wechat_gateway(body: dict = Body(default_factory=dict)):
    enabled = bool(body.get("enabled", False))
    _QCLOW_RUNTIME_STATE["wechat_open"] = enabled
    return {"success": True, "wechat_open": enabled}


@router.post("/api/ai/qclaw/openclaw/config")
def ai_qclaw_openclaw_config(body: dict = Body(default_factory=dict)):
    base_url = str(body.get("base_url") or "").strip().rstrip("/")
    if not base_url:
        return JSONResponse({"success": False, "message": "base_url 不能为空"}, status_code=400)
    _QCLOW_RUNTIME_STATE["openclaw_base"] = base_url
    return {"success": True, "openclaw_base": base_url}


@router.post("/api/ai/qclaw/whitelist")
def ai_qclaw_whitelist(body: dict = Body(default_factory=dict)):
    path = str(body.get("path") or "").strip()
    enabled = bool(body.get("enabled", False))
    if not path:
        return JSONResponse({"success": False, "message": "path 不能为空"}, status_code=400)
    whitelist = _QCLOW_RUNTIME_STATE.setdefault("whitelist", {})
    whitelist[path] = enabled
    return {"success": True, "path": path, "enabled": enabled}


@router.post("/api/ai/qclaw/test-route")
def ai_qclaw_test_route(request: Request, body: dict = Body(default_factory=dict)):
    path = str(body.get("path") or "").strip()
    method = str(body.get("method") or "GET").upper()
    if not path:
        return JSONResponse({"success": False, "message": "path 不能为空"}, status_code=400)
    whitelist = _QCLOW_RUNTIME_STATE.get("whitelist", {})
    if not bool(whitelist.get(path, False)):
        return JSONResponse({"success": False, "message": "该路由未在白名单启用"}, status_code=403)
    try:
        client = TestClient(request.app)
        if method == "POST":
            resp = client.post(path, json={"source": "qclaw", "message": "smoke"})
        else:
            resp = client.get(path)
        ok = resp.status_code < 500
        return {
            "success": True,
            "path": path,
            "method": method,
            "status_code": resp.status_code,
            "result": "ok" if ok else "error",
        }
    except Exception as err:
        return JSONResponse(
            {"success": False, "path": path, "method": method, "message": str(err)},
            status_code=500,
        )


@router.post("/api/ai/qclaw/openclaw/chat")
def ai_qclaw_openclaw_chat(body: dict = Body(default_factory=dict)):
    message = str(body.get("message") or "").strip()
    if not message:
        return JSONResponse({"success": False, "message": "message 不能为空"}, status_code=400)
    base = str(_QCLOW_RUNTIME_STATE.get("openclaw_base", "http://localhost:28789")).rstrip("/")
    target_url = f"{base}/api/chat"
    payload = json.dumps({"message": message}).encode("utf-8")
    req = urllib.request.Request(
        target_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw) if raw else {}
            except Exception:
                parsed = {"raw": raw}
            return {"success": True, "target": target_url, "data": parsed}
    except urllib.error.HTTPError as err:
        b = err.read().decode("utf-8", errors="replace")
        return JSONResponse(
            {
                "success": False,
                "target": target_url,
                "status_code": err.code,
                "message": b or str(err),
            },
            status_code=502,
        )
    except Exception as err:
        return JSONResponse(
            {"success": False, "target": target_url, "message": str(err)}, status_code=502
        )
