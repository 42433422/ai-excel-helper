from __future__ import annotations

from app.application.ports.purchase_unit_query import PurchaseUnitQueryPort
from app.db.models import PurchaseUnit
from app.db.models.shipment import ShipmentRecord
from app.db.session import get_db


class SQLAlchemyPurchaseUnitQuery(PurchaseUnitQueryPort):
    """从 products.db.purchase_units 表读取客户名称列表（去重保序）。"""

    def list_purchase_units(self) -> list[str]:
        with get_db() as db:
            rows = db.query(PurchaseUnit.unit_name).filter(PurchaseUnit.is_active == True).all()
            names: list[str] = [c[0] for c in rows if c and c[0]]
            seen = set()
            result: list[str] = []
            for n in names:
                if n in seen:
                    continue
                seen.add(n)
                result.append(n)
            return result

    def get_shipment_records_by_unit(
        self, unit_name: str | None = None, limit: int = 100
    ) -> list[dict]:
        """获取出货记录列表"""
        with get_db() as db:
            query = db.query(ShipmentRecord)
            if unit_name:
                query = query.filter(ShipmentRecord.purchase_unit == unit_name)
            records = query.order_by(ShipmentRecord.created_at.desc()).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "purchase_unit": r.purchase_unit,
                    "product_name": r.product_name,
                    "model_number": r.model_number,
                    "quantity_kg": r.quantity_kg,
                    "quantity_tins": r.quantity_tins,
                    "tin_spec": r.tin_spec,
                    "unit_price": r.unit_price,
                    "amount": r.amount,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                    "printed_at": r.printed_at.isoformat() if r.printed_at else None,
                    "printer_name": r.printer_name,
                }
                for r in records
            ]
