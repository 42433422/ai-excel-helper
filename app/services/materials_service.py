# -*- coding: utf-8 -*-
"""
原材料管理服务
"""
import logging
from typing import Any, Dict, List, Optional

from app.application.ports.material_repository import MaterialRepository

logger = logging.getLogger(__name__)


class MaterialsService:
    """原材料管理服务类"""

    def __init__(self, repository: Optional[MaterialRepository] = None):
        if repository is None:
            from app.application.ports.material_repository import MaterialRepository
            repository = MaterialRepository()
        self._repository = repository

    def set_repository(self, repository: MaterialRepository):
        self._repository = repository

    def get_all_materials(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("MaterialRepository 未注入")
            return {
                "success": False,
                "message": "服务未正确初始化",
                "data": [],
                "total": 0
            }
        return self._repository.find_all(search=search, category=category, page=page, per_page=per_page)

    def get_material_by_id(self, material_id: int) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("MaterialRepository 未注入")
            return {
                "success": False,
                "message": "服务未正确初始化"
            }
        result = self._repository.find_by_id(material_id)
        if result is None:
            return {
                "success": False,
                "message": "原材料不存在"
            }
        return {
            "success": True,
            "data": result
        }

    def create_material(
        self,
        material_code: str,
        name: str,
        category: Optional[str] = None,
        specification: Optional[str] = None,
        unit: str = "个",
        quantity: float = 0,
        unit_price: float = 0,
        supplier: Optional[str] = None,
        warehouse_location: Optional[str] = None,
        min_stock: float = 0,
        max_stock: float = 0,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("MaterialRepository 未注入")
            return {
                "success": False,
                "message": "服务未正确初始化"
            }
        data = {
            "material_code": material_code,
            "name": name,
            "category": category,
            "specification": specification,
            "unit": unit,
            "quantity": quantity,
            "unit_price": unit_price,
            "supplier": supplier,
            "warehouse_location": warehouse_location,
            "min_stock": min_stock,
            "max_stock": max_stock,
            "description": description,
        }
        return self._repository.create(data)

    def update_material(
        self,
        material_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("MaterialRepository 未注入")
            return {
                "success": False,
                "message": "服务未正确初始化"
            }
        return self._repository.update(material_id, kwargs)

    def delete_material(self, material_id: int) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("MaterialRepository 未注入")
            return {
                "success": False,
                "message": "服务未正确初始化"
            }
        success = self._repository.delete(material_id)
        if success:
            return {
                "success": True,
                "message": "原材料删除成功"
            }
        return {
            "success": False,
            "message": "删除失败"
        }

    def batch_delete_materials(self, ids: List[int]) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("MaterialRepository 未注入")
            return {
                "success": False,
                "message": "服务未正确初始化"
            }
        deleted_count = self._repository.batch_delete(ids)
        return {
            "success": True,
            "message": f"已删除 {deleted_count} 条记录",
            "deleted_count": deleted_count
        }

    def get_low_stock_materials(
        self,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("MaterialRepository 未注入")
            return {
                "success": False,
                "message": "服务未正确初始化",
                "data": [],
                "count": 0
            }
        materials = self._repository.find_low_stock(threshold)
        return {
            "success": True,
            "data": materials,
            "count": len(materials)
        }
