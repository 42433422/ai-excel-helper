from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class MaterialRepository(ABC):
    """原材料仓储接口 (Port)"""

    @abstractmethod
    def find_all(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, material_id: int) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update(self, material_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, material_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def batch_delete(self, ids: List[int]) -> int:
        raise NotImplementedError

    @abstractmethod
    def find_low_stock(self, threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def export_to_excel(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError
