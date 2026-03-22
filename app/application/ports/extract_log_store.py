from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ExtractLogStorePort(ABC):
    """提取日志仓储端口"""

    @abstractmethod
    def find_all(
        self,
        page: int = 1,
        per_page: int = 20,
        unit_name: Optional[str] = None
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, log_id: int) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def create(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, log_id: int) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def clear_old(self, days: int = 30) -> Dict[str, Any]:
        raise NotImplementedError
