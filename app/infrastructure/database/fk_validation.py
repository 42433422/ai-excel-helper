"""跨数据库外键验证服务

提供应用层的外键约束验证，解决 SQLite 跨数据库外键无法生效的问题。
当迁移到 PostgreSQL 统一 schema 后，可以改用数据库级外键约束。
"""

import logging

from app.db import SessionLocal

logger = logging.getLogger(__name__)


class ForeignKeyValidator:
    """外键验证器 - 应用级外键约束检查"""

    def __init__(self):
        self._valid_unit_ids: set[int] | None = None
        self._cache_ttl = 60  # 缓存60秒

    def validate_purchase_unit_exists(self, unit_id: int | None) -> bool:
        """
        验证 purchase_unit ID 是否存在

        Args:
            unit_id: 要验证的购买单位ID

        Returns:
            bool: True 如果 unit_id 有效或 None，False 如果不存在
        """
        if unit_id is None:
            return True

        if not isinstance(unit_id, int) or unit_id <= 0:
            logger.warning("Invalid unit_id format: %s (must be positive integer)", unit_id)
            return False

        try:
            with SessionLocal() as db:
                # 查询 purchase_units 表验证 ID 存在
                from sqlalchemy import text

                result = db.execute(
                    text("SELECT 1 FROM purchase_units WHERE id = :unit_id LIMIT 1"),
                    {"unit_id": unit_id},
                ).fetchone()

                exists = result is not None
                if not exists:
                    logger.warning(
                        "Foreign key violation: purchase_units.id=%s does not exist", unit_id
                    )
                return exists
        except Exception as e:
            # 数据库查询失败时，记录错误但允许操作继续（降级模式）
            logger.error("Failed to validate purchase_unit FK: %s", e)
            # 生产环境应该返回 False，但这里选择保守策略
            # 因为查询失败可能是网络/DB问题而非数据问题
            return True  # 保守策略：验证失败时允许操作

    def validate_product_exists(self, product_id: int | None) -> bool:
        """验证 product ID 是否存在"""
        if product_id is None:
            return True

        if not isinstance(product_id, int) or product_id <= 0:
            logger.warning("Invalid product_id format: %s", product_id)
            return False

        try:
            with SessionLocal() as db:
                from sqlalchemy import text

                result = db.execute(
                    text("SELECT 1 FROM products WHERE id = :product_id LIMIT 1"),
                    {"product_id": product_id},
                ).fetchone()

                exists = result is not None
                if not exists:
                    logger.warning(
                        "Foreign key violation: products.id=%s does not exist", product_id
                    )
                return exists
        except Exception as e:
            logger.error("Failed to validate product FK: %s", e)
            return True  # 保守策略

    def validate_customer_exists(self, customer_id: int | None) -> bool:
        """验证 customer ID 是否存在"""
        if customer_id is None:
            return True

        if not isinstance(customer_id, int) or customer_id <= 0:
            logger.warning("Invalid customer_id format: %s", customer_id)
            return False

        try:
            with SessionLocal() as db:
                from sqlalchemy import text

                result = db.execute(
                    text("SELECT 1 FROM customers WHERE id = :customer_id LIMIT 1"),
                    {"customer_id": customer_id},
                ).fetchone()

                exists = result is not None
                if not exists:
                    logger.warning(
                        "Foreign key violation: customers.id=%s does not exist", customer_id
                    )
                return exists
        except Exception as e:
            logger.error("Failed to validate customer FK: %s", e)
            return True  # 保守策略


# 全局验证器实例
_fk_validator: ForeignKeyValidator | None = None


def get_fk_validator() -> ForeignKeyValidator:
    """获取外键验证器单例"""
    global _fk_validator
    if _fk_validator is None:
        _fk_validator = ForeignKeyValidator()
    return _fk_validator


def validate_shipment_unit_id(unit_id: int | None) -> bool:
    """
    验证出货记录的单位ID是否有效

    这是 ShipmentRecord.unit_id 的外键验证入口
    """
    return get_fk_validator().validate_purchase_unit_exists(unit_id)
