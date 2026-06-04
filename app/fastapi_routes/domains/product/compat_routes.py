"""
XCAGI 前端兼容 API — 产品 / 库存 / 报价表导出路由。
"""

from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.infrastructure.auth.db_token import verify_db_read_token_header
from app.infrastructure.db.sync_engine import get_sync_engine
from app.shell.mod_row_scope import (
    append_mod_scope_where,
    products_update_or_delete_mod_and,
    scoped_mod_id,
)

from app.fastapi_routes.domains.db.base import (
    _EXPORT_MAX_ROWS,
    _business_mod_json_block,
    _product_parse_id,
    _product_parse_is_active,
    _product_parse_quantity,
    _products_write_raise,
    _sql_ident,
)
from app.fastapi_routes.domains.db.product_queries import (
    _load_products_all_for_export,
    _load_products_list_impl_pg,
)
from app.fastapi_routes.domains.db.queries import (
    _distinct_units_from_products_db,
    _merged_purchase_unit_entries,
    _products_units_for_select,
)

router = APIRouter(tags=["xcagi-compat"])
logger = logging.getLogger(__name__)


def _products_price_list_word_response(
    unit: str | None,
    keyword: str | None,
    export_date: str | None,
    template_slug: str | None = None,
) -> Response:
    from app.infrastructure.documents.price_list_export import (
        build_price_list_docx_bytes,
        resolve_price_list_docx_template,
    )

    from app.shell.mod_business_scope import business_data_exposed, business_data_hidden_reason

    if not business_data_exposed():
        raise HTTPException(
            status_code=503,
            detail=business_data_hidden_reason() or "扩展 Mod 未就绪，无法导出价格表。",
        )
    tpl_path, tpl_rel = resolve_price_list_docx_template(template_slug)
    if not tpl_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                "未找到 Word 模板文件："
                f"{tpl_rel}。请将 .docx 放到 424/document_templates/（如 price_list_default.docx），"
                "或在「模板预览」中登记，或设置环境变量 FHD_PRICE_LIST_DOCX_TEMPLATE。"
            ),
        )
    rows = _load_products_all_for_export(keyword, unit)
    customer = (unit or "").strip()
    qd = (export_date or "").strip() or date.today().strftime("%Y-%m-%d")
    try:
        body = build_price_list_docx_bytes(
            tpl_path,
            customer_name=customer,
            quote_date=qd,
            products=rows,
        )
    except Exception as e:
        logger.exception("products export docx failed")
        raise HTTPException(status_code=500, detail=f"生成 Word 失败：{e}") from e

    today = date.today().strftime("%Y-%m-%d")
    label = customer or "全部单位"
    utf8_name = f"产品价格表_{label}_{today}.docx"
    disp = "attachment; filename=\"price-list.docx\"; filename*=UTF-8''" + quote(utf8_name, safe="")
    return Response(
        content=body,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": disp},
    )


@router.get("/products/units")
def products_units(request: Request) -> dict:
    verify_db_read_token_header(request)
    return _products_units_for_select()


@router.get("/shipment/shipment-records/units")
@router.get("/shipment/shipment-records/units/", include_in_schema=False)
def shipment_records_units() -> dict:
    return _products_units_for_select()


@router.get("/purchase_units")
@router.get("/purchase_units/", include_in_schema=False)
def purchase_units_list() -> dict:
    return {"success": True, "data": _merged_purchase_unit_entries()}


@router.get("/products/list")
def products_list(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=2000),
    keyword: str | None = Query(None),
    unit: str | None = Query(None),
) -> dict:
    try:
        from app.mod_sdk.erp_domain_dispatch import try_invoke_erp_domain_handler

        mod_out = try_invoke_erp_domain_handler(
            "products",
            "list",
            request=request,
            page=page,
            per_page=per_page,
            keyword=keyword,
            unit=unit,
        )
        if mod_out is not None:
            return mod_out
    except Exception:
        logger.debug("erp domain products.list dispatch skipped", exc_info=True)
    try:
        from app.mod_sdk.erp_products_facade import (
            is_erp_products_via_service_enabled,
            products_list as products_list_via_service,
        )

        if is_erp_products_via_service_enabled():
            return products_list_via_service(
                request, page=page, per_page=per_page, keyword=keyword, unit=unit
            )
    except Exception:
        logger.debug("products list via service skipped", exc_info=True)
    verify_db_read_token_header(request)
    try:
        items, total, schema_hint = _load_products_list_impl_pg(page, per_page, keyword, unit)
        out: dict = {"success": True, "data": items, "total": total}
        if schema_hint:
            out["schema_hint"] = schema_hint
        return out
    except Exception as e:
        logger.exception("products list failed (postgresql)")
        return {"success": False, "message": str(e), "data": [], "total": 0}


@router.get("/products/{product_id:int}", response_model=None)
@router.get("/products/{product_id:int}/", response_model=None, include_in_schema=False)
def products_get_by_id(request: Request, product_id: int) -> dict | JSONResponse:
    from app.fastapi_routes.miniprogram import (
        _mp_json,
        build_mp_product_detail_response,
        classify_miniprogram_bearer,
    )

    kind, _ = classify_miniprogram_bearer(request.headers.get("Authorization"))
    if kind == "ok":
        return build_mp_product_detail_response(product_id)
    if kind == "invalid":
        return _mp_json(401, "token 无效或已过期", {"error": "invalid_token"}, success=False)

    try:
        from app.mod_sdk.erp_products_facade import (
            is_erp_products_via_service_enabled,
            products_get as products_get_via_service,
        )

        if is_erp_products_via_service_enabled():
            return products_get_via_service(request, product_id)
    except Exception:
        logger.debug("products get via service skipped", exc_info=True)
    verify_db_read_token_header(request)
    from app.bootstrap import get_products_service

    result = get_products_service().get_product(product_id)
    if result.get("success"):
        return result
    return JSONResponse(result, status_code=404)


@router.post("/products/resolve-name-hints")
@router.post("/products/resolve-name-hints/", include_in_schema=False)
def products_resolve_name_hints(request: Request, body: dict = Body(default_factory=dict)) -> dict:
    verify_db_read_token_header(request)
    raw = body.get("hints") or body.get("names") or []
    if not isinstance(raw, list):
        return {"success": False, "message": "hints 须为字符串数组", "data": []}
    hints = [str(x).strip() for x in raw if str(x).strip()]
    if not hints:
        return {"success": False, "message": "hints 不能为空", "data": []}

    gate = _business_mod_json_block()
    if gate:
        return {**gate, "data": []}

    raise HTTPException(
        status_code=501,
        detail=(
            "products/resolve-name-hints 未启用：product_name_resolve 模块已在清理过程中被移除，"
            "请使用销售合同流程中的 name_hint 解析能力。"
        ),
    )


@router.post("/products/update")
@router.post("/products/update/", include_in_schema=False)
def products_update(request: Request, body: dict = Body(default_factory=dict)) -> dict:
    try:
        from app.mod_sdk.erp_products_facade import (
            is_erp_products_via_service_enabled,
            products_update as products_update_via_service,
        )

        if is_erp_products_via_service_enabled():
            return products_update_via_service(request, body)
    except HTTPException:
        raise
    except Exception:
        logger.debug("products update via service skipped", exc_info=True)
    _products_write_raise(request)
    gate = _business_mod_json_block()
    if gate:
        return gate

    from app.application.excel_imports import _parse_price

    pid = _product_parse_id(body.get("id"))
    if pid is None:
        raise HTTPException(status_code=400, detail="id 无效或缺失")

    eng = get_sync_engine()
    insp = inspect(eng)
    col_names = {c["name"] for c in insp.get_columns("products")}
    if not {"id", "model_number", "name"}.issubset(col_names):
        raise HTTPException(
            status_code=503,
            detail="products 表缺少必要列（至少需要 id、model_number、name）。",
        )

    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="产品名称不能为空")

    sets: list[str] = []
    params: dict[str, object] = {"pid": pid}

    if "model_number" in col_names:
        mn = body.get("model_number")
        sets.append("model_number = :model_number")
        params["model_number"] = (str(mn).strip() if mn is not None else "")[:120]

    sets.append("name = :name")
    params["name"] = name[:500]

    if "specification" in col_names:
        sp = body.get("specification")
        sets.append("specification = :specification")
        params["specification"] = None if sp is None else str(sp)

    if "price" in col_names:
        sets.append("price = :price")
        params["price"] = _parse_price(body.get("price"))

    if "quantity" in col_names:
        sets.append("quantity = :quantity")
        params["quantity"] = _product_parse_quantity(body.get("quantity"))

    if "unit" in col_names:
        un = body.get("unit")
        sets.append("unit = :unit")
        params["unit"] = (str(un).strip() if un is not None else "")[:200]

    if "description" in col_names:
        dv = body.get("description")
        sets.append("description = :description")
        params["description"] = None if dv is None else str(dv)

    if "category" in col_names:
        cv = body.get("category")
        sets.append("category = :category")
        params["category"] = None if cv is None else str(cv)[:200]

    if "brand" in col_names:
        bv = body.get("brand")
        sets.append("brand = :brand")
        params["brand"] = None if bv is None else str(bv)[:200]

    if "is_active" in col_names:
        ia = _product_parse_is_active(body.get("is_active"))
        if ia is not None:
            sets.append("is_active = :is_active")
            params["is_active"] = ia

    if "updated_at" in col_names:
        sets.append("updated_at = NOW()")

    if not sets:
        raise HTTPException(status_code=400, detail="没有可更新的列")

    mod_and = products_update_or_delete_mod_and(col_names, params)
    sql = "UPDATE products SET " + ", ".join(sets) + " WHERE id = :pid" + mod_and
    try:
        with eng.begin() as conn:
            r = conn.execute(text(sql), params)
            if r.rowcount == 0:
                raise HTTPException(status_code=404, detail="产品不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("products update failed")
        raise HTTPException(status_code=500, detail=f"更新失败：{e}") from e

    return {"success": True, "data": {"id": pid}}


@router.post("/products/add")
@router.post("/products/add/", include_in_schema=False)
def products_add(request: Request, body: dict = Body(default_factory=dict)) -> dict:
    try:
        from app.mod_sdk.erp_products_facade import (
            is_erp_products_via_service_enabled,
            products_add as products_add_via_service,
        )

        if is_erp_products_via_service_enabled():
            return products_add_via_service(request, body)
    except HTTPException:
        raise
    except Exception:
        logger.debug("products add via service skipped", exc_info=True)
    _products_write_raise(request)
    gate = _business_mod_json_block()
    if gate:
        return gate

    from app.application.excel_imports import _norm_model, _parse_price

    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="产品名称不能为空")
    spec = str(body.get("specification") or "").strip()
    mn_raw = body.get("model_number")
    model_number = str(mn_raw).strip() if mn_raw is not None else ""
    if not model_number:
        model_number = _norm_model("", name, spec)

    eng = get_sync_engine()
    insp = inspect(eng)
    col_names = {c["name"] for c in insp.get_columns("products")}
    if not {"model_number", "name"}.issubset(col_names):
        raise HTTPException(
            status_code=503,
            detail="products 表缺少必要列（至少需要 model_number、name）。",
        )

    icols: list[str] = []
    params: dict[str, object] = {}

    def _add(col: str, val: object) -> None:
        if col in col_names:
            icols.append(col)
            params[col] = val

    _add("model_number", model_number[:120])
    _add("name", name[:500])
    _add("specification", spec or None)
    _add("price", _parse_price(body.get("price")))
    _add("quantity", _product_parse_quantity(body.get("quantity")))
    unit = str(body.get("unit") or "").strip()[:200]
    _add("unit", unit)
    _add(
        "description",
        str(body.get("description") or "") if body.get("description") is not None else None,
    )
    _add(
        "category",
        str(body.get("category") or "")[:200] if body.get("category") is not None else None,
    )
    _add("brand", str(body.get("brand") or "")[:200] if body.get("brand") is not None else None)
    ia = _product_parse_is_active(body.get("is_active"))
    if ia is not None and "is_active" in col_names:
        _add("is_active", ia)

    if not icols:
        raise HTTPException(status_code=500, detail="无法构造 INSERT 列")

    mid = scoped_mod_id()
    if "xcagi_mod_id" in col_names and mid:
        icols.append("xcagi_mod_id")
        params["xcagi_mod_id"] = mid

    quoted = ", ".join(_sql_ident(c) for c in icols)
    ph = ", ".join(f":{c}" for c in icols)
    sql = f"INSERT INTO products ({quoted}) VALUES ({ph}) RETURNING id"

    try:
        with eng.begin() as conn:
            new_id = conn.execute(text(sql), params).scalar_one()
    except Exception as e:
        logger.exception("products add failed")
        raise HTTPException(status_code=500, detail=f"添加失败：{e}") from e

    return {"success": True, "data": {"id": int(new_id)}}


@router.post("/products/delete")
@router.post("/products/delete/", include_in_schema=False)
def products_delete(request: Request, body: dict = Body(default_factory=dict)) -> dict:
    try:
        from app.mod_sdk.erp_products_facade import (
            is_erp_products_via_service_enabled,
            products_delete as products_delete_via_service,
        )

        if is_erp_products_via_service_enabled():
            return products_delete_via_service(request, body)
    except HTTPException:
        raise
    except Exception:
        logger.debug("products delete via service skipped", exc_info=True)
    _products_write_raise(request)
    gate = _business_mod_json_block()
    if gate:
        return gate

    pid = _product_parse_id(body.get("id"))
    if pid is None:
        raise HTTPException(status_code=400, detail="id 无效或缺失")

    eng = get_sync_engine()
    insp = inspect(eng)
    pcols = {c["name"] for c in insp.get_columns("products")}
    del_params: dict[str, object] = {"pid": pid}
    mod_and = products_update_or_delete_mod_and(pcols, del_params)
    try:
        with eng.begin() as conn:
            r = conn.execute(
                text("DELETE FROM products WHERE id = :pid" + mod_and),
                del_params,
            )
            if r.rowcount == 0:
                raise HTTPException(status_code=404, detail="产品不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("products delete failed")
        raise HTTPException(status_code=500, detail=f"删除失败：{e}") from e

    return {"success": True, "message": "已删除"}


@router.post("/products/batch-delete")
@router.post("/products/batch-delete/", include_in_schema=False)
def products_batch_delete(request: Request, body: dict = Body(default_factory=dict)) -> dict:
    try:
        from app.mod_sdk.erp_products_facade import (
            is_erp_products_via_service_enabled,
            products_batch_delete as products_batch_delete_via_service,
        )

        if is_erp_products_via_service_enabled():
            return products_batch_delete_via_service(request, body)
    except HTTPException:
        raise
    except Exception:
        logger.debug("products batch-delete via service skipped", exc_info=True)
    _products_write_raise(request)
    gate = _business_mod_json_block()
    if gate:
        return gate

    ids = body.get("ids") or body.get("product_ids") or []
    if not isinstance(ids, list) or not ids:
        raise HTTPException(status_code=400, detail="ids 须为非空数组")

    eng = get_sync_engine()
    insp = inspect(eng)
    pcols = {c["name"] for c in insp.get_columns("products")}
    deleted = 0
    skipped: list[str] = []
    try:
        with eng.begin() as conn:
            for raw in ids:
                pid = _product_parse_id(raw)
                if pid is None:
                    skipped.append(str(raw))
                    continue
                del_params = {"pid": pid}
                mod_and = products_update_or_delete_mod_and(pcols, del_params)
                r = conn.execute(
                    text("DELETE FROM products WHERE id = :pid" + mod_and),
                    del_params,
                )
                if r.rowcount:
                    deleted += 1
                else:
                    skipped.append(str(raw))
    except Exception as e:
        logger.exception("products batch-delete failed")
        raise HTTPException(status_code=500, detail=f"批量删除失败：{e}") from e

    return {
        "success": True,
        "message": f"已删除 {deleted} 条",
        "deleted": deleted,
        "skipped": skipped,
    }


@router.get("/products/price-list-export")
@router.get("/products/price-list-export/", include_in_schema=False)
def products_price_list_export(
    request: Request,
    unit: str | None = Query(None),
    keyword: str | None = Query(None),
    export_date: str | None = Query(None, description="报价日期 YYYY-MM-DD，默认当天"),
    template_id: str | None = Query(
        None, description="模板 slug（GET /api/document-templates?role=price_list_docx）"
    ),
) -> Response:
    verify_db_read_token_header(request)
    return _products_price_list_word_response(unit, keyword, export_date, template_id)


@router.get("/products/export.docx")
@router.get("/products/export.docx/", include_in_schema=False)
def products_export_docx(
    request: Request,
    unit: str | None = Query(None),
    keyword: str | None = Query(None),
    export_date: str | None = Query(None, description="报价日期 YYYY-MM-DD，默认当天"),
    template_id: str | None = Query(
        None, description="模板 slug（GET /api/document-templates?role=price_list_docx）"
    ),
) -> Response:
    verify_db_read_token_header(request)
    return _products_price_list_word_response(unit, keyword, export_date, template_id)


@router.get("/products/price-list-template-preview")
@router.get("/products/price-list-template-preview/", include_in_schema=False)
def products_price_list_template_preview(
    request: Request,
    template_id: str | None = Query(None, description="模板 slug（与 price-list-export 一致）"),
) -> dict:
    from app.infrastructure.documents.price_list_export import (
        build_price_list_template_preview_json,
    )

    verify_db_read_token_header(request)
    from app.shell.mod_business_scope import business_data_exposed, business_data_hidden_reason

    if not business_data_exposed():
        raise HTTPException(
            status_code=503,
            detail=business_data_hidden_reason() or "扩展 Mod 未就绪。",
        )
    return build_price_list_template_preview_json(template_id)
