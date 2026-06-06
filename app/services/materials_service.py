"""
原材料管理服务
"""

import logging
from typing import Any

from app.application.ports.material_repository import MaterialRepository
from app.neuro_bus.event_publisher_mixin import NeuroEventPublisherMixin

logger = logging.getLogger(__name__)


class MaterialsService(NeuroEventPublisherMixin):
    """原材料管理服务类"""

    def __init__(self, repository: MaterialRepository | None = None):
        if repository is None:
            from app.application.ports.material_repository import MaterialRepository

            repository = MaterialRepository()
        self._repository = repository

    def set_repository(self, repository: MaterialRepository):
        self._repository = repository

    def get_all_materials(
        self,
        search: str | None = None,
        category: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        if self._repository is None:
            logger.error("MaterialRepository 未注入")
            return {"success": False, "message": "服务未正确初始化", "data": [], "total": 0}
        return self._repository.find_all(
            search=search, category=category, page=page, per_page=per_page
        )

    def get_material_by_id(self, material_id: int) -> dict[str, Any]:
        if self._repository is None:
            logger.error("MaterialRepository 未注入")
            return {"success": False, "message": "服务未正确初始化"}
        result = self._repository.find_by_id(material_id)
        if result is None:
            return {"success": False, "message": "原材料不存在"}
        return {"success": True, "data": result}

    def create_material(
        self,
        material_code: str,
        name: str,
        category: str | None = None,
        specification: str | None = None,
        unit: str = "个",
        quantity: float = 0,
        unit_price: float = 0,
        supplier: str | None = None,
        warehouse_location: str | None = None,
        min_stock: float = 0,
        max_stock: float = 0,
        description: str | None = None,
    ) -> dict[str, Any]:
        if self._repository is None:
            logger.error("MaterialRepository 未注入")
            return {"success": False, "message": "服务未正确初始化"}
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

    def update_material(self, material_id: int, **kwargs) -> dict[str, Any]:
        if self._repository is None:
            logger.error("MaterialRepository 未注入")
            return {"success": False, "message": "服务未正确初始化"}
        return self._repository.update(material_id, kwargs)

    def delete_material(self, material_id: int) -> dict[str, Any]:
        if self._repository is None:
            logger.error("MaterialRepository 未注入")
            return {"success": False, "message": "服务未正确初始化"}
        success = self._repository.delete(material_id)
        if success:
            return {"success": True, "message": "原材料删除成功"}
        return {"success": False, "message": "删除失败"}

    def batch_delete_materials(self, ids: list[int]) -> dict[str, Any]:
        if self._repository is None:
            logger.error("MaterialRepository 未注入")
            return {"success": False, "message": "服务未正确初始化"}
        deleted_count = self._repository.batch_delete(ids)
        return {
            "success": True,
            "message": f"已删除 {deleted_count} 条记录",
            "deleted_count": deleted_count,
        }

    def get_low_stock_materials(self, threshold: float | None = None) -> dict[str, Any]:
        if self._repository is None:
            logger.error("MaterialRepository 未注入")
            return {"success": False, "message": "服务未正确初始化", "data": [], "count": 0}
        materials = self._repository.find_low_stock(threshold)
        return {"success": True, "data": materials, "count": len(materials)}


# NEURO-DDD: 为 Services 层类添加 instrumentation
from app.neuro_bus.neuro_service_instrumentation import instrument_service_layer_class

instrument_service_layer_class(MaterialsService, "app.services.materials_service")
