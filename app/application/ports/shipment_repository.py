from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.shipment.aggregates import Shipment


class ShipmentRepository(ABC):
    """发货单仓储接口 (Port)。"""

    @abstractmethod
    def save(self, shipment: Shipment) -> Shipment:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, shipment_id: int) -> Shipment | None:
        raise NotImplementedError

    @abstractmethod
    def find_by_order_number(self, order_number: str) -> Shipment | None:
        raise NotImplementedError

    @abstractmethod
    def find_all(self, page: int = 1, per_page: int = 20) -> list[Shipment]:
        raise NotImplementedError

    @abstractmethod
    def find_by_unit(self, unit_name: str) -> list[Shipment]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, shipment_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError
