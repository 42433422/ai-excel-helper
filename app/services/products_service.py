# -*- coding: utf-8 -*-
"""
产品库服务模块

提供产品 CRUD 等业务逻辑。
"""

import logging
from typing import Any, Dict, List, Optional

from app.application.ports.product_repository import ProductRepository

logger = logging.getLogger(__name__)


class ProductsService:
    """产品库服务类"""

    def __init__(self, repository: Optional[ProductRepository] = None):
        if repository is None:
            from app.infrastructure.repositories.product_repository_impl import (
                SQLAlchemyProductRepository,
            )
            repository = SQLAlchemyProductRepository()
        self._repository = repository

    def set_repository(self, repository: ProductRepository):
        self._repository = repository

    def get_products(
        self,
        unit_name: Optional[str] = None,
        model_number: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {
                "success": False,
                "message": "服务未正确初始化",
                "data": [],
                "total": 0
            }
        products, total = self._repository.find_all(
            unit_name=unit_name,
            model_number=model_number,
            keyword=keyword,
            page=page,
            per_page=per_page
        )
        return {
            "success": True,
            "data": [p.to_dict() if hasattr(p, 'to_dict') else p for p in products],
            "total": total,
            "count": len(products)
        }

    def get_product_units(self) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化", "data": [], "count": 0}
        units = self._repository.find_product_units()
        return {"success": True, "data": units, "count": len(units)}

    def get_product(self, product_id: int) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化", "data": None}
        result = self._repository.find_by_id(product_id)
        if result is None:
            return {"success": False, "message": "产品不存在", "data": None}
        return {"success": True, "data": result}

    def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化"}

        try:
            from app.domain.product.entities import Product
            from app.domain.value_objects import ModelNumber, Money

            product = Product(
                name=data.get("name", ""),
                category=data.get("category", ""),
                specification=data.get("specification", ""),
                quantity=int(data.get("quantity", 0)),
                price=Money(float(data.get("unit_price", 0))),
                unit=data.get("unit", "个"),
                description=data.get("description", ""),
                brand=data.get("brand", ""),
                model_number=ModelNumber(data.get("product_code", "")) if data.get("product_code") else None,
            )
            result = self._repository.create(product)
            return {"success": True, "data": result.to_dict() if hasattr(result, 'to_dict') else result}
        except Exception as e:
            logger.error(f"创建产品失败: {e}")
            return {"success": False, "message": str(e)}

    def update_product(self, product_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化"}
        return self._repository.update(product_id, data)

    def delete_product(self, product_id: int) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化"}
        success = self._repository.delete(product_id)
        if success:
            return {"success": True, "message": "产品删除成功"}
        return {"success": False, "message": "删除失败"}

    def batch_add_products(self, products_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化"}
        return self._repository.batch_create(products_data)

    def batch_delete_products(self, product_ids: List[int]) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化"}
        return self._repository.batch_delete(product_ids)

    def _product_exists(self, product_id: int) -> bool:
        if self._repository is None:
            return False
        return self._repository.exists(product_id)

    def get_product_names(self, keyword: Optional[str] = None) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化", "data": [], "count": 0}
        names = self._repository.find_names(keyword)
        return {"success": True, "data": names, "count": len(names)}

    def export_to_excel(self, unit_name: Optional[str] = None, keyword: Optional[str] = None) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化", "file_path": None, "filename": None}
        return self._repository.export_to_excel(unit_name=unit_name, keyword=keyword)
