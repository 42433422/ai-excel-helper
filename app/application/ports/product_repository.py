from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ProductRepository(ABC):
    """产品仓储接口 (Port)"""

    @abstractmethod
    def find_all(
        self,
        unit_name: str | None = None,
        model_number: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, product_id: int) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def find_product_units(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update(self, product_id: int, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, product_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def batch_create(self, products_data: list[dict[str, Any]]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def batch_delete(self, product_ids: list[int]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def find_names(self, keyword: str | None = None) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def exists(self, product_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def export_to_excel(
        self,
        unit_name: str | None = None,
        keyword: str | None = None,
        template_id: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError
