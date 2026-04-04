"""
统一数据访问层 - 收敛所有数据库查询到单一入口

目标：
1. 统一所有 db.query() 调用
2. 提供类型安全的查询接口
3. 支持缓存和性能优化
4. 便于后续迁移到 Repository Pattern
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from app.db.session import get_db

logger = logging.getLogger(__name__)

T = TypeVar("T")


class UnifiedQueryService:
    """统一查询服务"""

    @staticmethod
    def _parse_filter(model_class, key, value):
        """解析过滤条件，支持 Django 风格的查找

        支持: __gte, __gt, __lte, __lt, __ne, __in, __like, __ilike
        """
        LOOKUP_OPS = {
            "__gte": "__ge__",
            "__gt": "__gt__",
            "__lte": "__le__",
            "__lt": "__lt__",
            "__ne": "__ne__",
        }

        for lookup_suffix, op_method in LOOKUP_OPS.items():
            if key.endswith(lookup_suffix):
                field_name = key[: -len(lookup_suffix)]
                if hasattr(model_class, field_name):
                    attr = getattr(model_class, field_name)
                    return getattr(attr, op_method)(value)

        if key.endswith("__in"):
            field_name = key[:-4]
            if hasattr(model_class, field_name):
                return getattr(model_class, field_name).in_(value)

        if key.endswith("__like"):
            field_name = key[:-6]
            if hasattr(model_class, field_name):
                return getattr(model_class, field_name).like(f"%{value}%")

        if key.endswith("__ilike"):
            field_name = key[:-7]
            if hasattr(model_class, field_name):
                return getattr(model_class, field_name).ilike(f"%{value}%")

        # 默认等值匹配
        if hasattr(model_class, key):
            attr = getattr(model_class, key)
            if isinstance(value, list):
                return attr.in_(value)
            return attr == value

        return None

    @staticmethod
    def get_distinct_values(
        model_class: T,
        field_name: str,
        *,
        keyword: Optional[str] = None,
        filter_kwargs: Optional[Dict[str, Any]] = None,
        order_by: str = "asc",
        limit: int = 0,
    ) -> List[Any]:
        """获取去重值列表

        Args:
            model_class: SQLAlchemy 模型类
            field_name: 字段名
            keyword: 模糊搜索关键词
            filter_kwargs: 额外过滤条件
            order_by: 排序方式 (asc/desc)
            limit: 返回数量限制

        Returns:
            去重后的值列表
        """
        with get_db() as db:
            query = db.query(getattr(model_class, field_name))

            if filter_kwargs:
                for key, value in filter_kwargs.items():
                    condition = UnifiedQueryService._parse_filter(model_class, key, value)
                    if condition is not None:
                        query = query.filter(condition)

            if keyword and hasattr(model_class, field_name):
                attr = getattr(model_class, field_name)
                query = query.filter(attr.like(f"%{keyword}%"))

            if order_by == "desc":
                query = query.order_by(getattr(model_class, field_name).desc())
            else:
                query = query.order_by(getattr(model_class, field_name).asc())

            if limit > 0:
                query = query.limit(limit)

            rows = query.distinct().all()
            return [r[0] for r in rows if r and r[0]]

    @staticmethod
    def get_all(
        model_class: T,
        *,
        filter_kwargs: Optional[Dict[str, Any]] = None,
        order_by: Optional[List[tuple]] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[T]:
        """获取记录列表

        Args:
            model_class: SQLAlchemy 模型类
            filter_kwargs: 过滤条件
            order_by: 排序条件 [(field, direction), ...]
            offset: 偏移量
            limit: 数量限制

        Returns:
            记录列表
        """
        with get_db() as db:
            query = db.query(model_class)

            if filter_kwargs:
                for key, value in filter_kwargs.items():
                    condition = UnifiedQueryService._parse_filter(model_class, key, value)
                    if condition is not None:
                        query = query.filter(condition)

            if order_by:
                for field, direction in order_by:
                    attr = getattr(model_class, field, None)
                    if attr:
                        if direction.lower() == "desc":
                            query = query.order_by(attr.desc())
                        else:
                            query = query.order_by(attr.asc())

            return query.offset(offset).limit(limit).all()

    @staticmethod
    def get_first(
        model_class: T,
        **filter_kwargs,
    ) -> Optional[T]:
        """获取单条记录

        Args:
            model_class: SQLAlchemy 模型类
            **filter_kwargs: 过滤条件

        Returns:
            单条记录或 None
        """
        with get_db() as db:
            query = db.query(model_class)

            for key, value in filter_kwargs.items():
                condition = UnifiedQueryService._parse_filter(model_class, key, value)
                if condition is not None:
                    query = query.filter(condition)

            return query.first()

    @staticmethod
    def exists(
        model_class: T,
        **filter_kwargs,
    ) -> bool:
        """检查记录是否存在

        Args:
            model_class: SQLAlchemy 模型类
            **filter_kwargs: 过滤条件

        Returns:
            是否存在
        """
        with get_db() as db:
            query = db.query(model_class)

            for key, value in filter_kwargs.items():
                condition = UnifiedQueryService._parse_filter(model_class, key, value)
                if condition is not None:
                    query = query.filter(condition)

            return query.first() is not None

    @staticmethod
    def count(
        model_class: T,
        **filter_kwargs,
    ) -> int:
        """统计记录数量

        Args:
            model_class: SQLAlchemy 模型类
            **filter_kwargs: 过滤条件

        Returns:
            记录数量
        """
        with get_db() as db:
            query = db.query(model_class)

            for key, value in filter_kwargs.items():
                condition = UnifiedQueryService._parse_filter(model_class, key, value)
                if condition is not None:
                    query = query.filter(condition)

            return query.count()

    @staticmethod
    def delete(
        model_class: T,
        **filter_kwargs,
    ) -> int:
        """删除记录

        Args:
            model_class: SQLAlchemy 模型类
            **filter_kwargs: 过滤条件

        Returns:
            删除的记录数
        """
        with get_db() as db:
            query = db.query(model_class)

            for key, value in filter_kwargs.items():
                condition = UnifiedQueryService._parse_filter(model_class, key, value)
                if condition is not None:
                    query = query.filter(condition)

            count = query.count()
            if count > 0:
                query.delete(synchronize_session=False)
                db.commit()

            return count


# 全局单例
query_service = UnifiedQueryService()


def get_product_names(keyword: Optional[str] = None) -> List[str]:
    """获取产品名称列表"""
    from app.db.models.product import Product

    return query_service.get_distinct_values(
        Product,
        "name",
        keyword=keyword,
        filter_kwargs={"is_active": 1},
        order_by="asc"
    )


def get_purchase_units(keyword: Optional[str] = None) -> List[Dict[str, Any]]:
    """获取购买单位列表"""
    from app.db.models.purchase_unit import PurchaseUnit

    with get_db() as db:
        query = db.query(PurchaseUnit).filter(PurchaseUnit.is_active == True)
        if keyword:
            query = query.filter(PurchaseUnit.unit_name.like(f"%{keyword}%"))
        units = query.order_by(PurchaseUnit.unit_name.asc()).limit(200).all()

        return [
            {
                "id": u.id,
                "unit_name": u.unit_name,
                "contact_person": u.contact_person or "",
                "contact_phone": u.contact_phone or "",
                "address": u.address or "",
            }
            for u in units
        ]


def find_purchase_unit(**kwargs) -> Optional[Dict[str, Any]]:
    """查找单个购买单位"""
    from app.db.models.purchase_unit import PurchaseUnit

    with get_db() as db:
        unit = db.query(PurchaseUnit).filter_by(**kwargs).first()
        if not unit:
            return None

        return {
            "id": unit.id,
            "unit_name": unit.unit_name,
            "contact_person": unit.contact_person or "",
            "contact_phone": unit.contact_phone or "",
            "address": unit.address or "",
        }


def find_product(**kwargs) -> Optional[Dict[str, Any]]:
    """查找单个产品"""
    from app.db.models.product import Product

    with get_db() as db:
        product = db.query(Product).filter_by(**kwargs).first()
        if not product:
            return None

        return {
            "id": product.id,
            "name": product.name,
            "model_number": product.model_number or "",
            "specification": product.specification or "",
            "price": float(product.price or 0),
            "quantity": product.quantity or 0,
            "unit": product.unit or "个",
            "category": product.category or "",
            "brand": product.brand or "",
        }


def check_purchase_unit_exists(unit_name: str) -> bool:
    """检查购买单位是否存在"""
    from app.db.models.purchase_unit import PurchaseUnit

    return query_service.exists(PurchaseUnit, unit_name=unit_name)


def delete_purchase_unit(**kwargs) -> int:
    """删除购买单位"""
    from app.db.models.purchase_unit import PurchaseUnit

    return query_service.delete(PurchaseUnit, **kwargs)
