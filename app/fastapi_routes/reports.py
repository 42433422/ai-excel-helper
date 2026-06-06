"""
报表分析 API 路由

来源：从 legacy_inventory.py 中 /api/report/* 端点迁出。
预计后续引入 report_app_service_v2 接入 NeuroBus 事件流。

覆盖：
- /api/report/sales          销售报表
- /api/report/inventory      库存报表
- /api/report/inventory/transactions 库存流水报表
- /api/report/purchase       采购报表
- /api/report/dashboard      经营看板汇总
- /api/report/export         报表导出（Excel）
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Body, Query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reports"])


@router.get("/api/report/sales")
def report_sales(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    group_by: str = Query(default="product"),
    customer_id: int | None = Query(default=None),
):
    from app.application.facades.inventory_facade import ReportService

    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    return ReportService().get_sales_report(
        start_date=start_dt,
        end_date=end_dt,
        group_by=group_by,
        customer_id=customer_id,
    )


@router.get("/api/report/inventory")
def report_inventory(
    warehouse_id: int | None = Query(default=None),
    category: str | None = Query(default=None),
):
    from app.application.facades.inventory_facade import ReportService

    return ReportService().get_inventory_report(warehouse_id=warehouse_id, category=category)


@router.get("/api/report/inventory/transactions")
def report_inventory_transactions(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    transaction_type: str | None = Query(default=None),
    product_id: int | None = Query(default=None),
):
    from app.application.facades.inventory_facade import ReportService

    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    return ReportService().get_inventory_transaction_report(
        start_date=start_dt,
        end_date=end_dt,
        transaction_type=transaction_type,
        product_id=product_id,
    )


@router.get("/api/report/purchase")
def report_purchase(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    group_by: str = Query(default="supplier"),
):
    from app.application.facades.inventory_facade import ReportService

    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    return ReportService().get_purchase_report(
        start_date=start_dt,
        end_date=end_dt,
        group_by=group_by,
    )


@router.get("/api/report/dashboard")
def report_dashboard():
    from app.application.facades.inventory_facade import ReportService

    return ReportService().get_dashboard_summary()


@router.post("/api/report/export")
def report_export(body: dict = Body(default_factory=dict)):
    from app.application.facades.inventory_facade import ReportService

    data = body or {}
    return ReportService().export_to_excel(
        report_type=data.get("report_type", "report"),
        data=data.get("data", []),
        filename=data.get("filename", "report"),
    )
