from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ProductRepository(ABC):
    """产品仓储接口 (Port)"""

    @abstractmethod
    def find_all(
        self,
        unit_name: Optional[str] = None,
        model_number: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def find_product_units(self) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update(self, product_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, product_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def batch_create(self, products_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def batch_delete(self, product_ids: List[int]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def find_names(self, keyword: Optional[str] = None) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def exists(self, product_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def export_to_excel(
        self,
        unit_name: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        raise NotImplementedError
