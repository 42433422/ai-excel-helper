# -*- coding: utf-8 -*-
"""里程碑 G+c：客户 CRUD 统一经 ``CustomerApplicationService``。"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.mod_sdk.erp_domain_compat import ERP_DOMAIN_BRIDGE_MOD_ID, _read_manifest

logger = logging.getLogger(__name__)


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def is_erp_customers_via_service_enabled() -> bool:
    if _truthy_env("XCAGI_DISABLE_ERP_CUSTOMERS_VIA_SERVICE"):
        return False
    if _truthy_env("XCAGI_ERP_CUSTOMERS_VIA_SERVICE"):
        return True
    cfg = _read_manifest().get("config") or {}
    if isinstance(cfg, dict) and cfg.get("customers_via_service") is True:
        return True
    return False


def _service():
    from app.bootstrap import get_customer_app_service

    return get_customer_app_service()


def _map_body(body: dict[str, Any]) -> dict[str, Any]:
    from app.fastapi_routes.xcagi_compat_db_base import _customer_body_name_contact

    name, cp, ph, addr = _customer_body_name_contact(body)
    return {
        "customer_name": name,
        "contact_person": cp or "",
        "contact_phone": ph or "",
        "contact_address": addr or "",
    }


def _write_gate(request: Request | None) -> None:
    from app.fastapi_routes.xcagi_compat_db_base import _customers_write_raise

    if request is not None:
        _customers_write_raise(request)


def _stamp(out: dict[str, Any]) -> dict[str, Any]:
    from app.mod_sdk.erp_repository_registry import get_repository_execution_meta

    out["source"] = f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}"
    out["execution_path"] = "customers_service"
    out.update(get_repository_execution_meta("customers"))
    return out


def customers_list(
    request: Request | None = None,
    *,
    page: int = 1,
    per_page: int = 20,
    keyword: str | None = None,
) -> dict[str, Any]:
    from app.infrastructure.auth.db_token import verify_db_read_token_header

    if request is not None:
        verify_db_read_token_header(request)
    out = _service().get_all(keyword=keyword, page=page, per_page=per_page)
    if not out.get("success"):
        return _stamp(
            {
                "success": False,
                "message": out.get("message", "查询失败"),
                "data": [],
                "total": 0,
            }
        )
    return _stamp(
        {
            "success": True,
            "data": out.get("data") or [],
            "total": int(out.get("total") or 0),
        }
    )


def customers_get(request: Request, customer_id: int) -> dict | JSONResponse:
    from app.fastapi_routes.miniprogram import (
        _mp_json,
        build_mp_customer_detail_response,
        classify_miniprogram_bearer,
    )
    from app.infrastructure.auth.db_token import verify_db_read_token_header

    kind, _ = classify_miniprogram_bearer(request.headers.get("Authorization"))
    if kind == "ok":
        return build_mp_customer_detail_response(customer_id)
    if kind == "invalid":
        return _mp_json(401, "token 无效或已过期", {"error": "invalid_token"}, success=False)

    verify_db_read_token_header(request)
    result = _service().get_by_id(customer_id)
    if result.get("success"):
        return _stamp(result)
    return JSONResponse(result, status_code=404)


def customers_create(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    from app.neuro_bus.route_event_publisher import publish_simple_event

    _write_gate(request)
    mapped = _map_body(body)
    if not mapped.get("customer_name"):
        raise HTTPException(status_code=400, detail="客户名称不能为空")
    result = _service().create(mapped)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message") or "创建失败")
    data = result.get("data") or {}
    publish_simple_event(
        "customer.created",
        {
            "customer_id": data.get("id") if isinstance(data, dict) else None,
            "customer_name": mapped.get("customer_name"),
        },
        domain="customers",
    )
    return _stamp({"success": True, "data": data})


def customers_update(request: Request, customer_id: int, body: dict[str, Any]) -> dict[str, Any]:
    _write_gate(request)
    mapped = _map_body(body)
    if not mapped.get("customer_name"):
        raise HTTPException(status_code=400, detail="客户名称不能为空")
    result = _service().update(customer_id, mapped)
    if not result.get("success"):
        status = 404 if "不存在" in str(result.get("message") or "") else 400
        raise HTTPException(status_code=status, detail=result.get("message") or "更新失败")
    return _stamp({"success": True, "data": result.get("data")})


def customers_delete(request: Request, customer_id: int) -> dict[str, Any]:
    _write_gate(request)
    result = _service().delete(customer_id, force=False)
    if not result.get("success"):
        msg = str(result.get("message") or "删除失败")
        status = 404 if "不存在" in msg else 400
        raise HTTPException(status_code=status, detail=msg)
    return _stamp({"success": True, "message": result.get("message") or "已删除"})


__all__ = [
    "customers_create",
    "customers_delete",
    "customers_get",
    "customers_list",
    "customers_update",
    "is_erp_customers_via_service_enabled",
]
