"""
出货单 / 订单 / 出货记录 —— 继承自归档 ``ai_assistant_compat`` + ``shipment`` 蓝图端点契约的 FastAPI 补全。

覆盖：

- ``/api/orders*``、``/orders/next_number``（AI 助手根路径）
- ``/api/shipment/generate|print|download/*`` 与 ``/api/shipment/orders*``（与归档 ``shipment`` 蓝图对齐）
- ``GET /api/shipment/list`` 统一注册
- ``/api/shipment/shipment-records/*``

历史：统一 FastAPI 入口后兼容层未挂载上述路径时，前端会出现大量 404。
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from app.application.facades.query_facade import query_service
from app.bootstrap import get_shipment_application_service_core
from app.db.models import ShipmentRecord

logger = logging.getLogger(__name__)

router = APIRouter(tags=["shipment-orders-compat"])


def _svc():
    return get_shipment_application_service_core()


def _next_order_number_payload(suffix: str = "A") -> dict[str, Any]:
    today = datetime.now()
    year = today.strftime("%y")
    month = today.strftime("%m")
    start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (start + timedelta(days=32)).replace(day=1)
    count = query_service.count(
        ShipmentRecord,
        created_at__gte=start,
        created_at__lt=next_month,
    )
    next_sequence = int(count) + 1
    order_number = f"{year}-{month}-{next_sequence:05d}{suffix}"
    return {
        "success": True,
        "data": {
            "order_number": order_number,
            "sequence": next_sequence,
            "year_month": f"{year}-{month}",
        },
    }


@router.get("/orders/next_number")
def orders_next_number_root(suffix: str = Query(default="A")):
    return _next_order_number_payload(suffix)


@router.get("/api/shipment/orders/next_number")
def orders_next_number_under_shipment(suffix: str = Query(default="A")):
    # 与归档 ``shipment.get_next_order_number`` 一致：后缀须为单个大写字母，否则回退 A
    suf = (suffix or "").strip().upper()
    if not (len(suf) == 1 and re.fullmatch(r"[A-Z]", suf)):
        suf = "A"
    return _next_order_number_payload(suf)


@router.get("/api/orders/next_number")
def orders_next_number_under_api(suffix: str = Query(default="A")):
    return _next_order_number_payload(suffix)


# ----- /api/shipment（归档 shipment 蓝图，与 /api/orders* 镜像）-----


@router.post("/api/shipment/generate-batch")
def shipment_generate_batch(payload: dict[str, Any] = Body(default_factory=dict)):
    """批量生成：兼容测试与旧前端字段（customer_name / items）。"""
    shipments = payload.get("shipments") or []
    if not shipments:
        raise HTTPException(status_code=400, detail="shipments 不能为空")
    ok_count = 0
    errors: list[dict[str, Any]] = []
    for idx, s in enumerate(shipments):
        if not isinstance(s, dict):
            errors.append({"index": idx, "error": "条目必须是对象"})
            continue
        unit_name = str(s.get("unit_name") or s.get("customer_name") or "").strip()
        products = s.get("products") or s.get("items") or []
        if not unit_name:
            errors.append({"index": idx, "error": "单位名称不能为空"})
            continue
        if not products:
            errors.append({"index": idx, "error": "产品列表不能为空"})
            continue
        try:
            result = _svc().generate_shipment_document(
                unit_name=unit_name,
                products=products,
            )
            if result.get("success"):
                ok_count += 1
            else:
                errors.append({"index": idx, "error": result.get("message", "生成失败")})
        except Exception as e:
            logger.exception("shipment generate-batch[%s]: %s", idx, e)
            errors.append({"index": idx, "error": str(e)})
    return {
        "success": ok_count > 0 or not errors,
        "data": {"processed": ok_count, "total": len(shipments), "errors": errors},
    }


@router.post("/api/shipment/generate")
def shipment_generate(payload: dict[str, Any] = Body(default_factory=dict)):
    unit_name = str(payload.get("unit_name") or "").strip()
    products = payload.get("products") or []
    date = payload.get("date")
    if not unit_name:
        raise HTTPException(status_code=400, detail="单位名称不能为空")
    if not products:
        raise HTTPException(status_code=400, detail="产品列表不能为空")
    try:
        result = _svc().generate_shipment_document(
            unit_name=unit_name,
            products=products,
            date=date,
        )
        return JSONResponse(result, status_code=200 if result.get("success") else 500)
    except Exception as e:
        logger.exception("shipment generate: %s", e)
        return JSONResponse(
            {"success": False, "message": f"生成失败：{str(e)}"},
            status_code=500,
        )


@router.post("/api/shipment/print")
def shipment_print(payload: dict[str, Any] = Body(default_factory=dict)):
    file_path = payload.get("file_path")
    order_id = payload.get("order_id")
    printer_name = payload.get("printer_name")

    if not file_path:
        raise HTTPException(status_code=400, detail="文件路径不能为空")
    if not os.path.exists(str(file_path)):
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        if order_id:
            try:
                shipment_id = int(order_id)
            except Exception:
                raise HTTPException(status_code=400, detail="order_id 无效")
            result = _svc().mark_as_printed(shipment_id, printer_name=str(printer_name or ""))
            if isinstance(result, dict):
                result["file_path"] = file_path
                if "updated" not in result:
                    result["updated"] = bool(result.get("success"))
        else:
            result = {
                "success": True,
                "message": "发货单打印请求已完成，但未更新记录（缺少 order_id）",
                "printed_at": datetime.now().isoformat(),
                "file_path": file_path,
                "updated": False,
                "warning": "缺少 order_id，已跳过数据库状态更新",
            }
        return JSONResponse(result, status_code=200 if result.get("success") else 500)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("shipment print: %s", e)
        return JSONResponse(
            {"success": False, "message": f"打印失败：{str(e)}"},
            status_code=500,
        )


@router.get("/api/shipment/download/{filename:path}")
def shipment_download(filename: str):
    from app.utils.path_utils import get_app_data_dir

    output_dir = os.path.join(get_app_data_dir(), "shipment_outputs")
    safe = os.path.basename(filename) or filename
    file_path = os.path.join(output_dir, safe)
    if file_path and os.path.exists(file_path):
        return FileResponse(
            file_path,
            filename=safe,
            media_type="application/octet-stream",
        )
    return JSONResponse(
        {"success": False, "message": "文件不存在"},
        status_code=404,
    )


@router.get("/api/shipment/orders/purchase-units")
def shipment_orders_purchase_units():
    units = _svc().get_purchase_units()
    return {"success": True, "data": units, "count": len(units)}


@router.post("/api/shipment/orders/clear-shipment")
def shipment_orders_clear_shipment(payload: dict[str, Any] = Body(default_factory=dict)):
    purchase_unit = str(payload.get("purchase_unit") or "").strip()
    if not purchase_unit:
        raise HTTPException(status_code=400, detail="缺少购买单位参数")
    result = _svc().clear_shipment_by_unit(purchase_unit)
    return JSONResponse(result, status_code=200 if result.get("success") else 500)


@router.get("/api/shipment/orders")
def shipment_orders_list(limit: int = Query(default=100, ge=1, le=5000)):
    orders_list = _svc().get_orders(limit=limit) or []
    inner = {"success": True, "data": orders_list, "count": len(orders_list)}
    return {"success": True, "data": inner, "count": len(inner)}


@router.get("/api/shipment/orders/search")
def shipment_orders_search(q: str = Query(default="")):
    qs = (q or "").strip()
    if not qs:
        return {"success": True, "data": [], "count": 0}
    rows = _svc().search_orders(qs)
    return {"success": True, "data": rows, "count": len(rows)}


@router.get("/api/shipment/orders/latest")
def shipment_orders_latest():
    orders = _svc().get_orders(limit=10) or []
    return {"success": True, "data": orders}


@router.post("/api/shipment/orders/set-sequence")
def shipment_orders_set_sequence(payload: dict[str, Any] = Body(default_factory=dict)):
    sequence = int(payload.get("sequence", 1))
    result = _svc().set_order_sequence(sequence)
    return JSONResponse(result, status_code=200 if result.get("success") else 500)


@router.post("/api/shipment/orders/reset-sequence")
def shipment_orders_reset_sequence():
    result = _svc().reset_order_sequence()
    return JSONResponse(result, status_code=200 if result.get("success") else 500)


@router.delete("/api/shipment/orders/clear-all")
def shipment_orders_clear_all():
    result = _svc().clear_all_orders()
    return JSONResponse(result, status_code=200 if result.get("success") else 500)


@router.get("/api/shipment/orders/{order_number}")
def shipment_orders_get(order_number: str):
    order = _svc().get_order(str(order_number))
    if order:
        return {"success": True, "data": order}
    raise HTTPException(status_code=404, detail="订单不存在")


# ----- /api/orders（静态子路径必须早于 /api/orders/{order_number}）-----


@router.get("/api/orders")
def api_orders_list(limit: int = Query(default=100, ge=1, le=5000)):
    orders = _svc().get_orders(limit=limit) or []
    return {"success": True, "data": orders, "count": len(orders)}


@router.delete("/api/orders")
@router.delete("/api/orders/", include_in_schema=False)
def api_orders_delete_root():
    result = _svc().clear_all_orders()
    return JSONResponse(result, status_code=200 if result.get("success") else 500)


@router.get("/api/orders/latest")
def api_orders_latest():
    orders = _svc().get_orders(limit=10) or []
    return {"success": True, "data": orders, "count": len(orders)}


@router.get("/api/orders/search")
def api_orders_search(q: str = Query(default="")):
    qs = (q or "").strip()
    rows = _svc().search_orders(qs) if qs else []
    return {"success": True, "data": rows, "count": len(rows)}


@router.post("/api/orders/set-sequence")
def api_orders_set_sequence(payload: dict[str, Any] = Body(default_factory=dict)):
    sequence = int(payload.get("sequence", 1))
    return _svc().set_order_sequence(sequence)


@router.post("/api/orders/reset-sequence")
def api_orders_reset_sequence():
    return _svc().reset_order_sequence()


@router.get("/api/orders/purchase-units")
def api_orders_purchase_units():
    units = _svc().get_purchase_units()
    return {"success": True, "data": units, "count": len(units)}


@router.post("/api/orders/clear-shipment")
def api_orders_clear_shipment(payload: dict[str, Any] = Body(default_factory=dict)):
    purchase_unit = str(payload.get("purchase_unit") or "").strip()
    if not purchase_unit:
        raise HTTPException(status_code=400, detail="缺少购买单位参数")
    result = _svc().clear_shipment_by_unit(purchase_unit)
    return JSONResponse(result, status_code=200 if result.get("success") else 500)


@router.delete("/api/orders/clear-all")
def api_orders_clear_all():
    result = _svc().clear_all_orders()
    return JSONResponse(result, status_code=200 if result.get("success") else 500)


@router.get("/api/orders/{order_number}")
def api_orders_get(order_number: str):
    try:
        int(order_number)
    except ValueError:
        raise HTTPException(status_code=404, detail="订单不存在")
    order = _svc().get_order(str(order_number))
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return {"success": True, "data": order}


@router.delete("/api/shipment/orders/{order_number}")
def shipment_orders_delete(order_number: str):
    try:
        shipment_id = int(order_number)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的订单编号格式：{order_number}")
    result = _svc().delete_shipment(shipment_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "删除失败"))
    return {"success": True, "message": f"订单 {order_number} 已删除"}


# ----- /api/shipment/shipment-records -----


@router.get("/api/shipment/records")
def shipment_records_dashboard_alias(
    unit: str | None = Query(default=None),
    unit_name: str | None = Query(default=None),
    per_page: int = Query(default=100, ge=1, le=500),
    sort: str | None = Query(default=None),
):
    """企业客服等页面使用的短路径；与 shipment-records/records 同源，支持 per_page。"""
    _ = sort  # 预留与前端 sort=created_at_desc 对齐；列表默认按 created_at 倒序
    u = (unit or unit_name or "").strip() or None
    records = _svc().get_shipment_records(u, limit=per_page)
    return {"success": True, "data": records}


@router.get("/api/shipment/shipment-records/records")
@router.get("/api/shipment/shipment-records/records/", include_in_schema=False)
def shipment_records_list(
    unit: str | None = Query(default=None),
    unit_name: str | None = Query(default=None),
):
    try:
        from app.mod_sdk.erp_domain_dispatch import try_invoke_erp_domain_handler

        mod_out = try_invoke_erp_domain_handler(
            "shipment",
            "records_list",
            unit=unit,
            unit_name=unit_name,
        )
        if mod_out is not None:
            return mod_out
    except Exception:
        logger.debug("erp domain shipment.records_list dispatch skipped", exc_info=True)
    u = (unit or unit_name or "").strip() or None
    records = _svc().get_shipment_records(u)
    return {"success": True, "data": records}


@router.post("/api/shipment/shipment-records/record")
def shipment_records_create(payload: dict[str, Any] = Body(...)):
    """新建出货记录（从出货记录管理页手动建单）。"""
    unit_name = str(payload.get("unit_name") or payload.get("purchase_unit") or "").strip()
    if not unit_name:
        raise HTTPException(status_code=400, detail="缺少购买单位")
    products = payload.get("products") or []
    if not isinstance(products, list):
        products = []
    result = _svc().create_shipment(
        unit_name=unit_name,
        items_data=products,
        contact_person=payload.get("contact_person"),
        contact_phone=payload.get("contact_phone"),
    )
    return JSONResponse(result, status_code=200 if result.get("success") else 400)


@router.patch("/api/shipment/shipment-records/record")
def shipment_records_patch(payload: dict[str, Any] = Body(...)):
    record_id = payload.get("id")
    if not record_id:
        raise HTTPException(status_code=400, detail="缺少记录 ID")
    result = _svc().update_shipment_record(
        int(record_id),
        unit_name=payload.get("unit_name"),
        products=payload.get("products"),
        date=payload.get("date"),
        **{k: v for k, v in payload.items() if k not in ("id", "unit_name", "products", "date")},
    )
    return JSONResponse(result, status_code=200 if result.get("success") else 404)


@router.delete("/api/shipment/shipment-records/record")
def shipment_records_delete(payload: dict[str, Any] = Body(...)):
    record_id = payload.get("id")
    if not record_id:
        raise HTTPException(status_code=400, detail="缺少记录 ID")
    result = _svc().delete_shipment_record(int(record_id))
    return JSONResponse(result, status_code=200 if result.get("success") else 404)


@router.get("/api/shipment/shipment-records/export")
def shipment_records_export(
    unit: str | None = Query(default=None),
    unit_name: str | None = Query(default=None),
    template_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    u = (unit or unit_name or "").strip() or None
    result = _svc().export_shipment_records(
        unit_name=u,
        template_id=template_id,
        status_filter=status,
    )
    fp = result.get("file_path")
    if result.get("success") and fp and os.path.exists(str(fp)):
        fn = result.get("filename") or os.path.basename(str(fp))
        return FileResponse(
            str(fp),
            filename=fn,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    return JSONResponse(result, status_code=200 if result.get("success") else 500)
