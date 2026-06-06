from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MaterialRepository(ABC):
    """原材料仓储接口 (Port)"""

    @abstractmethod
    def find_all(
        self,
        search: str | None = None,
        category: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, material_id: int) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update(self, material_id: int, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, material_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def batch_delete(self, ids: list[int]) -> int:
        raise NotImplementedError

    @abstractmethod
    def find_low_stock(self, threshold: float | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def export_to_excel(
        self,
        search: str | None = None,
        category: str | None = None,
        template_id: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError
