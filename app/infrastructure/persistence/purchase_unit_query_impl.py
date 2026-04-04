from __future__ import annotations

from typing import List

from app.application.ports.purchase_unit_query import PurchaseUnitQueryPort
from app.db.models import PurchaseUnit
from app.db.session import get_db


class SQLAlchemyPurchaseUnitQuery(PurchaseUnitQueryPort):
    """从 products.db.purchase_units 表读取购买单位列表（去重保序）。"""

    def list_purchase_units(self) -> List[str]:
        with get_db() as db:
            rows = db.query(PurchaseUnit.unit_name).filter(PurchaseUnit.is_active == True).all()
            names: List[str] = [c[0] for c in rows if c and c[0]]
            seen = set()
            result: List[str] = []
            for n in names:
                if n in seen:
                    continue
                seen.add(n)
                result.append(n)
            return result
