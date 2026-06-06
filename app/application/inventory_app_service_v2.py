"""
inventory_app_service V2 - 事件驱动版本

基于 Neuro-DDD 架构的事件驱动实现。
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.events.base import EventPriority, NeuroEvent
from app.neuro_bus.events.inventory_events import *

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class InventoryAppServiceV2:
    """
    InventoryAppService V2 - 事件驱动版本

    Level 2 事件驱动实现:
    - 所有业务操作通过事件发布
    - 支持异步处理和事件链
    - 完整的可追溯性和可观测性
    """

    def __init__(self):
        self._bus = get_neuro_bus()
        self._correlation_prefix = "inventory"

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
                source="inventoryappservice_v2",
                correlation_id=cid,
                priority=priority,
            )
            self._bus.publish(event)
            return event
        except Exception as e:
            logger.error(f"[InventoryAppServiceV2] 发布事件失败: {e}")
            return None

    # ========== Level 2: 事件驱动核心方法 ==========

    async def stock_in(self, data: dict[str, Any]) -> dict[str, Any]:
        """入库 - 事件驱动实现"""
        try:
            correlation_id = self._create_correlation_id()
            batch_no = data.get("batch_no") or f"BATCH{datetime.now().strftime('%Y%m%d%H%M%S')}"

            event = InventoryStockInEvent(
                payload={
                    "product_id": data.get("product_id"),
                    "product_name": data.get("product_name"),
                    "warehouse_id": data.get("warehouse_id"),
                    "location_id": data.get("location_id"),
                    "quantity": data.get("quantity", 0),
                    "unit_price": data.get("unit_price", 0),
                    "batch_no": batch_no,
                    "reference_type": data.get("reference_type"),
                    "reference_id": data.get("reference_id"),
                    "operator": data.get("operator"),
                    "remark": data.get("remark"),
                },
                source="inventoryappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            logger.info(f"[InventoryAppServiceV2] 入库事件已发布: {batch_no}")

            return {
                "success": True,
                "batch_no": batch_no,
                "event_id": event.metadata.event_id,
                "correlation_id": correlation_id,
                "message": "入库事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[InventoryAppServiceV2] 入库失败: {e}")
            return {"success": False, "message": str(e), "error": str(e)}

    async def stock_out(self, data: dict[str, Any]) -> dict[str, Any]:
        """出库 - 事件驱动实现"""
        try:
            correlation_id = self._create_correlation_id()

            event = InventoryStockOutEvent(
                payload={
                    "product_id": data.get("product_id"),
                    "product_name": data.get("product_name"),
                    "warehouse_id": data.get("warehouse_id"),
                    "location_id": data.get("location_id"),
                    "quantity": data.get("quantity", 0),
                    "reference_type": data.get("reference_type"),
                    "reference_id": data.get("reference_id"),
                    "operator": data.get("operator"),
                    "remark": data.get("remark"),
                },
                source="inventoryappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            logger.info("[InventoryAppServiceV2] 出库事件已发布")

            return {
                "success": True,
                "event_id": event.metadata.event_id,
                "correlation_id": correlation_id,
                "message": "出库事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[InventoryAppServiceV2] 出库失败: {e}")
            return {"success": False, "message": str(e), "error": str(e)}

    async def transfer(self, data: dict[str, Any]) -> dict[str, Any]:
        """库存调拨 - 事件驱动实现"""
        try:
            correlation_id = self._create_correlation_id()
            transfer_id = data.get("transfer_id") or f"TRF{datetime.now().strftime('%Y%m%d%H%M%S')}"

            event = InventoryTransferEvent(
                payload={
                    "transfer_id": transfer_id,
                    "product_id": data.get("product_id"),
                    "from_warehouse_id": data.get("from_warehouse_id"),
                    "to_warehouse_id": data.get("to_warehouse_id"),
                    "quantity": data.get("quantity", 0),
                    "operator": data.get("operator"),
                    "remark": data.get("remark"),
                },
                source="inventoryappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            logger.info(f"[InventoryAppServiceV2] 调拨事件已发布: {transfer_id}")

            return {
                "success": True,
                "transfer_id": transfer_id,
                "event_id": event.metadata.event_id,
                "correlation_id": correlation_id,
                "message": "调拨事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[InventoryAppServiceV2] 调拨失败: {e}")
            return {"success": False, "message": str(e), "error": str(e)}

    async def adjust_stock(self, data: dict[str, Any]) -> dict[str, Any]:
        """库存调整 - 事件驱动实现"""
        try:
            correlation_id = self._create_correlation_id()

            event = InventoryStockChangedEvent(
                payload={
                    "product_id": data.get("product_id"),
                    "warehouse_id": data.get("warehouse_id"),
                    "quantity_delta": data.get("quantity_delta", 0),
                    "reason": data.get("reason", "库存调整"),
                    "operator": data.get("operator"),
                    "adjustment_id": data.get("adjustment_id"),
                },
                source="inventoryappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            logger.info("[InventoryAppServiceV2] 库存调整事件已发布")

            return {
                "success": True,
                "event_id": event.metadata.event_id,
                "correlation_id": correlation_id,
                "message": "库存调整事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[InventoryAppServiceV2] 库存调整失败: {e}")
            return {"success": False, "message": str(e), "error": str(e)}

    # ========== 统一命令执行入口 ==========

    async def execute_command(self, command: str, data: dict[str, Any]) -> dict[str, Any]:
        """统一命令执行入口"""
        command_map = {
            "stock_in": self.stock_in,
            "stock_out": self.stock_out,
            "transfer": self.transfer,
            "adjust_stock": self.adjust_stock,
        }

        handler = command_map.get(command)
        if not handler:
            return {
                "success": False,
                "message": f"未知命令: {command}",
                "supported_commands": list(command_map.keys()),
            }

        try:
            return await handler(**data)
        except TypeError as e:
            return {"success": False, "message": f"命令参数错误: {e}", "command": command}
        except Exception as e:
            return {"success": False, "message": f"执行命令失败: {str(e)}", "command": command}


# ========== 单例实例 ==========
_inventory_app_service_v2: InventoryAppServiceV2 | None = None


def get_inventory_app_service_v2() -> InventoryAppServiceV2:
    """获取 InventoryAppServiceV2 单例实例"""
    global _inventory_app_service_v2
    if _inventory_app_service_v2 is None:
        _inventory_app_service_v2 = InventoryAppServiceV2()
    return _inventory_app_service_v2
