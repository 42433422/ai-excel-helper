"""
库存管理 API 路由

来源：从 legacy_inventory.py 中 /api/inventory/* 端点迁出。
预计在完成 inventory_app_service_v2 全量实现后，直接调用新应用服务。

覆盖：
- /api/inventory             库存明细列表
- /api/inventory/summary     库存汇总
- /api/inventory/transactions 库存流水
- /api/inventory/locations*  储位管理
- /api/inventory/warehouses* 仓库管理
- /api/inventory/in|out|transfer 入库/出库/调拨
- /api/inventory/inventory/alert 库存预警
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Body, Query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["inventory"])


# ──────────────────────────── 库存明细 ────────────────────────────


@router.get("/api/inventory")
def inventory_list(
    warehouse_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    batch_no: str | None = Query(default=None),
    page: int = Query(default=1),
    per_page: int = Query(default=50),
):
    from app.application.facades.inventory_facade import InventoryService

    return InventoryService().get_inventory(
        warehouse_id=warehouse_id,
        product_id=product_id,
        batch_no=batch_no,
        page=page,
        per_page=per_page,
    )


@router.get("/api/inventory/summary")
def inventory_summary(warehouse_id: int | None = Query(default=None)):
    from app.application.facades.inventory_facade import InventoryService

    return InventoryService().get_inventory_summary(warehouse_id=warehouse_id)


@router.get("/api/inventory/transactions")
def inventory_transactions(
    product_id: int | None = Query(default=None),
    warehouse_id: int | None = Query(default=None),
    transaction_type: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    page: int = Query(default=1),
    per_page: int = Query(default=50),
):
    from app.application.facades.inventory_facade import InventoryService

    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    return InventoryService().get_inventory_transactions(
        product_id=product_id,
        warehouse_id=warehouse_id,
        transaction_type=transaction_type,
        start_date=start_dt,
        end_date=end_dt,
        page=page,
        per_page=per_page,
    )


# ──────────────────────────── 预警 ────────────────────────────


@router.get("/api/inventory/inventory/alert")
def inventory_alert():
    from app.application.facades.inventory_facade import InventoryService

    return InventoryService().get_inventory_alert()


@router.get("/api/inventory/alert")
def inventory_alert_alias():
    """兼容旧路径 /api/inventory/alert，转发到 /api/inventory/inventory/alert。"""
    from app.application.facades.inventory_facade import InventoryService

    return InventoryService().get_inventory_alert()


@router.get("/api/inventory/combined-alert")
def inventory_combined_alert(threshold: float | None = None):
    """聚合预警：合并仓储库存预警（inventory/alert）与原材料低库存（materials/low-stock），消除双轨概念混乱。"""
    from app.application.facades.inventory_facade import InventoryService

    inv_result = InventoryService().get_inventory_alert()
    inv_items = inv_result.get("data") or inv_result.get("alerts") or []

    mat_items: list = []
    try:
        from app.application import get_material_application_service

        mat_result = get_material_application_service().get_low_stock_materials(threshold=threshold)
        mat_items = mat_result.get("data") or []
    except Exception:
        pass

    return {
        "success": True,
        "inventory_alerts": inv_items,
        "material_low_stock": mat_items,
        "total_alerts": len(inv_items) + len(mat_items),
    }


# ──────────────────────────── 储位 ────────────────────────────


@router.get("/api/inventory/locations")
def inventory_locations(
    warehouse_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
):
    from app.application.facades.inventory_facade import InventoryService

    if not warehouse_id:
        return {"success": False, "message": "仓库ID不能为空"}
    return InventoryService().get_storage_locations(warehouse_id=warehouse_id, status=status)


@router.post("/api/inventory/locations")
def inventory_locations_post(body: dict = Body(default_factory=dict)):
    from app.application.facades.inventory_facade import InventoryService

    return InventoryService().create_storage_location(body or {})


@router.put("/api/inventory/locations/{location_id}")
def inventory_locations_put(location_id: int, body: dict = Body(default_factory=dict)):
    from app.application.facades.inventory_facade import InventoryService

    return InventoryService().update_storage_location(location_id, body or {})


# ──────────────────────────── 仓库 ────────────────────────────


@router.get("/api/inventory/warehouses")
def inventory_warehouses_list(status: str | None = Query(default=None)):
    from app.application.facades.inventory_facade import InventoryService

    return InventoryService().get_warehouses(status=status)


@router.get("/api/inventory/warehouses/{warehouse_id}")
def inventory_warehouses_get(warehouse_id: int):
    from app.application.facades.inventory_facade import InventoryService

    return InventoryService().get_warehouse(warehouse_id)


@router.post("/api/inventory/warehouses")
def inventory_warehouses_post(body: dict = Body(default_factory=dict)):
    from app.application.facades.inventory_facade import InventoryService

    return InventoryService().create_warehouse(body or {})


@router.put("/api/inventory/warehouses/{warehouse_id}")
def inventory_warehouses_put(warehouse_id: int, body: dict = Body(default_factory=dict)):
    from app.application.facades.inventory_facade import InventoryService

    return InventoryService().update_warehouse(warehouse_id, body or {})


@router.delete("/api/inventory/warehouses/{warehouse_id}")
def inventory_warehouses_delete(warehouse_id: int):
    from app.application.facades.inventory_facade import InventoryService

    return InventoryService().delete_warehouse(warehouse_id)


# ──────────────────────────── 出入库操作 ────────────────────────────


@router.post("/api/inventory/in")
def inventory_in(body: dict = Body(default_factory=dict)):
    from app.application.facades.inventory_facade import InventoryService

    data = body or {}
    return InventoryService().inventory_in(
        product_id=data.get("product_id"),
        warehouse_id=data.get("warehouse_id"),
        quantity=float(data.get("quantity", 0)),
        batch_no=data.get("batch_no"),
        location_id=data.get("location_id"),
        unit_price=float(data["unit_price"]) if data.get("unit_price") is not None else None,
        reference_type=data.get("reference_type"),
        reference_id=data.get("reference_id"),
        operator=data.get("operator"),
        remark=data.get("remark"),
    )


@router.post("/api/inventory/out")
def inventory_out(body: dict = Body(default_factory=dict)):
    from app.application.facades.inventory_facade import InventoryService

    data = body or {}
    return InventoryService().inventory_out(
        product_id=data.get("product_id"),
        warehouse_id=data.get("warehouse_id"),
        quantity=float(data.get("quantity", 0)),
        batch_no=data.get("batch_no"),
        location_id=data.get("location_id"),
        unit_price=float(data["unit_price"]) if data.get("unit_price") is not None else None,
        reference_type=data.get("reference_type"),
        reference_id=data.get("reference_id"),
        operator=data.get("operator"),
        remark=data.get("remark"),
    )


@router.post("/api/inventory/transfer")
def inventory_transfer(body: dict = Body(default_factory=dict)):
    from app.application.facades.inventory_facade import InventoryService

    data = body or {}
    return InventoryService().inventory_transfer(
        product_id=data.get("product_id"),
        from_warehouse_id=data.get("from_warehouse_id"),
        to_warehouse_id=data.get("to_warehouse_id"),
        quantity=float(data.get("quantity", 0)),
        batch_no=data.get("batch_no"),
        from_location_id=data.get("from_location_id"),
        to_location_id=data.get("to_location_id"),
        operator=data.get("operator"),
        remark=data.get("remark"),
    )
