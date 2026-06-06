"""
shipment_app_service V2 - 事件驱动版本

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
from app.neuro_bus.events.shipment_events import *

if TYPE_CHECKING:
    pass  # 根据实际需要添加类型引用

logger = logging.getLogger(__name__)


class ShipmentAppServiceV2:
    """
    ShipmentAppService V2 - 事件驱动版本

    Level 2 事件驱动实现:
    - 所有业务操作通过事件发布
    - 支持异步处理和事件链
    - 完整的可追溯性和可观测性
    """

    def __init__(self):
        self._bus = get_neuro_bus()
        self._correlation_prefix = "shipment"

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
                source="shipmentappservice_v2",
                correlation_id=cid,
                priority=priority,
            )
            self._bus.publish(event)
            return event
        except Exception as e:
            logger.error(f"[ShipmentAppServiceV2] 发布事件失败: {e}")
            return None

    # ========== Level 2: 事件驱动核心方法 ==========

    async def create_shipment(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        创建发货单 - 事件驱动实现

        Level 2 事件驱动:
        1. 发布 shipment.created 事件
        2. 由领域处理器异步处理
        3. 触发库存扣减等后续事件链
        """
        try:
            shipment_id = data.get("shipment_id") or f"SH{datetime.now().strftime('%Y%m%d%H%M%S')}"
            correlation_id = self._create_correlation_id()

            # Level 2: 发布领域事件
            event = ShipmentCreatedEvent(
                payload={
                    "shipment_id": shipment_id,
                    "unit_name": data.get("unit_name"),
                    "items": data.get("items", []),
                    "deduct_inventory": data.get("deduct_inventory", True),
                    "created_by": data.get("created_by"),
                    "metadata": data.get("metadata", {}),
                },
                source="shipmentappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            logger.info(f"[ShipmentAppServiceV2] 发货单创建事件已发布: {shipment_id}")

            return {
                "success": True,
                "shipment_id": shipment_id,
                "event_id": event.metadata.event_id,
                "correlation_id": correlation_id,
                "message": "发货单创建事件已提交",
                "mode": "event_driven",  # Level 2 标志
            }

        except Exception as e:
            logger.exception(f"[ShipmentAppServiceV2] 创建发货单失败: {e}")
            return {"success": False, "message": str(e), "error": str(e)}

    async def add_item_to_shipment(self, shipment_id: str, item: dict[str, Any]) -> dict[str, Any]:
        """
        添加产品到发货单 - 事件驱动实现

        Level 2 事件驱动:
        1. 发布 shipment.item_added 事件
        2. 触发金额计算等后续处理
        """
        try:
            correlation_id = self._create_correlation_id()

            event = ShipmentItemAddedEvent(
                payload={
                    "shipment_id": shipment_id,
                    "product_id": item.get("product_id"),
                    "quantity": item.get("quantity"),
                    "unit_price": item.get("unit_price", 0),
                    "specification": item.get("specification"),
                    "added_by": item.get("added_by"),
                },
                source="shipmentappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            return {
                "success": True,
                "shipment_id": shipment_id,
                "event_id": event.metadata.event_id,
                "message": "添加产品事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[ShipmentAppServiceV2] 添加产品失败: {e}")
            return {"success": False, "message": str(e)}

    async def print_shipment(
        self, shipment_id: str, print_options: dict[str, Any]
    ) -> dict[str, Any]:
        """
        打印发货单 - 事件驱动实现

        Level 2 事件驱动:
        1. 发布 shipment.printed 事件
        2. 由打印服务异步处理
        """
        try:
            correlation_id = self._create_correlation_id()

            event = ShipmentPrintedEvent(
                payload={
                    "shipment_id": shipment_id,
                    "printer_name": print_options.get("printer_name", "default"),
                    "template": print_options.get("template"),
                    "copies": print_options.get("copies", 1),
                    "generate_record": print_options.get("generate_record", True),
                },
                source="shipmentappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            return {
                "success": True,
                "shipment_id": shipment_id,
                "event_id": event.metadata.event_id,
                "message": "打印事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[ShipmentAppServiceV2] 打印发货单失败: {e}")
            return {"success": False, "message": str(e)}

    async def cancel_shipment(
        self, shipment_id: str, reason: str, restore_inventory: bool = True
    ) -> dict[str, Any]:
        """
        取消发货单 - 事件驱动实现

        Level 2 事件驱动:
        1. 发布 shipment.cancelled 事件
        2. 触发库存恢复等后续处理
        """
        try:
            correlation_id = self._create_correlation_id()

            event = ShipmentCancelledEvent(
                payload={
                    "shipment_id": shipment_id,
                    "reason": reason,
                    "restore_inventory": restore_inventory,
                    "cancelled_at": datetime.now().isoformat(),
                },
                source="shipmentappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            return {
                "success": True,
                "shipment_id": shipment_id,
                "event_id": event.metadata.event_id,
                "message": "取消事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[ShipmentAppServiceV2] 取消发货单失败: {e}")
            return {"success": False, "message": str(e)}

    async def delete_shipment(self, shipment_id: str) -> dict[str, Any]:
        """删除发货单 - 事件驱动实现"""
        try:
            correlation_id = self._create_correlation_id()

            event = ShipmentDeletedEvent(
                payload={"shipment_id": shipment_id, "deleted_at": datetime.now().isoformat()},
                source="shipmentappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            return {
                "success": True,
                "shipment_id": shipment_id,
                "event_id": event.metadata.event_id,
                "message": "删除事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[ShipmentAppServiceV2] 删除发货单失败: {e}")
            return {"success": False, "message": str(e)}

    async def export_shipments(self, query: dict[str, Any], file_path: str) -> dict[str, Any]:
        """
        导出发货单 - 事件驱动实现

        Level 2 事件驱动:
        1. 发布 shipment.exported 事件
        2. 由导出服务异步处理
        """
        try:
            correlation_id = self._create_correlation_id()

            event = ShipmentExportedEvent(
                payload={
                    "file_path": file_path,
                    "query": query,
                    "format": query.get("format", "excel"),
                    "requested_by": query.get("requested_by"),
                },
                source="shipmentappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            return {
                "success": True,
                "file_path": file_path,
                "event_id": event.metadata.event_id,
                "message": "导出事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[ShipmentAppServiceV2] 导出发货单失败: {e}")
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
            "create": self.create_shipment,
            "add_item": self.add_item_to_shipment,
            "print": self.print_shipment,
            "cancel": self.cancel_shipment,
            "delete": self.delete_shipment,
            "export": self.export_shipments,
        }

        if command_type in command_map:
            return await command_map[command_type](payload)

        # 未知命令：直接发布原始事件
        try:
            correlation_id = self._create_correlation_id()
            event_type = f"shipment.{command_type}"

            event = NeuroEvent(
                event_type=event_type,
                payload=payload,
                source="shipmentappservice_v2",
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
            logger.exception(f"[ShipmentAppServiceV2] 执行命令失败: {e}")
            return {"success": False, "message": str(e)}


# 注册到 instrumentation
from app.neuro_bus.neuro_application_instrumentation import instrument_application_service_class

instrument_application_service_class(ShipmentAppServiceV2, service_name="ShipmentAppServiceV2")

# 单例管理
_shipmentappservice_v2_instance = None


def get_shipment_app_service_v2() -> ShipmentAppServiceV2:
    """获取 ShipmentAppServiceV2 单例"""
    global _shipmentappservice_v2_instance
    if _shipmentappservice_v2_instance is None:
        _shipmentappservice_v2_instance = ShipmentAppServiceV2()
    return _shipmentappservice_v2_instance
