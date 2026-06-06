"""
采购管理 API 路由

来源：从 legacy_inventory.py 中 /api/purchase/* 端点迁出。
预计在完成 purchase_app_service_v2 事件驱动重构后，直接调用新应用服务。

覆盖：
- /api/purchase/suppliers*    供应商 CRUD
- /api/purchase/orders*       采购订单 CRUD + 审批/取消
- /api/purchase/inbounds*     采购入库单 CRUD
- /api/purchase/summary       采购汇总
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Body, Query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["purchase"])


# ──────────────────────────── 供应商 ────────────────────────────


@router.get("/api/purchase/suppliers")
def purchase_suppliers(
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
):
    from app.application.facades.inventory_facade import PurchaseService

    return PurchaseService().get_suppliers(status=status, keyword=keyword)


@router.get("/api/purchase/suppliers/summary")
def purchase_suppliers_summary():
    from app.application.facades.inventory_facade import PurchaseService

    return PurchaseService().get_supplier_summary()


@router.get("/api/purchase/suppliers/{supplier_id}")
def purchase_supplier_get(supplier_id: int):
    from app.application.facades.inventory_facade import PurchaseService

    return PurchaseService().get_supplier(supplier_id)


@router.post("/api/purchase/suppliers")
def purchase_suppliers_post(body: dict = Body(default_factory=dict)):
    from app.application.facades.inventory_facade import PurchaseService

    return PurchaseService().create_supplier(body or {})


@router.put("/api/purchase/suppliers/{supplier_id}")
def purchase_suppliers_put(supplier_id: int, body: dict = Body(default_factory=dict)):
    from app.application.facades.inventory_facade import PurchaseService

    return PurchaseService().update_supplier(supplier_id, body or {})


@router.delete("/api/purchase/suppliers/{supplier_id}")
def purchase_supplier_delete(supplier_id: int):
    from app.application.facades.inventory_facade import PurchaseService

    return PurchaseService().delete_supplier(supplier_id)


# ──────────────────────────── 采购订单 ────────────────────────────


@router.get("/api/purchase/orders")
def purchase_orders(
    supplier_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    page: int = Query(default=1),
    per_page: int = Query(default=20),
):
    from app.application.facades.inventory_facade import PurchaseService

    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    return PurchaseService().get_purchase_orders(
        supplier_id=supplier_id,
        status=status,
        start_date=start_dt,
        end_date=end_dt,
        page=page,
        per_page=per_page,
    )


@router.get("/api/purchase/orders/{order_id}")
def purchase_order_get(order_id: int):
    from app.application.facades.inventory_facade import PurchaseService

    return PurchaseService().get_purchase_order(order_id)


@router.post("/api/purchase/orders")
def purchase_orders_post(body: dict = Body(default_factory=dict)):
    from app.application.facades.inventory_facade import PurchaseService

    return PurchaseService().create_purchase_order(body or {})


@router.put("/api/purchase/orders/{order_id}")
def purchase_orders_put(order_id: int, body: dict = Body(default_factory=dict)):
    from app.application.facades.inventory_facade import PurchaseService

    return PurchaseService().update_purchase_order(order_id, body or {})


@router.post("/api/purchase/orders/{order_id}/approve")
def purchase_orders_approve(order_id: int, approver: str = Query(default="system")):
    from app.application.facades.inventory_facade import PurchaseService

    return PurchaseService().approve_purchase_order(order_id, approver)


@router.post("/api/purchase/orders/{order_id}/cancel")
def purchase_orders_cancel(order_id: int):
    from app.application.facades.inventory_facade import PurchaseService

    return PurchaseService().cancel_purchase_order(order_id)


# ──────────────────────────── 采购入库 ────────────────────────────


@router.get("/api/purchase/inbounds")
def purchase_inbounds(
    supplier_id: int | None = Query(default=None),
    order_id: int | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    page: int = Query(default=1),
    per_page: int = Query(default=20),
):
    from app.application.facades.inventory_facade import PurchaseService

    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    return PurchaseService().get_purchase_inbounds(
        supplier_id=supplier_id,
        order_id=order_id,
        start_date=start_dt,
        end_date=end_dt,
        page=page,
        per_page=per_page,
    )


@router.post("/api/purchase/inbounds")
def purchase_inbounds_post(body: dict = Body(default_factory=dict)):
    from app.application.facades.inventory_facade import PurchaseService

    return PurchaseService().create_purchase_inbound(body or {})


# ──────────────────────────── 汇总 ────────────────────────────


@router.get("/api/purchase/summary")
def purchase_summary():
    from app.application.facades.inventory_facade import PurchaseService

    return PurchaseService().get_purchase_summary()
