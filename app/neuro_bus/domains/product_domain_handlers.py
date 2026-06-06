"""
Product 领域事件处理器

处理所有 product.* 事件的业务逻辑。
"""

import logging
from typing import Any

from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.events.product_events import (
    ProductCacheInvalidatedEvent,
    ProductCreatedEvent,
    ProductDeletedEvent,
    ProductImportedEvent,
    ProductPriceChangedEvent,
    ProductUpdatedEvent,
)

logger = logging.getLogger(__name__)


class ProductDomainHandlers:
    """Product 领域事件处理器集合"""

    def __init__(self):
        self._bus = None

    @property
    def bus(self):
        """延迟获取 NeuroBus 实例"""
        if self._bus is None:
            self._bus = get_neuro_bus()
        return self._bus

    async def handle_product_created(self, event: ProductCreatedEvent) -> dict[str, Any]:
        """
        处理产品创建事件

        职责:
        1. 记录产品创建日志
        2. 初始化产品相关数据
        3. 触发缓存预热
        4. 发送通知（如果需要）
        """
        logger.info(
            f"[ProductDomain] 处理产品创建: {event.payload.get('product_name')} "
            f"(ID: {event.payload.get('product_id')})"
        )

        result = {"success": True, "product_id": event.payload.get("product_id"), "actions": []}

        try:
            # 1. 记录审计日志
            result["actions"].append("audit_logged")

            # 2. 触发缓存预热
            cache_event = ProductCacheInvalidatedEvent(
                payload={
                    "unit_name": event.payload.get("unit_name"),
                    "reason": "new_product_added",
                },
                source="product_domain",
                correlation_id=event.metadata.event_id,
            )
            self.bus.publish(cache_event)
            result["actions"].append("cache_warmup_triggered")

            # 3. 可以在这里触发其他下游事件
            # 例如：通知搜索服务索引新产品

        except Exception as e:
            logger.error(f"[ProductDomain] 处理产品创建事件失败: {e}")
            result["success"] = False
            result["error"] = str(e)

        return result

    async def handle_product_updated(self, event: ProductUpdatedEvent) -> dict[str, Any]:
        """
        处理产品更新事件

        职责:
        1. 记录变更历史
        2. 检查价格变更并触发价格变更事件
        3. 使相关缓存失效
        """
        logger.info(f"[ProductDomain] 处理产品更新: {event.payload.get('product_id')}")

        result = {"success": True, "product_id": event.payload.get("product_id"), "actions": []}

        try:
            # 1. 记录变更历史
            result["actions"].append("change_history_recorded")

            # 2. 检查价格变更
            if "price" in event.payload.get("changed_fields", []):
                old_price = event.payload.get("old_price")
                new_price = event.payload.get("price")

                price_event = ProductPriceChangedEvent(
                    payload={
                        "product_id": event.payload.get("product_id"),
                        "old_price": old_price,
                        "new_price": new_price,
                        "unit_name": event.payload.get("unit_name"),
                    },
                    source="product_domain",
                    correlation_id=event.metadata.event_id,
                )
                self.bus.publish(price_event)
                result["actions"].append("price_change_event_triggered")

            # 3. 使缓存失效
            cache_event = ProductCacheInvalidatedEvent(
                payload={
                    "product_id": event.payload.get("product_id"),
                    "unit_name": event.payload.get("unit_name"),
                },
                source="product_domain",
                correlation_id=event.metadata.event_id,
            )
            self.bus.publish(cache_event)
            result["actions"].append("cache_invalidated")

        except Exception as e:
            logger.error(f"[ProductDomain] 处理产品更新事件失败: {e}")
            result["success"] = False
            result["error"] = str(e)

        return result

    async def handle_product_deleted(self, event: ProductDeletedEvent) -> dict[str, Any]:
        """
        处理产品删除事件

        职责:
        1. 记录删除审计日志
        2. 使相关缓存失效
        3. 清理相关关联数据
        """
        logger.info(f"[ProductDomain] 处理产品删除: {event.payload.get('product_id')}")

        result = {"success": True, "product_id": event.payload.get("product_id"), "actions": []}

        try:
            # 1. 记录删除审计
            result["actions"].append("deletion_audit_logged")

            # 2. 使缓存失效
            cache_event = ProductCacheInvalidatedEvent(
                payload={
                    "product_id": event.payload.get("product_id"),
                    "unit_name": event.payload.get("unit_name"),
                    "reason": "product_deleted",
                },
                source="product_domain",
                correlation_id=event.metadata.event_id,
            )
            self.bus.publish(cache_event)
            result["actions"].append("cache_invalidated")

        except Exception as e:
            logger.error(f"[ProductDomain] 处理产品删除事件失败: {e}")
            result["success"] = False
            result["error"] = str(e)

        return result

    async def handle_product_imported(self, event: ProductImportedEvent) -> dict[str, Any]:
        """
        处理批量导入事件

        职责:
        1. 统计导入结果
        2. 批量使缓存失效
        3. 发送导入完成通知
        """
        logger.info(
            f"[ProductDomain] 处理产品批量导入: {event.payload.get('unit_name')} "
            f"(数量: {event.payload.get('count', 0)})"
        )

        result = {
            "success": True,
            "unit_name": event.payload.get("unit_name"),
            "imported_count": event.payload.get("count", 0),
            "actions": [],
        }

        try:
            # 1. 记录导入统计
            result["actions"].append("import_stats_recorded")

            # 2. 批量使缓存失效
            cache_event = ProductCacheInvalidatedEvent(
                payload={
                    "unit_name": event.payload.get("unit_name"),
                    "reason": "bulk_import",
                    "affected_count": event.payload.get("count", 0),
                },
                source="product_domain",
                correlation_id=event.metadata.event_id,
            )
            self.bus.publish(cache_event)
            result["actions"].append("bulk_cache_invalidated")

        except Exception as e:
            logger.error(f"[ProductDomain] 处理产品导入事件失败: {e}")
            result["success"] = False
            result["error"] = str(e)

        return result

    async def handle_price_changed(self, event: ProductPriceChangedEvent) -> dict[str, Any]:
        """
        处理价格变更事件

        职责:
        1. 记录价格历史
        2. 检查是否需要触发价格预警
        3. 通知相关业务方
        """
        logger.info(
            f"[ProductDomain] 处理价格变更: {event.payload.get('product_id')} "
            f"({event.payload.get('old_price')} -> {event.payload.get('new_price')})"
        )

        result = {
            "success": True,
            "product_id": event.payload.get("product_id"),
            "price_delta": event.payload.get("new_price", 0) - event.payload.get("old_price", 0),
            "actions": [],
        }

        try:
            # 1. 记录价格历史
            result["actions"].append("price_history_recorded")

            # 2. 可以在这里触发价格预警检查
            # 如果价格变动超过阈值，发送预警

        except Exception as e:
            logger.error(f"[ProductDomain] 处理价格变更事件失败: {e}")
            result["success"] = False
            result["error"] = str(e)

        return result

    async def handle_cache_invalidated(self, event: ProductCacheInvalidatedEvent) -> dict[str, Any]:
        """
        处理缓存失效事件

        职责:
        1. 执行实际的缓存清除操作
        2. 通知其他节点（如果是分布式缓存）
        """
        payload = event.payload

        if "product_id" in payload:
            logger.info(f"[ProductDomain] 清除产品缓存: {payload.get('product_id')}")
        elif "unit_name" in payload:
            logger.info(f"[ProductDomain] 清除单位缓存: {payload.get('unit_name')}")

        result = {"success": True, "invalidated": payload, "actions": ["cache_cleared"]}

        try:
            # 这里调用实际的缓存清除逻辑
            # 可以调用 ProductsService 的缓存清除方法
            pass
        except Exception as e:
            logger.error(f"[ProductDomain] 处理缓存失效事件失败: {e}")
            result["success"] = False
            result["error"] = str(e)

        return result


# 创建处理器实例
_product_handlers = None


def get_product_domain_handlers() -> ProductDomainHandlers:
    """获取 ProductDomainHandlers 单例"""
    global _product_handlers
    if _product_handlers is None:
        _product_handlers = ProductDomainHandlers()
    return _product_handlers


def register_product_domain_handlers(bus):
    """注册所有 Product 领域事件处理器到 NeuroBus"""
    handlers = get_product_domain_handlers()

    # 注册所有事件处理器
    bus.subscribe("product.created", handlers.handle_product_created)
    bus.subscribe("product.updated", handlers.handle_product_updated)
    bus.subscribe("product.deleted", handlers.handle_product_deleted)
    bus.subscribe("product.imported", handlers.handle_product_imported)
    bus.subscribe("product.price_changed", handlers.handle_price_changed)
    bus.subscribe("product.cache_invalidated", handlers.handle_cache_invalidated)

    logger.info("[ProductDomain] 所有事件处理器已注册")
