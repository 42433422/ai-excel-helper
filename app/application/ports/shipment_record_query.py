from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ShipmentRecordQueryPort(ABC):
    """出货记录查询端口（Read side）。"""

    @abstractmethod
    def query_shipments(
        self,
        *,
        unit_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        返回与历史接口尽量一致的结构：
        {
          "success": bool,
          "data": List[Dict[str, Any]],
          "total": int,
          "page": int,
          "per_page": int
        }
        """
        raise NotImplementedError

    @abstractmethod
    def search_shipments(self, query: str) -> List[Dict[str, Any]]:
        """在 shipment_records 中模糊搜索（purchase_unit/product_name/model_number）。"""
        raise NotImplementedError

    @abstractmethod
    def get_shipment_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """根据 shipment_records.id 查询单条记录（用于 GET /orders/<order_number>）。"""
        raise NotImplementedError

    @abstractmethod
    def get_latest_shipments(self, limit: int) -> List[Dict[str, Any]]:
        """获取最近创建的 shipment_records（用于 GET /orders/latest）。"""
        raise NotImplementedError

    @abstractmethod
    def get_shipment_records(
        self,
        unit_name: Optional[str] = None,
        *,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """获取 shipment_records 列表（用于后台管理接口）。"""
        raise NotImplementedError

