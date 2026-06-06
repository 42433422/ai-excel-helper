"""业务桩与未知 /api 兜底，避免沙盒里前端大量 404/500。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

_stubs = APIRouter(tags=["sandbox-mock"])
_fallback = APIRouter(tags=["sandbox-api-fallback"])


def _empty_list() -> dict[str, Any]:
    return {"data": [], "total": 0}


def _empty_data() -> dict[str, Any]:
    return {"data": []}


@_stubs.get("/api/health")
def sandbox_health():
    return {"status": "ok", "sandbox": True}


@_stubs.get("/api/products")
def mock_products():
    return _empty_list()


@_stubs.get("/api/product_names")
def mock_product_names():
    return _empty_list()


@_stubs.get("/api/purchase_units")
def mock_purchase_units():
    return _empty_list()


@_stubs.get("/api/orders")
def mock_orders():
    return _empty_data()


@_stubs.get("/api/shipment-records")
def mock_shipment_records():
    return _empty_data()


@_stubs.get("/api/materials")
def mock_materials():
    return _empty_data()


@_stubs.get("/api/printers")
def mock_printers():
    return _empty_data()


@_stubs.get("/api/templates")
def mock_templates():
    return _empty_data()


@_stubs.get("/api/wechat_contacts")
def mock_wechat_contacts():
    return _empty_data()


@_stubs.get("/api/tools")
def mock_tools():
    return _empty_data()


@_stubs.get("/api/intent-packages")
def mock_intent_packages():
    return _empty_data()


@_fallback.api_route("/api/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def sandbox_api_fallback(full_path: str, request: Request):
    if request.method == "OPTIONS":
        return Response(status_code=204)
    logger.debug("sandbox api stub: %s %s", request.method, request.url.path)
    return JSONResponse(
        {
            "success": True,
            "data": None,
            "sandbox": True,
            "missing_route": f"/api/{full_path}",
            "hint": "沙盒未挂载该接口；若 Mod 依赖请在生产 FHD 验证或扩展 sandbox 白名单。",
        }
    )


def mount_mock_routes(app) -> None:
    """先挂具体桩，最后不应单独调用 fallback——fallback 由 app_factory 最后挂载。"""
    app.include_router(_stubs)


def mount_api_fallback_last(app) -> None:
    """必须在所有真实 /api 路由之后注册。"""
    app.include_router(_fallback)
