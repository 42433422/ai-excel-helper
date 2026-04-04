# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from sqlalchemy import func, case, extract
from .plugins import AnalysisPlugin, PluginResult


@dataclass
class FinancialMetrics:
    total_revenue: float = 0.0
    total_cost: float = 0.0
    gross_profit: float = 0.0
    profit_margin: float = 0.0
    order_count: int = 0
    avg_order_value: float = 0.0


class FinancialReportPlugin(AnalysisPlugin):
    key = "financial_report"
    title = "财务报表分析"

    def run(self, payload: Dict[str, Any]) -> PluginResult:
        try:
            metrics = self._calculate_financial_metrics(payload)
            monthly_data = self._get_monthly_breakdown()
            product_analysis = self._get_product_profitability()
            customer_analysis = self._get_customer_analysis()

            summary = (
                f"本期营收 ¥{metrics.total_revenue:,.2f}，"
                f"成本估算 ¥{metrics.total_cost:,.2f}，"
                f"毛利润 ¥{metrics.gross_profit:,.2f}（毛利率 {metrics.profit_margin:.1f}%），"
                f"共 {metrics.order_count} 笔订单。"
            )

            return PluginResult(
                key=self.key,
                title=self.title,
                level="info",
                summary=summary,
                details={
                    "metrics": {
                        "total_revenue": round(metrics.total_revenue, 2),
                        "total_cost": round(metrics.total_cost, 2),
                        "gross_profit": round(metrics.gross_profit, 2),
                        "profit_margin": round(metrics.profit_margin, 2),
                        "order_count": metrics.order_count,
                        "avg_order_value": round(metrics.avg_order_value, 2),
                    },
                    "monthly_breakdown": monthly_data,
                    "product_analysis": product_analysis[:10],
                    "customer_analysis": customer_analysis[:10],
                },
            )
        except Exception as e:
            return PluginResult(
                key=self.key,
                title=self.title,
                level="warn",
                summary=f"财务分析执行失败：{str(e)}",
                details={"error": str(e)},
            )

    def _calculate_financial_metrics(self, payload: Dict[str, Any]) -> FinancialMetrics:
        from app.db.session import get_db
        from app.db.models.shipment import ShipmentRecord

        metrics = FinancialMetrics()

        with get_db() as db:
            now = datetime.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            result = db.query(
                func.coalesce(func.sum(ShipmentRecord.amount), 0).label("total_revenue"),
                func.count(ShipmentRecord.id).label("order_count"),
                func.coalesce(func.avg(ShipmentRecord.amount), 0).label("avg_order"),
            ).filter(
                ShipmentRecord.created_at >= month_start,
                ShipmentRecord.status == "completed",
            ).first()

            if result:
                metrics.total_revenue = float(result.total_revenue or 0)
                metrics.order_count = int(result.order_count or 0)
                metrics.avg_order_value = float(result.avg_order or 0)

            cost_result = self._estimate_cost(db)
            metrics.total_cost = cost_result

            metrics.gross_profit = metrics.total_revenue - metrics.total_cost

            if metrics.total_revenue > 0:
                metrics.profit_margin = (metrics.gross_profit / metrics.total_revenue) * 100

        return metrics

    def _estimate_cost(self, db) -> float:
        try:
            from app.db.models.material import Material
            from sqlalchemy import Float as SAFloat, cast

            inv_val = db.query(
                func.coalesce(
                    func.sum(cast(Material.quantity, SAFloat) * cast(Material.unit_price, SAFloat)),
                    0.0,
                )
            ).filter(Material.is_active == 1).scalar()

            return float(inv_val or 0) * 0.3
        except Exception:
            return 0.0

    def _get_monthly_breakdown(self) -> List[Dict[str, Any]]:
        try:
            from app.db.session import get_db
            from app.db.models.shipment import ShipmentRecord

            monthly_data = []
            with get_db() as db:
                for i in range(6):
                    date = datetime.now() - timedelta(days=30 * i)
                    month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

                    if i == 5:
                        month_end = month_start
                    else:
                        next_month = month_start + timedelta(days=32)
                        month_end = next_month.replace(day=1)

                    result = db.query(
                        func.coalesce(func.sum(ShipmentRecord.amount), 0).label("revenue"),
                        func.count(ShipmentRecord.id).label("count"),
                    ).filter(
                        ShipmentRecord.created_at >= month_start,
                        ShipmentRecord.created_at < month_end,
                    ).first()

                    monthly_data.append({
                        "month": month_start.strftime("%Y-%m"),
                        "revenue": round(float(result.revenue or 0), 2),
                        "order_count": int(result.count or 0),
                    })

            return list(reversed(monthly_data))
        except Exception:
            return []

    def _get_product_profitability(self) -> List[Dict[str, Any]]:
        try:
            from app.db.session import get_db
            from app.db.models.shipment import ShipmentRecord

            with get_db() as db:
                now = datetime.now()
                month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

                results = (
                    db.query(
                        ShipmentRecord.product_name,
                        func.coalesce(func.sum(ShipmentRecord.amount), 0).label("total_revenue"),
                        func.coalesce(func.sum(ShipmentRecord.quantity_kg), 0).label("total_qty"),
                        func.count(ShipmentRecord.id).label("order_count"),
                        func.coalesce(func.avg(ShipmentRecord.unit_price), 0).label("avg_price"),
                    )
                    .filter(ShipmentRecord.created_at >= month_start)
                    .group_by(ShipmentRecord.product_name)
                    .order_by(func.sum(ShipmentRecord.amount).desc())
                    .limit(15)
                    .all()
                )

                return [
                    {
                        "product_name": r.product_name,
                        "total_revenue": round(float(r.total_revenue or 0), 2),
                        "total_qty": round(float(r.total_qty or 0), 2),
                        "order_count": int(r.order_count or 0),
                        "avg_price": round(float(r.avg_price or 0), 2),
                    }
                    for r in results
                ]
        except Exception:
            return []

    def _get_customer_analysis(self) -> List[Dict[str, Any]]:
        try:
            from app.db.session import get_db
            from app.db.models.shipment import ShipmentRecord

            with get_db() as db:
                now = datetime.now()
                month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

                results = (
                    db.query(
                        ShipmentRecord.purchase_unit,
                        func.coalesce(func.sum(ShipmentRecord.amount), 0).label("total_amount"),
                        func.count(ShipmentRecord.id).label("order_count"),
                        func.coalesce(func.avg(ShipmentRecord.amount), 0).label("avg_order"),
                    )
                    .filter(ShipmentRecord.created_at >= month_start)
                    .group_by(ShipmentRecord.purchase_unit)
                    .order_by(func.sum(ShipmentRecord.amount).desc())
                    .limit(10)
                    .all()
                )

                return [
                    {
                        "customer": r.purchase_unit,
                        "total_amount": round(float(r.total_amount or 0), 2),
                        "order_count": int(r.order_count or 0),
                        "avg_order_value": round(float(r.avg_order or 0), 2),
                    }
                    for r in results
                ]
        except Exception:
            return []


class InventoryValuationPlugin(AnalysisPlugin):
    key = "inventory_valuation"
    title = "库存价值评估"

    def run(self, payload: Dict[str, Any]) -> PluginResult:
        try:
            material_valuation = self._get_material_valuation()
            product_valuation = self._get_product_valuation()
            low_stock_items = self._get_low_stock_items()

            total_value = material_valuation["total_value"] + product_valuation["total_value"]

            summary = (
                f"库存总估值 ¥{total_value:,.2f} "
                f"(原材料 ¥{material_valuation['total_value']:,.2f} + 成品 ¥{product_valuation['total_value']:,.2f})，"
                f"{low_stock_items['count']} 项低于安全库存。"
            )

            return PluginResult(
                key=self.key,
                title=self.title,
                level="warn" if low_stock_items["count"] > 0 else "info",
                summary=summary,
                details={
                    "materials": material_valuation,
                    "products": product_valuation,
                    "low_stock_alerts": low_stock_items["items"][:10],
                    "total_inventory_value": round(total_value, 2),
                },
            )
        except Exception as e:
            return PluginResult(
                key=self.key,
                title=self.title,
                level="warn",
                summary=f"库存评估失败：{str(e)}",
                details={"error": str(e)},
            )

    def _get_material_valuation(self) -> Dict[str, Any]:
        try:
            from app.db.session import get_db
            from app.db.models.material import Material
            from sqlalchemy import Float as SAFloat, cast

            with get_db() as db:
                total_items = db.query(func.count(Material.id)).filter(Material.is_active == 1).scalar() or 0

                total_value = db.query(
                    func.coalesce(
                        func.sum(cast(Material.quantity, SAFloat) * cast(Material.unit_price, SAFloat)),
                        0.0,
                    )
                ).filter(Material.is_active == 1).scalar()

                category_breakdown = (
                    db.query(
                        Material.category,
                        func.coalesce(
                            func.sum(cast(Material.quantity, SAFloat) * cast(Material.unit_price, SAFloat)),
                            0.0,
                        ).label("value"),
                        func.count(Material.id).label("count"),
                    )
                    .filter(Material.is_active == 1)
                    .group_by(Material.category)
                    .all()
                )

                return {
                    "total_items": int(total_items),
                    "total_value": round(float(total_value or 0), 2),
                    "categories": [
                        {"category": c[0] or "未分类", "value": round(float(c[1] or 0), 2), "count": int(c[2] or 0)}
                        for c in category_breakdown
                    ],
                }
        except Exception:
            return {"total_items": 0, "total_value": 0.0, "categories": []}

    def _get_product_valuation(self) -> Dict[str, Any]:
        try:
            from app.db.session import get_db
            from app.db.models.product import Product
            from sqlalchemy import Float as SAFloat, cast

            with get_db() as db:
                total_items = db.query(func.count(Product.id)).filter(Product.is_active == 1).scalar() or 0

                total_value = db.query(
                    func.coalesce(
                        func.sum(cast(Product.quantity, SAFloat) * cast(Product.price, SAFloat)),
                        0.0,
                    )
                ).filter(Product.is_active == 1).scalar()

                return {
                    "total_items": int(total_items),
                    "total_value": round(float(total_value or 0), 2),
                }
        except Exception:
            return {"total_items": 0, "total_value": 0.0}

    def _get_low_stock_items(self) -> Dict[str, Any]:
        try:
            from app.db.session import get_db
            from app.db.models.material import Material

            with get_db() as db:
                items = (
                    db.query(Material.name, Material.category, Material.quantity, Material.min_stock, Material.unit_price)
                    .filter(
                        Material.is_active == 1,
                        Material.min_stock > 0,
                        Material.quantity < Material.min_stock,
                    )
                    .limit(20)
                    .all()
                )

                return {
                    "count": len(items),
                    "items": [
                        {
                            "name": m.name,
                            "category": m.category,
                            "current": float(m.quantity or 0),
                            "min_required": float(m.min_stock or 0),
                            "unit_price": float(m.unit_price or 0),
                        }
                        for m in items
                    ],
                }
        except Exception:
            return {"count": 0, "items": []}
