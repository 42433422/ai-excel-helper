"""
原材料应用服务

负责原材料管理相关的用例编排
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from app.application.ports.material_repository import MaterialRepository


class MaterialApplicationService:
    """原材料应用服务 - 负责原材料相关的用例编排"""

    def __init__(
        self,
        repository: Optional["MaterialRepository"] = None,
    ):
        if repository is None:
            from app.infrastructure.persistence.material_repository_impl import (
                SQLAlchemyMaterialRepository,
            )
            repository = SQLAlchemyMaterialRepository()
        self._repository = repository

    def get_materials(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        return self._repository.find_all(
            search=search,
            category=category,
            page=page,
            per_page=per_page
        )

    def get_all_materials(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        return self.get_materials(search, category, page, per_page)

    def get_material(self, material_id: int) -> Dict[str, Any]:
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

    def get_material_by_id(self, material_id: int) -> Dict[str, Any]:
        return self.get_material(material_id)

    def create_material(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        if data is None:
            data = kwargs
        else:
            data = {**data, **kwargs}
        material_name = data.get("material_name") or data.get("name")

        if not material_name:
            return {
                "success": False,
                "message": "原材料名称不能为空"
            }

        if "price" in data and data["price"] < 0:
            return {
                "success": False,
                "message": "价格不能为负数"
            }

        if "unit_price" in data and data["unit_price"] < 0:
            return {
                "success": False,
                "message": "价格不能为负数"
            }

        create_data = {
            "material_code": data.get("material_code", ""),
            "name": material_name,
            "category": data.get("category"),
            "specification": data.get("specification"),
            "unit": data.get("unit", "个"),
            "quantity": data.get("quantity", 0),
            "unit_price": data.get("unit_price", data.get("price", 0)),
            "supplier": data.get("supplier"),
            "warehouse_location": data.get("warehouse_location"),
            "min_stock": data.get("min_stock", 0),
            "max_stock": data.get("max_stock", 0),
            "description": data.get("description"),
        }

        result = self._repository.create(create_data)

        if result.get("success"):
            self._log_action("create_material", material_id=result.get("data", {}).get("id"), data=data)

        return result

    def update_material(self, material_id: int, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        update_data = data or kwargs

        if not update_data:
            return {
                "success": False,
                "message": "更新数据不能为空"
            }

        if "price" in update_data and update_data["price"] < 0:
            return {
                "success": False,
                "message": "价格不能为负数"
            }

        if "unit_price" in update_data and update_data["unit_price"] < 0:
            return {
                "success": False,
                "message": "价格不能为负数"
            }

        result = self._repository.update(material_id, update_data)

        if result.get("success"):
            self._log_action("update_material", material_id=material_id, data=update_data)

        return result

    def delete_material(self, material_id: int) -> Dict[str, Any]:
        success = self._repository.delete(material_id)
        if success:
            self._log_action("delete_material", material_id=material_id)
            return {
                "success": True,
                "message": "原材料删除成功"
            }
        return {
            "success": False,
            "message": "删除失败"
        }

    def batch_delete_materials(self, ids: List[int]) -> Dict[str, Any]:
        deleted_count = self._repository.batch_delete(ids)
        return {
            "success": True,
            "message": f"已删除 {deleted_count} 条记录",
            "deleted_count": deleted_count
        }

    def get_low_stock_materials(self, threshold: Optional[float] = None) -> Dict[str, Any]:
        materials = self._repository.find_low_stock(threshold)
        return {
            "success": True,
            "data": materials,
            "count": len(materials)
        }

    def get_material_statistics(self, category: Optional[str] = None) -> Dict[str, Any]:
        result = self._repository.find_all(
            category=category,
            page=1,
            per_page=1
        )
        total = result.get("total", 0)

        return {
            "success": True,
            "data": {
                "total_materials": total,
                "category": category or "全部",
                "statistics_time": datetime.now().isoformat()
            }
        }

    def export_to_excel(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._repository.export_to_excel(search=search, category=category, template_id=template_id)

    def _log_action(self, action: str, **kwargs):
        pass


_material_app_service: Optional[MaterialApplicationService] = None


def get_material_application_service() -> "MaterialApplicationService":
    """获取原材料应用服务单例"""
    global _material_app_service
    if _material_app_service is None:
        _material_app_service = MaterialApplicationService()
    return _material_app_service


def get_material_app_service() -> "MaterialApplicationService":
    """获取原材料应用服务单例 (别名)"""
    return get_material_application_service()


def init_material_application_service(
    repository: "MaterialRepository",
) -> "MaterialApplicationService":
    """初始化原材料应用服务 (用于依赖注入)"""
    global _material_app_service
    _material_app_service = MaterialApplicationService(
        repository=repository
    )
    return _material_app_service