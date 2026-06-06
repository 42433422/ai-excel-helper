"""
XCAGI 前端兼容 API — 客户管理路由。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from app.fastapi_routes.domains.db.base import (
    _business_mod_json_block,
    _customer_body_name_contact,
    _customers_write_raise,
)
from app.fastapi_routes.domains.db.queries import (
    _customer_find_by_id,
    _customer_row_for_api,
    _customer_row_matches_keyword,
    _customers_schema_hint_if_empty,
    _load_customers_rows,
)
from app.fastapi_routes.domains.db.writes import (
    _customer_delete_unified,
    _customer_pg_insert,
    _customer_pg_update,
)
from app.infrastructure.auth.db_token import verify_db_read_token_header
from app.neuro_bus.route_event_publisher import (
    RouteEvents,
    publish_route_event,
    publish_simple_event,
)

router = APIRouter(tags=["xcagi-compat"])
logger = logging.getLogger(__name__)


@router.get("/customers", response_model=None)
@router.get("/customers/", response_model=None, include_in_schema=False)
@publish_route_event(RouteEvents.DB_QUERY, domain="customers")
def customers_all(
    request: Request,
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=500),
) -> dict | JSONResponse:
    return {"success": True, "data": _load_customers_rows()}


@router.get("/customers/match")
@router.get("/customers/match/", include_in_schema=False)
def customers_match(
    customer_name: str | None = Query(None, description="已抽取的客户名或片段"),
    context: str | None = Query(
        None, description="可选：本轮用户原始话术，供 extract_customer_name"
    ),
) -> dict:
    from app.infrastructure.products.customer_matching import (
        extract_customer_name,
        find_matching_customer,
    )

    field = (customer_name or "").strip()
    ctx = (context or "").strip()
    if not field and not ctx:
        return {"success": True, "matched": None, "input": "", "extracted": None, "display": None}

    if _business_mod_json_block():
        return {
            "success": True,
            "matched": None,
            "input": field or ctx,
            "extracted": None,
            "display": None,
        }

    extracted = extract_customer_name(field) or extract_customer_name(ctx)
    if extracted:
        matched = find_matching_customer(extracted)
    else:
        matched = find_matching_customer(field or ctx)

    chosen = (matched or "").strip()
    base = field or ctx
    display = chosen or base
    return {
        "success": True,
        "input": base,
        "extracted": extracted,
        "matched": chosen or None,
        "display": display,
    }


@router.get("/customers/list")
def customers_list(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=2000),
    keyword: str | None = Query(None, description="按名称、电话、地址等子串过滤（大小写不敏感）"),
) -> dict:
    try:
        from app.mod_sdk.client_primary_erp import try_invoke_client_mod_customers_list

        client_out = try_invoke_client_mod_customers_list(
            request=request,
            page=page,
            per_page=per_page,
            keyword=keyword,
        )
        if client_out is not None:
            return client_out
    except Exception:
        logger.debug("client mod customers.list skipped", exc_info=True)
    try:
        from app.mod_sdk.client_primary_erp import resolve_client_erp_mod_for_request
        from app.mod_sdk.erp_domain_dispatch import try_invoke_erp_domain_handler
        from app.request_active_mod_ctx import get_request_active_mod_id, parse_active_mod_header

        active = get_request_active_mod_id()
        if not active and request is not None:
            active = parse_active_mod_header(request.headers)
        if not resolve_client_erp_mod_for_request(active):
            mod_out = try_invoke_erp_domain_handler(
                "customers",
                "list",
                request=request,
                page=page,
                per_page=per_page,
                keyword=keyword,
            )
            if mod_out is not None:
                return mod_out
    except Exception:
        logger.debug("erp domain customers.list dispatch skipped", exc_info=True)
    try:
        from app.mod_sdk.erp_customers_facade import customers_list as customers_list_via_service
        from app.mod_sdk.erp_customers_facade import (
            is_erp_customers_via_service_enabled,
        )

        if is_erp_customers_via_service_enabled():
            return customers_list_via_service(
                request, page=page, per_page=per_page, keyword=keyword
            )
    except Exception:
        logger.debug("customers list via service skipped", exc_info=True)
    verify_db_read_token_header(request)
    rows = _load_customers_rows()
    kw = (keyword or "").strip()
    if kw:
        rows = [r for r in rows if _customer_row_matches_keyword(r, kw)]
    total = len(rows)
    offset = (page - 1) * per_page
    out = {
        "success": True,
        "data": rows[offset : offset + per_page],
        "total": total,
    }
    if total == 0:
        ch = _customers_schema_hint_if_empty()
        if ch:
            out["schema_hint"] = ch
    return out


@router.get("/customers/{customer_id}", response_model=None)
@router.get("/customers/{customer_id}/", response_model=None, include_in_schema=False)
def customers_get_one(request: Request, customer_id: int) -> dict | JSONResponse:
    try:
        from app.mod_sdk.erp_customers_facade import customers_get as customers_get_via_service
        from app.mod_sdk.erp_customers_facade import (
            is_erp_customers_via_service_enabled,
        )

        if is_erp_customers_via_service_enabled():
            return customers_get_via_service(request, customer_id)
    except Exception:
        logger.debug("customers get via service skipped", exc_info=True)
    row = _customer_find_by_id(customer_id)
    if not row:
        raise HTTPException(status_code=404, detail="客户不存在")
    return {"success": True, "data": _customer_row_for_api(row)}


@router.post("/customers")
@router.post("/customers/", include_in_schema=False)
@publish_route_event(RouteEvents.DB_QUERY, domain="customers")
def customers_create(request: Request, body: dict = Body(default_factory=dict)) -> dict:
    try:
        from app.mod_sdk.erp_customers_facade import (
            customers_create as customers_create_via_service,
        )
        from app.mod_sdk.erp_customers_facade import (
            is_erp_customers_via_service_enabled,
        )

        if is_erp_customers_via_service_enabled():
            return customers_create_via_service(request, body)
    except HTTPException:
        raise
    except Exception:
        logger.debug("customers create via service skipped", exc_info=True)
    _customers_write_raise(request)
    name, cp, ph, addr = _customer_body_name_contact(body)
    if not name:
        raise HTTPException(status_code=400, detail="客户名称不能为空")
    data = _customer_pg_insert(name, cp, ph, addr)

    publish_simple_event(
        "customer.created",
        {
            "customer_id": data.get("id") if isinstance(data, dict) else None,
            "customer_name": name,
        },
        domain="customers",
    )

    return {"success": True, "data": data}


@router.put("/customers/{customer_id}")
@router.put("/customers/{customer_id}/", include_in_schema=False)
def customers_update(
    request: Request, customer_id: int, body: dict = Body(default_factory=dict)
) -> dict:
    try:
        from app.mod_sdk.erp_customers_facade import (
            customers_update as customers_update_via_service,
        )
        from app.mod_sdk.erp_customers_facade import (
            is_erp_customers_via_service_enabled,
        )

        if is_erp_customers_via_service_enabled():
            return customers_update_via_service(request, customer_id, body)
    except HTTPException:
        raise
    except Exception:
        logger.debug("customers update via service skipped", exc_info=True)
    _customers_write_raise(request)
    name, cp, ph, addr = _customer_body_name_contact(body)
    if not name:
        raise HTTPException(status_code=400, detail="客户名称不能为空")
    data = _customer_pg_update(customer_id, name, cp, ph, addr)
    return {"success": True, "data": data}


@router.delete("/customers/{customer_id}")
@router.delete("/customers/{customer_id}/", include_in_schema=False)
def customers_delete(request: Request, customer_id: int) -> dict:
    try:
        from app.mod_sdk.erp_customers_facade import (
            customers_delete as customers_delete_via_service,
        )
        from app.mod_sdk.erp_customers_facade import (
            is_erp_customers_via_service_enabled,
        )

        if is_erp_customers_via_service_enabled():
            return customers_delete_via_service(request, customer_id)
    except HTTPException:
        raise
    except Exception:
        logger.debug("customers delete via service skipped", exc_info=True)
    _customers_write_raise(request)
    _customer_delete_unified(customer_id)
    return {"success": True, "message": "已删除"}


@router.post("/customers/batch-delete")
@router.post("/customers/batch-delete/", include_in_schema=False)
def customers_batch_delete(request: Request, body: dict = Body(default_factory=dict)) -> dict:
    _customers_write_raise(request)
    ids = body.get("ids") or body.get("customer_ids") or []
    if not isinstance(ids, list) or not ids:
        raise HTTPException(status_code=400, detail="ids 须为非空数组")
    deleted = 0
    errors: list[str] = []
    for raw in ids:
        try:
            cid = int(raw)
        except (TypeError, ValueError):
            errors.append(str(raw))
            continue
        try:
            _customer_delete_unified(cid)
            deleted += 1
        except HTTPException as e:
            if e.status_code == 404:
                errors.append(str(cid))
            else:
                raise
    return {
        "success": True,
        "message": f"已删除 {deleted} 条",
        "deleted": deleted,
        "skipped": errors,
    }


@router.post("/customers/import")
@router.post("/customers/import/", include_in_schema=False)
async def customers_import(request: Request, file: UploadFile = File(...)) -> dict:
    _customers_write_raise(request)
    gate = _business_mod_json_block()
    if gate:
        return gate
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取上传文件失败：{e}") from e
    from app.application.excel_imports import run_customers_excel_import_bytes

    out = run_customers_excel_import_bytes(content)
    if not out.get("success"):
        msg = str(out.get("message") or out.get("error") or "导入失败")
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "data": out}


@router.get("/customers/export")
@router.get("/customers/export/", include_in_schema=False)
def customers_export_stub() -> dict:
    raise HTTPException(
        status_code=501,
        detail="客户 Excel 导出尚未在 FastAPI 兼容层实现；请接回 XCAGI 全量后端或使用本地模板导出。",
    )
