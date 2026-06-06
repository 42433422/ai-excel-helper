from __future__ import annotations

from abc import ABC, abstractmethod


class PurchaseUnitQueryPort(ABC):
    """购买单位只读查询端口（用于后台管理/下拉列表）。"""

    @abstractmethod
    def list_purchase_units(self) -> list[str]:
        raise NotImplementedError
