"""
product_app_service V2 - 事件驱动版本

基于 Neuro-DDD 架构的事件驱动实现。

与 V1 的区别：
- V1: 直接调用 Services 层方法
- V2: 发布事件到 NeuroBus，由事件处理器执行实际业务

生成时间: 自动生成
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.events.base import EventPriority, NeuroEvent
from app.neuro_bus.events.product_events import *

if TYPE_CHECKING:
    pass  # 根据实际需要添加类型引用

logger = logging.getLogger(__name__)


class ProductAppServiceV2:
    """
    ProductAppService V2 - 事件驱动版本

    Level 2 事件驱动实现:
    - 所有业务操作通过事件发布
    - 支持异步处理和事件链
    - 完整的可追溯性和可观测性
    """

    def __init__(self):
        self._bus = get_neuro_bus()
        self._correlation_prefix = "product"

    def _create_correlation_id(self) -> str:
        """创建事件关联 ID"""
        return f"{self._correlation_prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{id(self)}"

    def _publish_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: str | None = None,
    ) -> NeuroEvent | None:
        """内部方法：发布事件到 NeuroBus"""
        try:
            cid = correlation_id or self._create_correlation_id()
            event = NeuroEvent(
                event_type=event_type,
                payload=payload,
                source="productappservice_v2",
                correlation_id=cid,
                priority=priority,
            )
            self._bus.publish(event)
            return event
        except Exception as e:
            logger.error(f"[ProductAppServiceV2] 发布事件失败: {e}")
            return None

    # ========== Level 2: 事件驱动核心方法 ==========

    async def create_product(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        创建产品 - 事件驱动实现

        Level 2 事件驱动:
        1. 发布 product.created 事件
        2. 由领域处理器异步处理
        3. 触发缓存更新等后续事件链
        """
        try:
            product_id = data.get("product_id") or f"PR{datetime.now().strftime('%Y%m%d%H%M%S')}"
            correlation_id = self._create_correlation_id()

            event = ProductCreatedEvent(
                payload={
                    "product_id": product_id,
                    "unit_name": data.get("unit_name"),
                    "product_name": data.get("product_name"),
                    "model_number": data.get("model_number"),
                    "price": data.get("price", 0),
                    "specification": data.get("specification"),
                    "created_by": data.get("created_by"),
                    "metadata": data.get("metadata", {}),
                },
                source="productappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            logger.info(f"[ProductAppServiceV2] 产品创建事件已发布: {product_id}")

            return {
                "success": True,
                "product_id": product_id,
                "event_id": event.metadata.event_id,
                "correlation_id": correlation_id,
                "message": "产品创建事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[ProductAppServiceV2] 创建产品失败: {e}")
            return {"success": False, "message": str(e), "error": str(e)}

    async def update_product(self, product_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """
        更新产品 - 事件驱动实现

        Level 2 事件驱动:
        1. 发布 product.updated 事件
        2. 触发缓存失效等后续处理
        """
        try:
            correlation_id = self._create_correlation_id()

            # 如果价格变更，额外发布价格变更事件
            if "price" in updates:
                price_event = ProductPriceChangedEvent(
                    payload={
                        "product_id": product_id,
                        "old_price": updates.get("old_price", 0),
                        "new_price": updates["price"],
                        "changed_at": datetime.now().isoformat(),
                    },
                    source="productappservice_v2",
                    correlation_id=correlation_id,
                )
                self._bus.publish(price_event)

            event = ProductUpdatedEvent(
                payload={
                    "product_id": product_id,
                    "updates": updates,
                    "updated_by": updates.get("updated_by"),
                    "updated_at": datetime.now().isoformat(),
                },
                source="productappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            # 触发缓存失效
            cache_event = ProductCacheInvalidatedEvent(
                payload={"product_id": product_id, "reason": "product_updated"},
                source="productappservice_v2",
                correlation_id=correlation_id,
            )
            self._bus.publish(cache_event)

            return {
                "success": True,
                "product_id": product_id,
                "event_id": event.metadata.event_id,
                "message": "产品更新事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[ProductAppServiceV2] 更新产品失败: {e}")
            return {"success": False, "message": str(e)}

    async def delete_product(
        self, product_id: str, deleted_by: str | None = None
    ) -> dict[str, Any]:
        """
        删除产品 - 事件驱动实现

        Level 2 事件驱动:
        1. 发布 product.deleted 事件（软删除）
        2. 触发缓存失效
        """
        try:
            correlation_id = self._create_correlation_id()

            event = ProductDeletedEvent(
                payload={
                    "product_id": product_id,
                    "deleted_by": deleted_by,
                    "deleted_at": datetime.now().isoformat(),
                    "soft_delete": True,
                },
                source="productappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            # 触发缓存失效
            cache_event = ProductCacheInvalidatedEvent(
                payload={"product_id": product_id, "reason": "product_deleted"},
                source="productappservice_v2",
                correlation_id=correlation_id,
            )
            self._bus.publish(cache_event)

            return {
                "success": True,
                "product_id": product_id,
                "event_id": event.metadata.event_id,
                "message": "产品删除事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[ProductAppServiceV2] 删除产品失败: {e}")
            return {"success": False, "message": str(e)}

    async def import_products(
        self, unit_name: str, products: list[dict[str, Any]], imported_by: str | None = None
    ) -> dict[str, Any]:
        """
        批量导入产品 - 事件驱动实现

        Level 2 事件驱动:
        1. 发布 product.imported 事件（低优先级，后台处理）
        2. 异步处理批量导入
        """
        try:
            correlation_id = self._create_correlation_id()

            event = ProductImportedEvent(
                payload={
                    "unit_name": unit_name,
                    "products": products,
                    "count": len(products),
                    "imported_by": imported_by,
                    "imported_at": datetime.now().isoformat(),
                },
                source="productappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            return {
                "success": True,
                "unit_name": unit_name,
                "count": len(products),
                "event_id": event.metadata.event_id,
                "message": f"批量导入事件已提交 ({len(products)} 个产品)",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[ProductAppServiceV2] 批量导入产品失败: {e}")
            return {"success": False, "message": str(e)}

    async def invalidate_cache(
        self, product_id: str | None = None, unit_name: str | None = None
    ) -> dict[str, Any]:
        """
        使产品缓存失效 - 事件驱动实现

        Level 2 事件驱动:
        1. 发布 product.cache_invalidated 事件（高优先级）
        2. 快速传播缓存失效指令
        """
        try:
            correlation_id = self._create_correlation_id()

            payload = {"reason": "manual_invalidation"}
            if product_id:
                payload["product_id"] = product_id
            if unit_name:
                payload["unit_name"] = unit_name

            event = ProductCacheInvalidatedEvent(
                payload=payload, source="productappservice_v2", correlation_id=correlation_id
            )

            self._bus.publish(event)

            return {
                "success": True,
                "event_id": event.metadata.event_id,
                "message": "缓存失效事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[ProductAppServiceV2] 缓存失效失败: {e}")
            return {"success": False, "message": str(e)}

    # ========== 通用命令方法 (向后兼容) ==========

    async def execute_command(self, command_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        通用命令执行方法 - Level 2 事件驱动

        Args:
            command_type: 命令类型 (对应事件类型)
            payload: 命令数据

        Returns:
            执行结果
        """
        command_map = {
            "create": self.create_product,
            "update": self.update_product,
            "delete": self.delete_product,
            "import": self.import_products,
            "invalidate_cache": self.invalidate_cache,
        }

        if command_type in command_map:
            return await command_map[command_type](payload)

        # 未知命令：直接发布原始事件
        try:
            correlation_id = self._create_correlation_id()
            event_type = f"product.{command_type}"

            event = NeuroEvent(
                event_type=event_type,
                payload=payload,
                source="productappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            return {
                "success": True,
                "event_id": event.metadata.event_id,
                "correlation_id": correlation_id,
                "message": f"{command_type} 命令已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[ProductAppServiceV2] 执行命令失败: {e}")
            return {"success": False, "message": str(e)}


# 注册到 instrumentation
from app.neuro_bus.neuro_application_instrumentation import instrument_application_service_class

instrument_application_service_class(ProductAppServiceV2, service_name="ProductAppServiceV2")

# 单例管理
_productappservice_v2_instance = None


def get_product_app_service_v2() -> ProductAppServiceV2:
    """获取 ProductAppServiceV2 单例"""
    global _productappservice_v2_instance
    if _productappservice_v2_instance is None:
        _productappservice_v2_instance = ProductAppServiceV2()
    return _productappservice_v2_instance
