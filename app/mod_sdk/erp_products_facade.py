# -*- coding: utf-8 -*-
"""里程碑 G+：产品 CRUD 统一经 ``ProductsService``（Mod handler 与宿主 compat 共用）。"""

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


def is_erp_products_via_service_enabled() -> bool:
    if _truthy_env("XCAGI_DISABLE_ERP_PRODUCTS_VIA_SERVICE"):
        return False
    if _truthy_env("XCAGI_ERP_PRODUCTS_VIA_SERVICE"):
        return True
    cfg = _read_manifest().get("config") or {}
    if isinstance(cfg, dict) and cfg.get("products_via_service") is True:
        return True
    return False


def _service():
    from app.bootstrap import get_products_service

    return get_products_service()


def _map_create_body(body: dict[str, Any]) -> dict[str, Any]:
    from app.application.excel_imports import _norm_model

    name = str(body.get("name") or "").strip()
    spec = str(body.get("specification") or "").strip()
    mn = str(body.get("model_number") or body.get("product_code") or "").strip()
    if not mn:
        mn = _norm_model("", name, spec)
    price = body.get("unit_price", body.get("price", 0))
    return {
        "name": name,
        "specification": spec,
        "product_code": mn,
        "unit_price": price,
        "quantity": body.get("quantity", 0),
        "unit": str(body.get("unit") or "个").strip() or "个",
        "description": body.get("description") or "",
        "category": body.get("category") or "",
        "brand": body.get("brand") or "",
    }


def _write_gate(request: Request | None) -> dict | None:
    from app.fastapi_routes.xcagi_compat_db_base import (
        _business_mod_json_block,
        _products_write_raise,
    )

    if request is not None:
        _products_write_raise(request)
    return _business_mod_json_block()


def products_list(
    request: Request | None = None,
    *,
    page: int = 1,
    per_page: int = 20,
    keyword: str | None = None,
    unit: str | None = None,
) -> dict[str, Any]:
    from app.infrastructure.auth.db_token import verify_db_read_token_header

    if request is not None:
        verify_db_read_token_header(request)
    out = _service().get_products(
        unit_name=unit,
        keyword=keyword,
        page=page,
        per_page=per_page,
    )
    if not out.get("success"):
        return {
            "success": False,
            "message": out.get("message", "查询失败"),
            "data": [],
            "total": 0,
        }
    payload: dict[str, Any] = {
        "success": True,
        "data": out.get("data") or [],
        "total": int(out.get("total") or 0),
    }
    payload["source"] = f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}"
    payload["execution_path"] = "products_service"
    from app.mod_sdk.erp_repository_registry import get_repository_execution_meta

    payload.update(get_repository_execution_meta("products"))
    return payload


def products_get(request: Request, product_id: int) -> dict | JSONResponse:
    from app.fastapi_routes.miniprogram import (
        _mp_json,
        build_mp_product_detail_response,
        classify_miniprogram_bearer,
    )
    from app.infrastructure.auth.db_token import verify_db_read_token_header

    kind, _ = classify_miniprogram_bearer(request.headers.get("Authorization"))
    if kind == "ok":
        return build_mp_product_detail_response(product_id)
    if kind == "invalid":
        return _mp_json(401, "token 无效或已过期", {"error": "invalid_token"}, success=False)

    verify_db_read_token_header(request)
    result = _service().get_product(product_id)
    if result.get("success"):
        data = result.get("data")
        if hasattr(data, "to_dict"):
            result = {**result, "data": data.to_dict()}
        result["source"] = f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}"
        result["execution_path"] = "products_service"
        return result
    return JSONResponse(result, status_code=404)


def products_add(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    gate = _write_gate(request)
    if gate:
        return gate
    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="产品名称不能为空")
    result = _service().create_product(_map_create_body(body))
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message") or "添加失败")
    data = result.get("data") or {}
    pid = data.get("id") if isinstance(data, dict) else getattr(data, "id", None)
    return {
        "success": True,
        "data": {"id": int(pid) if pid is not None else None},
        "source": f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}",
        "execution_path": "products_service",
    }


def products_update(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    from app.fastapi_routes.xcagi_compat_db_base import _product_parse_id

    gate = _write_gate(request)
    if gate:
        return gate
    pid = _product_parse_id(body.get("id"))
    if pid is None:
        raise HTTPException(status_code=400, detail="id 无效或缺失")
    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="产品名称不能为空")
    payload = dict(body)
    payload.pop("id", None)
    result = _service().update_product(pid, payload)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message") or "产品不存在")
    return {
        "success": True,
        "data": {"id": pid},
        "source": f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}",
        "execution_path": "products_service",
    }


def products_delete(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    from app.fastapi_routes.xcagi_compat_db_base import _product_parse_id

    gate = _write_gate(request)
    if gate:
        return gate
    pid = _product_parse_id(body.get("id"))
    if pid is None:
        raise HTTPException(status_code=400, detail="id 无效或缺失")
    result = _service().delete_product(pid)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message") or "产品不存在")
    return {
        "success": True,
        "message": result.get("message") or "已删除",
        "source": f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}",
        "execution_path": "products_service",
    }


def products_batch_delete(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    from app.fastapi_routes.xcagi_compat_db_base import _product_parse_id

    gate = _write_gate(request)
    if gate:
        return gate
    raw_ids = body.get("ids") or body.get("product_ids") or []
    if not isinstance(raw_ids, list) or not raw_ids:
        raise HTTPException(status_code=400, detail="ids 须为非空数组")
    int_ids: list[int] = []
    skipped: list[str] = []
    for raw in raw_ids:
        pid = _product_parse_id(raw)
        if pid is None:
            skipped.append(str(raw))
        else:
            int_ids.append(pid)
    if not int_ids:
        raise HTTPException(status_code=400, detail="无有效产品 id")
    result = _service().batch_delete_products(int_ids)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message") or "批量删除失败")
    deleted = int(
        result.get("deleted_count")
        or (result.get("data") or {}).get("deleted_count")
        or len(int_ids)
    )
    return {
        "success": True,
        "message": f"已删除 {deleted} 条",
        "deleted": deleted,
        "skipped": skipped,
        "source": f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}",
        "execution_path": "products_service",
    }


def products_product_names(keyword: str = "") -> dict[str, Any]:
    out = _service().get_product_names(keyword=keyword or None)
    out["source"] = f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}"
    out["execution_path"] = "products_service"
    return out


def products_batch(body: dict[str, Any]) -> dict[str, Any]:
    products = body.get("products") or []
    if not isinstance(products, list) or not products:
        return {"success": False, "message": "products 必须为非空数组"}
    mapped = [_map_create_body(p) if isinstance(p, dict) else p for p in products]
    out = _service().batch_add_products(mapped)
    out["source"] = f"mod:{ERP_DOMAIN_BRIDGE_MOD_ID}"
    out["execution_path"] = "products_service"
    return out


__all__ = [
    "is_erp_products_via_service_enabled",
    "products_add",
    "products_batch",
    "products_batch_delete",
    "products_delete",
    "products_get",
    "products_list",
    "products_product_names",
    "products_update",
]
