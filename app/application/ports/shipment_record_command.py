from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ShipmentRecordCommandPort(ABC):
    """shipment_records 写操作端口（Command side）。"""

    @abstractmethod
    def clear_all(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def clear_by_unit(self, purchase_unit: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update_record(
        self,
        record_id: int,
        *,
        unit_name: Optional[str] = None,
        date: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def delete_record(self, record_id: int) -> Dict[str, Any]:
        raise NotImplementedError

