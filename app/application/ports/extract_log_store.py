from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ExtractLogStorePort(ABC):
    """提取日志仓储端口"""

    @abstractmethod
    def find_all(
        self, page: int = 1, per_page: int = 20, unit_name: str | None = None
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, log_id: int) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def create(self, log_data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, log_id: int) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def clear_old(self, days: int = 30) -> dict[str, Any]:
        raise NotImplementedError
