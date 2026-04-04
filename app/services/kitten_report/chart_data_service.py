# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChartDataService:
    def __init__(self):
        pass

    def get_revenue_chart_data(self, months: int = 6) -> Dict[str, Any]:
        try:
            from app.db.session import get_db
            from app.db.models.shipment import ShipmentRecord

            chart_data = {"labels": [], "revenue": [], "orders": []}

            with get_db() as db:
                for i in range(months):
                    date = datetime.now() - timedelta(days=30 * i)
                    month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

                    if i == months - 1:
                        month_end = month_start
                    else:
                        next_month = month_start + timedelta(days=32)
                        month_end = next_month.replace(day=1)

                    result = db.query(
                        func.coalesce(func.sum(ShipmentRecord.amount), 0),
                        func.count(ShipmentRecord.id),
                    ).filter(
                        ShipmentRecord.created_at >= month_start,
                        ShipmentRecord.created_at < month_end,
                    ).first()

                    from sqlalchemy import func as sa_func
                    chart_data["labels"].insert(0, month_start.strftime("%Y-%m"))
                    chart_data["revenue"].insert(0, round(float(result[0] or 0), 2))
                    chart_data["orders"].insert(0, int(result[1] or 0))

            return {
                "success": True,
                "type": "line",
                "data": chart_data,
                "title": "月度营收趋势",
            }
        except Exception as e:
            logger.exception("get_revenue_chart_data failed: %s", e)
            return {"success": False, "error": str(e)}

    def get_product_pie_chart_data(self) -> Dict[str, Any]:
        try:
            from app.db.session import get_db
            from app.db.models.shipment import ShipmentRecord
            from sqlalchemy import func as sa_func

            now = datetime.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            with get_db() as db:
                results = (
                    db.query(
                        ShipmentRecord.product_name,
                        sa_func.coalesce(sa_func.sum(ShipmentRecord.amount), 0).label("total"),
                    )
                    .filter(ShipmentRecord.created_at >= month_start)
                    .group_by(ShipmentRecord.product_name)
                    .order_by(sa_func.sum(ShipmentRecord.amount).desc())
                    .limit(10)
                    .all()
                )

                labels = [r.product_name for r in results]
                values = [round(float(r.total or 0), 2) for r in results]

            return {
                "success": True,
                "type": "pie",
                "data": {
                    "labels": labels,
                    "values": values,
                },
                "title": "产品销售占比（本月）",
            }
        except Exception as e:
            logger.exception("get_product_pie_chart_data failed: %s", e)
            return {"success": False, "error": str(e)}

    def get_customer_bar_chart_data(self) -> Dict[str, Any]:
        try:
            from app.db.session import get_db
            from app.db.models.shipment import ShipmentRecord
            from sqlalchemy import func as sa_func

            now = datetime.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            with get_db() as db:
                results = (
                    db.query(
                        ShipmentRecord.purchase_unit,
                        sa_func.coalesce(sa_func.sum(ShipmentRecord.amount), 0).label("total"),
                        sa_func.count(ShipmentRecord.id).label("count"),
                    )
                    .filter(ShipmentRecord.created_at >= month_start)
                    .group_by(ShipmentRecord.purchase_unit)
                    .order_by(sa_func.sum(ShipmentRecord.amount).desc())
                    .limit(8)
                    .all()
                )

                data = {
                    "labels": [r.purchase_unit[:10] + "..." if len(r.purchase_unit) > 10 else r.purchase_unit for r in results],
                    "amounts": [round(float(r.total or 0), 2) for r in results],
                    "orders": [int(r.count or 0) for r in results],
                }

            return {
                "success": True,
                "type": "bar",
                "data": data,
                "title": "客户销售额排行（本月）",
            }
        except Exception as e:
            logger.exception("get_customer_bar_chart_data failed: %s", e)
            return {"success": False, "error": str(e)}

    def get_profit_trend_chart_data(self, months: int = 6) -> Dict[str, Any]:
        try:
            from app.db.session import get_db
            from app.db.models.shipment import ShipmentRecord
            from sqlalchemy import func as sa_func

            chart_data = {"labels": [], "revenue": [], "estimated_cost": [], "profit": []}

            with get_db() as db:
                for i in range(months):
                    date = datetime.now() - timedelta(days=30 * i)
                    month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

                    if i == months - 1:
                        month_end = month_start
                    else:
                        next_month = month_start + timedelta(days=32)
                        month_end = next_month.replace(day=1)

                    revenue_result = (
                        db.query(sa_func.coalesce(sa_func.sum(ShipmentRecord.amount), 0))
                        .filter(
                            ShipmentRecord.created_at >= month_start,
                            ShipmentRecord.created_at < month_end,
                        )
                        .scalar()
                    )

                    revenue = float(revenue_result or 0)
                    estimated_cost = revenue * 0.3
                    profit = revenue - estimated_cost

                    chart_data["labels"].insert(0, month_start.strftime("%Y-%m"))
                    chart_data["revenue"].insert(0, round(revenue, 2))
                    chart_data["estimated_cost"].insert(0, round(estimated_cost, 2))
                    chart_data["profit"].insert(0, round(profit, 2))

            return {
                "success": True,
                "type": "mixed",
                "data": chart_data,
                "title": "营收成本利润趋势",
            }
        except Exception as e:
            logger.exception("get_profit_trend_chart_data failed: %s", e)
            return {"success": False, "error": str(e)}

    def get_inventory_chart_data(self) -> Dict[str, Any]:
        try:
            from app.db.session import get_db
            from app.db.models.material import Material
            from sqlalchemy import Float as SAFloat, cast, func as sa_func

            with get_db() as db:
                category_results = (
                    db.query(
                        Material.category,
                        sa_func.coalesce(
                            sa_func.sum(cast(Material.quantity, SAFloat) * cast(Material.unit_price, SAFloat)),
                            0.0,
                        ).label("value"),
                    )
                    .filter(Material.is_active == 1)
                    .group_by(Material.category)
                    .all()
                )

                categories = []
                values = []

                for cat, val in category_results:
                    if val and val > 0:
                        categories.append(cat or "未分类")
                        values.append(round(float(val), 2))

            return {
                "success": True,
                "type": "doughnut",
                "data": {
                    "labels": categories,
                    "values": values,
                },
                "title": "原材料库存价值分布",
            }
        except Exception as e:
            logger.exception("get_inventory_chart_data failed: %s", e)
            return {"success": False, "error": str(e)}

    def get_all_charts_data(self) -> Dict[str, Any]:
        return {
            "revenue_trend": self.get_revenue_chart_data(),
            "product_distribution": self.get_product_pie_chart_data(),
            "customer_ranking": self.get_customer_bar_chart_data(),
            "profit_analysis": self.get_profit_trend_chart_data(),
            "inventory_breakdown": self.get_inventory_chart_data(),
        }


chart_service = ChartDataService()
