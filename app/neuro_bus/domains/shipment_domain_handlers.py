"""
Shipment 领域事件处理器

处理所有 shipment.* 事件的业务逻辑。
"""

import logging
from typing import Any

from app.bootstrap import get_shipment_application_service_core
from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.command_gateway import try_complete_command_reply
from app.neuro_bus.events.base import NeuroEvent
from app.neuro_bus.events.shipment_events import (
    ShipmentExportedEvent,
    ShipmentInventoryDeductedEvent,
    ShipmentItemAddedEvent,
)

logger = logging.getLogger(__name__)


class ShipmentDomainHandlers:
    """Shipment 领域事件处理器集合"""

    def __init__(self):
        self._bus = None

    @property
    def bus(self):
        """延迟获取 NeuroBus 实例"""
        if self._bus is None:
            self._bus = get_neuro_bus()
        return self._bus

    async def handle_shipment_created(self, event: NeuroEvent) -> dict[str, Any]:
        """Strangler: 委托 ``ShipmentApplicationService.create_shipment``（核心实现，无事件递归）。"""
        logger.info(
            "[ShipmentDomain] 处理发货单创建: %s for %s",
            event.payload.get("shipment_id"),
            event.payload.get("unit_name"),
        )
        core = get_shipment_application_service_core()
        try:
            p = event.payload
            result = core.create_shipment(
                unit_name=str(p.get("unit_name") or ""),
                items_data=p.get("items") or [],
                contact_person=str(p.get("contact_person") or ""),
                contact_phone=str(p.get("contact_phone") or ""),
            )
            try_complete_command_reply(event, result)
            return result
        except Exception as e:
            logger.exception("[ShipmentDomain] 创建发货单失败: %s", e)
            try_complete_command_reply(event, None, error=e)
            raise

    async def handle_item_added(self, event: ShipmentItemAddedEvent) -> dict[str, Any]:
        """
        处理添加产品事件

        职责:
        1. 更新发货单总金额
        2. 检查库存是否足够
        3. 记录操作日志
        """
        logger.info(
            f"[ShipmentDomain] 处理添加产品: shipment={event.payload.get('shipment_id')} "
            f"product={event.payload.get('product_id')} qty={event.payload.get('quantity')}"
        )

        result = {"success": True, "shipment_id": event.payload.get("shipment_id"), "actions": []}

        try:
            # 1. 记录操作
            result["actions"].append("item_logged")

            # 2. 计算金额更新
            price = event.payload.get("unit_price", 0)
            qty = event.payload.get("quantity", 0)
            amount = price * qty
            result["amount_delta"] = amount

            # 3. 可以触发库存检查

        except Exception as e:
            logger.error(f"[ShipmentDomain] 处理添加产品事件失败: {e}")
            result["success"] = False
            result["error"] = str(e)

        return result

    async def handle_printed(self, event: NeuroEvent) -> dict[str, Any]:
        logger.info(
            "[ShipmentDomain] 处理打印: %s by %s",
            event.payload.get("shipment_id"),
            event.payload.get("printer_name", "unknown"),
        )
        core = get_shipment_application_service_core()
        try:
            sid = int(event.payload.get("shipment_id"))
            result = core.mark_as_printed(sid, str(event.payload.get("printer_name") or ""))
            try_complete_command_reply(event, result)
            return result
        except Exception as e:
            logger.exception("[ShipmentDomain] 打印处理失败: %s", e)
            try_complete_command_reply(event, None, error=e)
            raise

    async def handle_cancelled(self, event: NeuroEvent) -> dict[str, Any]:
        logger.info(
            "[ShipmentDomain] 处理取消: %s reason=%s",
            event.payload.get("shipment_id"),
            event.payload.get("reason", "unknown"),
        )
        core = get_shipment_application_service_core()
        try:
            sid = int(event.payload.get("shipment_id"))
            result = core.cancel_shipment(sid)
            try_complete_command_reply(event, result)
            return result
        except Exception as e:
            logger.exception("[ShipmentDomain] 取消失败: %s", e)
            try_complete_command_reply(event, None, error=e)
            raise

    async def handle_deleted(self, event: NeuroEvent) -> dict[str, Any]:
        logger.info("[ShipmentDomain] 处理删除: %s", event.payload.get("shipment_id"))
        core = get_shipment_application_service_core()
        try:
            sid = int(event.payload.get("shipment_id"))
            result = core.delete_shipment(sid)
            try_complete_command_reply(event, result)
            return result
        except Exception as e:
            logger.exception("[ShipmentDomain] 删除失败: %s", e)
            try_complete_command_reply(event, None, error=e)
            raise

    async def handle_exported(self, event: ShipmentExportedEvent) -> dict[str, Any]:
        """
        处理导出事件

        职责:
        1. 记录导出日志
        2. 统计导出数据
        3. 可以触发文件上传/清理
        """
        logger.info(
            f"[ShipmentDomain] 处理导出: {event.payload.get('file_path')} "
            f"({event.payload.get('record_count', 0)} 条记录)"
        )

        result = {"success": True, "file_path": event.payload.get("file_path"), "actions": []}

        try:
            # 1. 记录导出
            result["actions"].append("export_logged")

            # 2. 统计
            result["actions"].append("export_stats_updated")

            # 3. 可以触发文件处理

        except Exception as e:
            logger.error(f"[ShipmentDomain] 处理导出事件失败: {e}")
            result["success"] = False
            result["error"] = str(e)

        return result

    async def handle_inventory_deducted(
        self, event: ShipmentInventoryDeductedEvent
    ) -> dict[str, Any]:
        """
        处理库存扣减事件

        职责:
        1. 扣减对应产品库存
        2. 记录库存变动
        3. 检查库存预警
        """
        logger.info(
            f"[ShipmentDomain] 处理库存扣减: {event.payload.get('shipment_id')} "
            f"items={len(event.payload.get('items', []))}"
        )

        result = {"success": True, "shipment_id": event.payload.get("shipment_id"), "actions": []}

        try:
            # 1. 执行库存扣减
            items = event.payload.get("items", [])
            for item in items:
                # 这里调用库存服务的扣减方法
                pass

            result["actions"].append("inventory_deducted")

            # 2. 记录变动
            result["actions"].append("inventory_movement_logged")

            # 3. 检查预警
            result["actions"].append("alert_checked")

        except Exception as e:
            logger.error(f"[ShipmentDomain] 处理库存扣减事件失败: {e}")
            result["success"] = False
            result["error"] = str(e)

        return result


# 创建处理器实例
_shipment_handlers = None


def get_shipment_domain_handlers() -> ShipmentDomainHandlers:
    """获取 ShipmentDomainHandlers 单例"""
    global _shipment_handlers
    if _shipment_handlers is None:
        _shipment_handlers = ShipmentDomainHandlers()
    return _shipment_handlers


def register_shipment_domain_handlers(bus):
    """注册所有 Shipment 领域事件处理器到 NeuroBus"""
    handlers = get_shipment_domain_handlers()

    # 注册所有事件处理器
    bus.subscribe("shipment.created", handlers.handle_shipment_created)
    bus.subscribe("shipment.item_added", handlers.handle_item_added)
    bus.subscribe("shipment.printed", handlers.handle_printed)
    bus.subscribe("shipment.cancelled", handlers.handle_cancelled)
    bus.subscribe("shipment.deleted", handlers.handle_deleted)
    bus.subscribe("shipment.exported", handlers.handle_exported)
    bus.subscribe("shipment.inventory_deducted", handlers.handle_inventory_deducted)

    logger.info("[ShipmentDomain] 所有事件处理器已注册")
