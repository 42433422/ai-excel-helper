"""
财务应用服务

聚合两类数据来源：
1. 实时派生：从 ShipmentRecord（销售收入/AR）和 PurchaseOrder（采购支出/AP）聚合。
2. 手动凭证：通过 FinancialTransaction 表记录手工收付款、账期调整等。

消失条件：当引入正式 ERP 总账模块时，本模块迁移为 GL 适配器。
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func

from app.db.models.finance import FinancialTransaction
from app.db.models.purchase import PurchaseOrder, Supplier
from app.db.models.shipment import ShipmentRecord
from app.db.session import get_db

logger = logging.getLogger(__name__)


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    return float(v)


class FinanceAppService:
    """财务应用服务"""

    # ── 财务看板 ─────────────────────────────────────────────────

    def get_dashboard(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """财务总览：收入、成本、应收、应付、毛利。"""
        with get_db() as db:
            # 销售收入（出货单金额汇总）
            shipment_q = db.query(func.sum(ShipmentRecord.amount))
            if start_date:
                shipment_q = shipment_q.filter(ShipmentRecord.created_at >= start_date)
            if end_date:
                shipment_q = shipment_q.filter(ShipmentRecord.created_at <= end_date)
            total_revenue = _to_float(shipment_q.scalar()) or 0.0

            # 采购成本（采购订单实际支付额）
            purchase_q = db.query(func.sum(PurchaseOrder.paid_amount))
            if start_date:
                purchase_q = purchase_q.filter(PurchaseOrder.order_date >= start_date)
            if end_date:
                purchase_q = purchase_q.filter(PurchaseOrder.order_date <= end_date)
            total_cost = _to_float(purchase_q.scalar()) or 0.0

            # 应付款（采购订单中 total_amount - paid_amount，状态非 cancelled）
            ap_q = db.query(
                func.sum(PurchaseOrder.total_amount - PurchaseOrder.paid_amount)
            ).filter(PurchaseOrder.status.notin_(["cancelled", "completed"]))
            total_payable = _to_float(ap_q.scalar()) or 0.0

            # 手工凭证汇总
            manual_receipt = (
                _to_float(
                    db.query(func.sum(FinancialTransaction.amount))
                    .filter(FinancialTransaction.transaction_type == "receipt")
                    .filter(FinancialTransaction.status == "completed")
                    .scalar()
                )
                or 0.0
            )

            manual_payment = (
                _to_float(
                    db.query(func.sum(FinancialTransaction.amount))
                    .filter(FinancialTransaction.transaction_type == "payment")
                    .filter(FinancialTransaction.status == "completed")
                    .scalar()
                )
                or 0.0
            )

            gross_profit = total_revenue - total_cost
            gross_margin = (gross_profit / total_revenue * 100) if total_revenue else 0.0

            return {
                "success": True,
                "data": {
                    "total_revenue": total_revenue,
                    "total_cost": total_cost,
                    "gross_profit": round(gross_profit, 2),
                    "gross_margin_pct": round(gross_margin, 2),
                    "total_payable": round(total_payable, 2),
                    "manual_receipt": manual_receipt,
                    "manual_payment": manual_payment,
                    "period": {
                        "start": start_date.isoformat() if start_date else None,
                        "end": end_date.isoformat() if end_date else None,
                    },
                },
            }

    # ── 应收账款 ─────────────────────────────────────────────────

    def get_receivables(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        """应收账款列表（来自 FinancialTransaction receivable 类型）。"""
        with get_db() as db:
            q = db.query(FinancialTransaction).filter(
                FinancialTransaction.transaction_type.in_(["receivable", "receipt"])
            )
            if start_date:
                q = q.filter(FinancialTransaction.transaction_date >= start_date)
            if end_date:
                q = q.filter(FinancialTransaction.transaction_date <= end_date)
            if status:
                q = q.filter(FinancialTransaction.status == status)

            total = q.count()
            items = (
                q.order_by(FinancialTransaction.transaction_date.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            return {
                "success": True,
                "data": [i.to_dict() for i in items],
                "total": total,
                "page": page,
                "per_page": per_page,
            }

    # ── 应付账款 ─────────────────────────────────────────────────

    def get_payables(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        """应付账款列表（来自采购订单 + FinancialTransaction payable 类型）。"""
        with get_db() as db:
            q = (
                db.query(PurchaseOrder)
                .join(Supplier, PurchaseOrder.supplier_id == Supplier.id, isouter=True)
                .filter(PurchaseOrder.status.notin_(["cancelled"]))
            )

            if start_date:
                q = q.filter(PurchaseOrder.order_date >= start_date)
            if end_date:
                q = q.filter(PurchaseOrder.order_date <= end_date)
            if status:
                q = q.filter(PurchaseOrder.status == status)

            total = q.count()
            orders = (
                q.order_by(PurchaseOrder.order_date.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )

            data = []
            for o in orders:
                data.append(
                    {
                        "id": o.id,
                        "order_no": o.order_no,
                        "supplier_name": o.supplier.name if o.supplier else None,
                        "total_amount": _to_float(o.total_amount),
                        "paid_amount": _to_float(o.paid_amount),
                        "outstanding": _to_float(o.total_amount - (o.paid_amount or 0)),
                        "status": o.status,
                        "order_date": o.order_date.isoformat() if o.order_date else None,
                        "delivery_date": o.delivery_date.isoformat() if o.delivery_date else None,
                    }
                )

            return {
                "success": True,
                "data": data,
                "total": total,
                "page": page,
                "per_page": per_page,
            }

    # ── 收支流水（手工凭证 CRUD）────────────────────────────────────

    def list_transactions(
        self,
        transaction_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        with get_db() as db:
            q = db.query(FinancialTransaction)
            if transaction_type:
                q = q.filter(FinancialTransaction.transaction_type == transaction_type)
            if start_date:
                q = q.filter(FinancialTransaction.transaction_date >= start_date)
            if end_date:
                q = q.filter(FinancialTransaction.transaction_date <= end_date)
            if status:
                q = q.filter(FinancialTransaction.status == status)

            total = q.count()
            items = (
                q.order_by(FinancialTransaction.transaction_date.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            return {
                "success": True,
                "data": [i.to_dict() for i in items],
                "total": total,
                "page": page,
                "per_page": per_page,
            }

    def get_transaction(self, txn_id: int) -> dict[str, Any]:
        with get_db() as db:
            txn = db.query(FinancialTransaction).filter(FinancialTransaction.id == txn_id).first()
            if not txn:
                return {"success": False, "message": "凭证不存在"}
            return {"success": True, "data": txn.to_dict()}

    def create_transaction(self, data: dict[str, Any]) -> dict[str, Any]:
        with get_db() as db:
            try:
                txn = FinancialTransaction(
                    transaction_type=data["transaction_type"],
                    amount=Decimal(str(data["amount"])),
                    currency=data.get("currency", "CNY"),
                    reference_type=data.get("reference_type"),
                    reference_id=data.get("reference_id"),
                    description=data.get("description"),
                    transaction_date=_parse_dt(data.get("transaction_date")) or datetime.utcnow(),
                    due_date=_parse_dt(data.get("due_date")),
                    status=data.get("status", "pending"),
                    counterparty_name=data.get("counterparty_name"),
                    counterparty_id=data.get("counterparty_id"),
                    created_by=data.get("created_by"),
                )
                db.add(txn)
                db.commit()
                db.refresh(txn)
                return {"success": True, "data": txn.to_dict()}
            except Exception as e:
                db.rollback()
                logger.error("create_transaction failed: %s", e)
                return {"success": False, "message": str(e)}

    def update_transaction(self, txn_id: int, data: dict[str, Any]) -> dict[str, Any]:
        with get_db() as db:
            try:
                txn = (
                    db.query(FinancialTransaction).filter(FinancialTransaction.id == txn_id).first()
                )
                if not txn:
                    return {"success": False, "message": "凭证不存在"}

                updatable = {
                    "amount",
                    "currency",
                    "description",
                    "status",
                    "due_date",
                    "transaction_date",
                    "counterparty_name",
                    "counterparty_id",
                    "reference_type",
                    "reference_id",
                }
                for k, v in data.items():
                    if k in updatable and v is not None:
                        if k == "amount":
                            v = Decimal(str(v))
                        elif k in ("transaction_date", "due_date"):
                            v = _parse_dt(v)
                        setattr(txn, k, v)
                txn.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(txn)
                return {"success": True, "data": txn.to_dict()}
            except Exception as e:
                db.rollback()
                logger.error("update_transaction failed: %s", e)
                return {"success": False, "message": str(e)}

    def delete_transaction(self, txn_id: int) -> dict[str, Any]:
        with get_db() as db:
            try:
                txn = (
                    db.query(FinancialTransaction).filter(FinancialTransaction.id == txn_id).first()
                )
                if not txn:
                    return {"success": False, "message": "凭证不存在"}
                db.delete(txn)
                db.commit()
                return {"success": True, "message": "凭证已删除"}
            except Exception as e:
                db.rollback()
                logger.error("delete_transaction failed: %s", e)
                return {"success": False, "message": str(e)}

    # ── 月度趋势 ────────────────────────────────────────────────

    def get_monthly_trend(self, year: int | None = None) -> dict[str, Any]:
        """按月统计收入/支出趋势（最近12个月）。"""
        import calendar
        from datetime import date

        target_year = year or datetime.utcnow().year
        with get_db() as db:
            months = []
            for m in range(1, 13):
                month_start = datetime(target_year, m, 1)
                last_day = calendar.monthrange(target_year, m)[1]
                month_end = datetime(target_year, m, last_day, 23, 59, 59)

                revenue = (
                    _to_float(
                        db.query(func.sum(ShipmentRecord.amount))
                        .filter(
                            ShipmentRecord.created_at >= month_start,
                            ShipmentRecord.created_at <= month_end,
                        )
                        .scalar()
                    )
                    or 0.0
                )

                cost = (
                    _to_float(
                        db.query(func.sum(PurchaseOrder.paid_amount))
                        .filter(
                            PurchaseOrder.order_date >= month_start,
                            PurchaseOrder.order_date <= month_end,
                        )
                        .scalar()
                    )
                    or 0.0
                )

                months.append(
                    {
                        "month": f"{target_year}-{m:02d}",
                        "revenue": revenue,
                        "cost": cost,
                        "profit": round(revenue - cost, 2),
                    }
                )

            return {"success": True, "data": months, "year": target_year}


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None
