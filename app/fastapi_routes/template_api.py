"""
XCAGI 前端使用的 Excel 模板列表等（GET /api/templates）。

FHD compact 栈（backend.http_app）不加载完整 XCAGI 时，至少避免 404；
若同进程可导入 ``app.application.template_app_service``，则返回真实列表，否则空列表。
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.neuro_bus.application_neuro_bridge import publish_neuro_event

logger = logging.getLogger(__name__)

router = APIRouter(tags=["templates-compat"])


def _templates_payload() -> dict:
    try:
        from app.application.template_app_service import get_template_app_service

        data = get_template_app_service().get_templates()
        return {"success": True, "templates": data.get("templates") or []}
    except Exception as e:
        logger.warning("template_api: 模板服务加载失败: %s", e)
        # 返回 503-compatible 错误结构；GET /api/templates 自身不抛异常，
        # 但调用方（前端）可通过 service_unavailable 字段判断需要告警。
        return {
            "success": False,
            "templates": [],
            "service_unavailable": True,
            "message": "模板服务暂时不可用，请刷新或联系管理员",
        }


def _find_template_row(template_id: str) -> dict[str, Any] | None:
    """按前端常用的 id / db_id / db:<n> 在列表结果中解析单条模板。"""
    raw = str(template_id or "").strip()
    if not raw:
        return None
    templates = _templates_payload().get("templates") or []
    if raw.startswith("db:"):
        for t in templates:
            if str((t or {}).get("id") or "") == raw:
                return t
        try:
            n = int(raw.split(":", 1)[1])
        except (ValueError, IndexError):
            n = None
        if n is not None:
            for t in templates:
                if (t or {}).get("db_id") == n:
                    return t
    if raw.isdigit():
        n = int(raw)
        for t in templates:
            if (t or {}).get("db_id") == n or str((t or {}).get("id") or "") == raw:
                return t
    for t in templates:
        if str((t or {}).get("id") or "") == raw:
            return t
    return None


def _publish_template_event(event_type: str, payload: dict[str, Any]) -> None:
    """发布模板相关事件到 NeuroBus"""
    try:
        publish_neuro_event(
            event_type,
            payload,
            domain="template",
        )
    except Exception:
        pass  # 静默失败，不影响主流程


@router.get("/api/templates/list", summary="模板列表（兼容旧路径 /api/templates/list）")
def templates_list_legacy_alias(request: Request):
    """与 GET /api/templates 相同，供仍使用 /list 后缀的前端使用。"""
    return templates_list_compat(request)


@router.get("/api/templates", summary="模板列表（兼容 XCAGI 前端）")
@router.get("/api/templates/", summary="模板列表（兼容 XCAGI 前端）", include_in_schema=False)
def templates_list_compat(request: Request):
    t0 = time.perf_counter()
    rid = str(getattr(request.state, "trace_id", None) or id(request))

    # 发布请求开始事件
    _publish_template_event(
        "template.request.started",
        {
            "request_id": rid,
            "path": str(request.url.path),
            "method": request.method,
            "client": request.client.host if request.client else None,
        },
    )

    try:
        result = _templates_payload()
        latency_ms = (time.perf_counter() - t0) * 1000.0

        # 发布请求完成事件
        _publish_template_event(
            "template.request.completed",
            {
                "request_id": rid,
                "path": str(request.url.path),
                "latency_ms": round(latency_ms, 3),
                "template_count": len(result.get("templates", [])),
                "success": result.get("success", False),
            },
        )
        from fastapi.responses import JSONResponse

        if result.get("service_unavailable"):
            return JSONResponse(result, status_code=503)
        return result
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000.0

        # 发布请求失败事件
        _publish_template_event(
            "template.request.failed",
            {
                "request_id": rid,
                "path": str(request.url.path),
                "latency_ms": round(latency_ms, 3),
                "error": str(e)[:300],
            },
        )
        raise


@router.get(
    "/api/templates/detail/{template_id}",
    summary="模板详情（兼容 /api/templates/detail/{id}）",
)
def templates_detail_compat(template_id: str):
    row = _find_template_row(template_id)
    if not row:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"success": True, "template": row}


@router.get("/api/templates/{template_id}", summary="模板详情（XCAGI：/api/templates/{id}）")
def templates_get_one(template_id: str):
    if template_id in {"list", "detail"}:
        raise HTTPException(status_code=404, detail="Not Found")
    row = _find_template_row(template_id)
    if not row:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"success": True, "template": row}
