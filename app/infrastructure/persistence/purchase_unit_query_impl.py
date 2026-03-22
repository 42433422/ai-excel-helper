from __future__ import annotations

from typing import List

from app.application.ports.purchase_unit_query import PurchaseUnitQueryPort
from app.db.models import PurchaseUnit
from app.infrastructure.repositories.customer_repository_impl import get_customers_session


class SQLAlchemyPurchaseUnitQuery(PurchaseUnitQueryPort):
    """从 customers.db.purchase_units 表读取购买单位列表（去重保序）。"""

    def list_purchase_units(self) -> List[str]:
        session = get_customers_session()
        try:
            rows = session.query(PurchaseUnit.unit_name).filter(PurchaseUnit.is_active == True).all()
            names: List[str] = [c[0] for c in rows if c and c[0]]
            seen = set()
            result: List[str] = []
            for n in names:
                if n in seen:
                    continue
                seen.add(n)
                result.append(n)
            return result
        finally:
            session.close()

