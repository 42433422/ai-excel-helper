# -*- coding: utf-8 -*-
"""
产品库服务模块（性能优化版）

提供产品 CRUD 等业务逻辑，集成：
- 多级缓存（Redis + 本地）
- 查询优化
- 请求去重
- 性能监控
- 异步批量操作
"""

import functools
import logging
import time
from typing import Any, Dict, List, Optional

from app.application.ports.product_repository import ProductRepository

logger = logging.getLogger(__name__)

PRODUCT_CACHE_TTL = int(__import__('os').environ.get("XCAGI_PRODUCT_CACHE_TTL", "300"))
PRODUCT_LIST_CACHE_TTL = int(__import__('os').environ.get("XCAGI_PRODUCT_LIST_CACHE_TTL", "60"))


class ProductsService:
    """产品库服务类（性能优化版）"""

    def __init__(self, repository: Optional[ProductRepository] = None):
        if repository is None:
            from app.infrastructure.repositories.product_repository_impl import (
                SQLAlchemyProductRepository,
            )
            repository = SQLAlchemyProductRepository()
        self._repository = repository

        self._cache = None
        self._query_optimizer = None
        self._deduplicator = None
        self._monitor = None

        try:
            from app.utils.performance_initializer import get_performance_optimizer
            optimizer = get_performance_optimizer()

            if optimizer.redis_cache:
                self._cache = optimizer.redis_cache
            if optimizer.query_optimizer:
                self._query_optimizer = optimizer.query_optimizer
            if optimizer.request_deduplicator:
                self._deduplicator = optimizer.request_deduplicator
            if optimizer.performance_monitor:
                self._monitor = optimizer.performance_monitor
        except Exception as e:
            logger.debug(f"性能优化组件加载失败: {e}")

    def set_repository(self, repository: ProductRepository):
        self._repository = repository
        self._invalidate_product_cache()

    @staticmethod
    def _normalize_find_all_result(repo_result: Any) -> tuple[List[Any], int]:
        """
        兼容不同 repository 的 find_all 返回格式。
        支持：
        - (products, total) 元组
        - {"data": [...], "total": n} 字典
        """
        if isinstance(repo_result, tuple) and len(repo_result) >= 2:
            products = repo_result[0] or []
            total = repo_result[1] or 0
            return list(products), int(total)

        if isinstance(repo_result, dict):
            products = repo_result.get("data", []) or []
            total = repo_result.get("total")
            if total is None:
                total = repo_result.get("count", len(products))
            return list(products), int(total)

        # 未知格式时尽量兜底，避免接口直接 500
        if isinstance(repo_result, list):
            return repo_result, len(repo_result)
        return [], 0

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

        start_time = time.perf_counter()
        cache_key = f"products:list:{unit_name}:{model_number}:{keyword}:{page}:{per_page}"

        # 尝试从缓存获取（仅对第一页和简单查询启用缓存）
        use_cache = (page == 1 and not model_number) or (keyword is None)
        if self._cache and use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        repo_result = self._repository.find_all(
            unit_name=unit_name,
            model_number=model_number,
            keyword=keyword,
            page=page,
            per_page=per_page
        )
        products, total = self._normalize_find_all_result(repo_result)

        result = {
            "success": True,
            "data": [p.to_dict() if hasattr(p, 'to_dict') else p for p in products],
            "total": total,
            "count": len(products),
            "_cached": False
        }

        duration_ms = (time.perf_counter() - start_time) * 1000

        if self._monitor:
            self._monitor.record_metric("get_products", duration_ms, success=True, page=page, total=total)

        if self._cache and use_cache:
            self._cache.set(cache_key, result, ttl=PRODUCT_LIST_CACHE_TTL)
            result["_cached"] = True

        return result

    def get_product_units(self) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化", "data": [], "count": 0}

        cache_key = "product_units:all"

        if self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        units = self._repository.find_product_units()
        result = {"success": True, "data": units, "count": len(units)}

        if self._cache:
            self._cache.set(cache_key, result, ttl=PRODUCT_CACHE_TTL * 2)

        return result

    def get_product(self, product_id: int) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化", "data": None}

        cache_key = f"product:{product_id}"

        if self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        result = self._repository.find_by_id(product_id)
        if result is None:
            return {"success": False, "message": "产品不存在", "data": None}

        response = {"success": True, "data": result}

        if self._cache:
            self._cache.set(cache_key, response, ttl=PRODUCT_CACHE_TTL)

        return response

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

            self._invalidate_product_cache()

            return {"success": True, "data": result.to_dict() if hasattr(result, 'to_dict') else result}
        except Exception as e:
            logger.error(f"创建产品失败: {e}")
            return {"success": False, "message": str(e)}

    def update_product(self, product_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化"}

        result = self._repository.update(product_id, data)
        self._invalidate_single_product_cache(product_id)
        return result

    def delete_product(self, product_id: int) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化"}
        success = self._repository.delete(product_id)

        if success:
            self._invalidate_single_product_cache(product_id)
            return {"success": True, "message": "产品删除成功"}
        return {"success": False, "message": "删除失败"}

    def batch_add_products(self, products_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化"}

        start_time = time.perf_counter()

        try:
            if self._query_optimizer and len(products_data) > 10:
                batch_result = self._query_optimizer.batch_execute(
                    products_data,
                    lambda item: self._repository.create_from_dict(item),
                    batch_size=50
                )

                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.info(f"批量添加产品完成: {batch_result.success_count} 成功, {batch_result.failed_count} 失败, 耗时 {duration_ms:.2f}ms")

                self._invalidate_product_cache()

                return {
                    "success": batch_result.failed_count == 0,
                    "data": {
                        "success_count": batch_result.success_count,
                        "failed_count": batch_result.failed_count,
                        "errors": batch_result.errors[:10],
                        "duration_ms": round(duration_ms, 2),
                    }
                }

            result = self._repository.batch_create(products_data)
            self._invalidate_product_cache()
            return result

        except Exception as e:
            logger.error(f"批量添加产品失败: {e}")
            return {"success": False, "message": str(e)}

    def batch_delete_products(self, product_ids: List[int]) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化"}

        start_time = time.perf_counter()
        result = self._repository.batch_delete(product_ids)

        for pid in product_ids:
            self._invalidate_single_product_cache(pid)

        duration_ms = (time.perf_counter() - start_time) * 1000
        if self._monitor:
            self._monitor.record_metric("batch_delete_products", duration_ms, count=len(product_ids))

        return result

    def _product_exists(self, product_id: int) -> bool:
        if self._repository is None:
            return False
        return self._repository.exists(product_id)

    def get_product_names(self, keyword: Optional[str] = None) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化", "data": [], "count": 0}

        cache_key = f"product_names:{keyword or 'all'}"

        if self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        names = self._repository.find_names(keyword)
        result = {"success": True, "data": names, "count": len(names)}

        if self._cache:
            self._cache.set(cache_key, result, ttl=PRODUCT_CACHE_TTL // 2)

        return result

    def export_to_excel(
        self,
        unit_name: Optional[str] = None,
        keyword: Optional[str] = None,
        template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self._repository is None:
            logger.error("ProductRepository 未注入")
            return {"success": False, "message": "服务未正确初始化", "file_path": None, "filename": None}

        start_time = time.perf_counter()
        result = self._repository.export_to_excel(unit_name=unit_name, keyword=keyword, template_id=template_id)

        duration_ms = (time.perf_counter() - start_time) * 1000
        if self._monitor:
            self._monitor.record_metric("export_to_excel", duration_ms, success=result.get("success", False))

        return result

    def _invalidate_product_cache(self):
        """清除所有产品相关缓存"""
        if not self._cache:
            return

        try:
            patterns = [
                "products:list:*",
                "product_units:*",
                "product_names:*",
            ]

            for pattern in patterns:
                self._cache.clear_pattern(pattern)

            logger.debug("产品列表缓存已清除")

        except Exception as e:
            logger.warning(f"清除产品缓存失败: {e}")

    def _invalidate_single_product_cache(self, product_id: int):
        """清除单个产品的缓存"""
        if not self._cache:
            return

        try:
            cache_key = f"product:{product_id}"
            self._cache.delete(cache_key)
        except Exception as e:
            logger.warning(f"清除单产品缓存失败 [{product_id}]: {e}")
