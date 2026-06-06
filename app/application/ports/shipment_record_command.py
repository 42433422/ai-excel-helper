from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ShipmentRecordCommandPort(ABC):
    """shipment_records 写操作端口（Command side）。"""

    @abstractmethod
    def clear_all(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def clear_by_unit(self, purchase_unit: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update_record(
        self,
        record_id: int,
        *,
        unit_name: str | None = None,
        date: str | None = None,
        fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def delete_record(self, record_id: int) -> dict[str, Any]:
        raise NotImplementedError
