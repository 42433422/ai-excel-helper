# -*- coding: utf-8 -*-
"""
报表服务模块

提供销售、库存、采购等统计报表。
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import func

from app.db.models import (
    Customer,
    InventoryLedger,
    InventoryTransaction,
    Product,
    PurchaseInbound,
    PurchaseInboundItem,
    PurchaseOrder,
    PurchaseOrderItem,
    ShipmentRecord,
    Supplier,
)
from app.db.session import get_db

logger = logging.getLogger(__name__)


class ReportService:
    """报表服务类"""

    @staticmethod
    def _decimal_to_float(value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        return value

    def get_sales_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "product",
        customer_id: Optional[int] = None
    ) -> Dict[str, Any]:
        with get_db() as db:
            query = db.query(
                ShipmentRecord,
                func.count(ShipmentRecord.id).label("record_count")
            )

            if start_date:
                query = query.filter(ShipmentRecord.shipment_date >= start_date)
            if end_date:
                query = query.filter(ShipmentRecord.shipment_date <= end_date)
            if customer_id:
                query = query.filter(ShipmentRecord.customer_id == customer_id)

            records = query.group_by(ShipmentRecord.id).all()

            if group_by == "product":
                product_stats = {}
                for record, count in records:
                    for item in record.items:
                        key = item.product_name or f"产品{item.product_id}"
                        if key not in product_stats:
                            product_stats[key] = {"product_name": key, "quantity": 0, "amount": 0}
                        product_stats[key]["quantity"] += float(item.quantity or 0)
                        product_stats[key]["amount"] += float(item.amount or 0)

                return {
                    "success": True,
                    "data": list(product_stats.values()),
                    "summary": {
                        "total_quantity": sum(p["quantity"] for p in product_stats.values()),
                        "total_amount": sum(p["amount"] for p in product_stats.values())
                    }
                }

            elif group_by == "customer":
                customer_stats = {}
                for record, count in records:
                    key = record.customer_name or f"客户{record.customer_id}"
                    if key not in customer_stats:
                        customer_stats[key] = {"customer_name": key, "order_count": 0, "amount": 0}
                    customer_stats[key]["order_count"] += 1
                    customer_stats[key]["amount"] += float(record.total_amount or 0)

                return {
                    "success": True,
                    "data": list(customer_stats.values()),
                    "summary": {
                        "total_customers": len(customer_stats),
                        "total_amount": sum(c["amount"] for c in customer_stats.values())
                    }
                }

            elif group_by == "date":
                date_stats = {}
                for record, count in records:
                    date_key = record.shipment_date.strftime("%Y-%m-%d") if record.shipment_date else "unknown"
                    if date_key not in date_stats:
                        date_stats[date_key] = {"date": date_key, "order_count": 0, "amount": 0}
                    date_stats[date_key]["order_count"] += 1
                    date_stats[date_key]["amount"] += float(record.total_amount or 0)

                return {
                    "success": True,
                    "data": list(date_stats.values()),
                    "summary": {
                        "total_days": len(date_stats),
                        "total_amount": sum(d["amount"] for d in date_stats.values())
                    }
                }

            return {"success": True, "data": [], "summary": {}}

    def get_inventory_report(
        self,
        warehouse_id: Optional[int] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        with get_db() as db:
            query = db.query(
                InventoryLedger,
                Product
            ).join(Product)

            if warehouse_id:
                query = query.filter(InventoryLedger.warehouse_id == warehouse_id)
            if category:
                query = query.filter(Product.category == category)

            ledgers = query.all()

            product_inventory = {}
            for ledger, product in ledgers:
                key = product.id
                if key not in product_inventory:
                    product_inventory[key] = {
                        "product_id": product.id,
                        "product_name": product.name,
                        "model_number": product.model_number,
                        "category": product.category,
                        "total_quantity": 0,
                        "available_quantity": 0,
                        "reserved_quantity": 0,
                        "warehouse_name": ledger.warehouse.name if ledger.warehouse else None
                    }
                product_inventory[key]["total_quantity"] += float(ledger.quantity or 0)
                product_inventory[key]["available_quantity"] += float(ledger.available_quantity or 0)
                product_inventory[key]["reserved_quantity"] += float(ledger.reserved_quantity or 0)

            return {
                "success": True,
                "data": list(product_inventory.values()),
                "summary": {
                    "total_products": len(product_inventory),
                    "total_quantity": sum(p["total_quantity"] for p in product_inventory.values()),
                    "total_available": sum(p["available_quantity"] for p in product_inventory.values())
                }
            }

    def get_purchase_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "supplier"
    ) -> Dict[str, Any]:
        with get_db() as db:
            query = db.query(PurchaseOrder)

            if start_date:
                query = query.filter(PurchaseOrder.order_date >= start_date)
            if end_date:
                query = query.filter(PurchaseOrder.order_date <= end_date)

            orders = query.all()

            if group_by == "supplier":
                supplier_stats = {}
                for order in orders:
                    key = order.supplier.name if order.supplier else f"供应商{order.supplier_id}"
                    if key not in supplier_stats:
                        supplier_stats[key] = {
                            "supplier_name": key,
                            "order_count": 0,
                            "total_amount": 0,
                            "paid_amount": 0
                        }
                    supplier_stats[key]["order_count"] += 1
                    supplier_stats[key]["total_amount"] += float(order.total_amount or 0)
                    supplier_stats[key]["paid_amount"] += float(order.paid_amount or 0)

                return {
                    "success": True,
                    "data": list(supplier_stats.values()),
                    "summary": {
                        "total_suppliers": len(supplier_stats),
                        "total_amount": sum(s["total_amount"] for s in supplier_stats.values())
                    }
                }

            elif group_by == "status":
                status_stats = {}
                for order in orders:
                    key = order.status or "unknown"
                    if key not in status_stats:
                        status_stats[key] = {"status": key, "order_count": 0, "total_amount": 0}
                    status_stats[key]["order_count"] += 1
                    status_stats[key]["total_amount"] += float(order.total_amount or 0)

                return {
                    "success": True,
                    "data": list(status_stats.values())
                }

            elif group_by == "date":
                date_stats = {}
                for order in orders:
                    date_key = order.order_date.strftime("%Y-%m-%d") if order.order_date else "unknown"
                    if date_key not in date_stats:
                        date_stats[date_key] = {"date": date_key, "order_count": 0, "total_amount": 0}
                    date_stats[date_key]["order_count"] += 1
                    date_stats[date_key]["total_amount"] += float(order.total_amount or 0)

                return {
                    "success": True,
                    "data": list(date_stats.values())
                }

            return {"success": True, "data": []}

    def get_inventory_transaction_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        transaction_type: Optional[str] = None,
        product_id: Optional[int] = None
    ) -> Dict[str, Any]:
        with get_db() as db:
            query = db.query(InventoryTransaction)

            if start_date:
                query = query.filter(InventoryTransaction.transaction_date >= start_date)
            if end_date:
                query = query.filter(InventoryTransaction.transaction_date <= end_date)
            if transaction_type:
                query = query.filter(InventoryTransaction.transaction_type == transaction_type)
            if product_id:
                query = query.filter(InventoryTransaction.product_id == product_id)

            transactions = query.order_by(InventoryTransaction.transaction_date.desc()).limit(1000).all()

            result = []
            for t in transactions:
                result.append({
                    "id": t.id,
                    "transaction_type": t.transaction_type,
                    "product_name": t.product.name if t.product else None,
                    "warehouse_name": t.warehouse.name if t.warehouse else None,
                    "quantity": self._decimal_to_float(t.quantity),
                    "before_quantity": self._decimal_to_float(t.before_quantity),
                    "after_quantity": self._decimal_to_float(t.after_quantity),
                    "unit_price": self._decimal_to_float(t.unit_price),
                    "total_amount": self._decimal_to_float(t.total_amount),
                    "reference_type": t.reference_type,
                    "transaction_date": t.transaction_date.isoformat() if t.transaction_date else None,
                    "operator": t.operator,
                    "remark": t.remark
                })

            return {
                "success": True,
                "data": result,
                "count": len(result)
            }

    def get_dashboard_summary(self) -> Dict[str, Any]:
        with get_db() as db:
            today = datetime.now().date()
            month_start = today.replace(day=1)

            product_count = db.query(func.count(Product.id)).scalar() or 0
            supplier_count = db.query(func.count(Supplier.id)).filter(Supplier.status == "active").scalar() or 0

            month_shipments = db.query(
                func.count(ShipmentRecord.id),
                func.sum(ShipmentRecord.total_amount)
            ).filter(ShipmentRecord.shipment_date >= month_start).first()

            month_purchases = db.query(
                func.count(PurchaseOrder.id),
                func.sum(PurchaseOrder.total_amount)
            ).filter(PurchaseOrder.order_date >= month_start).first()

            low_stock_count = db.query(func.count(InventoryLedger.id)).filter(
                InventoryLedger.available_quantity <= 0
            ).scalar() or 0

            pending_orders = db.query(func.count(PurchaseOrder.id)).filter(
                PurchaseOrder.status.in_(["draft", "approved"])
            ).scalar() or 0

            return {
                "success": True,
                "data": {
                    "product_count": product_count,
                    "supplier_count": supplier_count,
                    "monthly_sales": {
                        "order_count": month_shipments[0] or 0,
                        "total_amount": self._decimal_to_float(month_shipments[1])
                    },
                    "monthly_purchases": {
                        "order_count": month_purchases[0] or 0,
                        "total_amount": self._decimal_to_float(month_purchases[1])
                    },
                    "alerts": {
                        "low_stock": low_stock_count,
                        "pending_orders": pending_orders
                    }
                }
            }

    def export_to_excel(
        self,
        report_type: str,
        data: List[Dict[str, Any]],
        filename: str
    ) -> Dict[str, Any]:
        try:
            df = pd.DataFrame(data)

            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name=report_type)

            output.seek(0)

            return {
                "success": True,
                "file_path": None,
                "data": output.read(),
                "filename": f"{filename}.xlsx",
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            }
        except Exception as e:
            logger.error(f"导出Excel失败: {e}")
            return {"success": False, "message": str(e)}
