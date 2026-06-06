"""
customer_app_service V2 - 事件驱动版本

基于 Neuro-DDD 架构的事件驱动实现。
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.events.base import EventPriority, NeuroEvent
from app.neuro_bus.events.customer_events import *

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class CustomerAppServiceV2:
    """
    CustomerAppService V2 - 事件驱动版本

    Level 2 事件驱动实现:
    - 所有业务操作通过事件发布
    - 支持异步处理和事件链
    - 完整的可追溯性和可观测性
    """

    def __init__(self):
        self._bus = get_neuro_bus()
        self._correlation_prefix = "customer"

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
                source="customerappservice_v2",
                correlation_id=cid,
                priority=priority,
            )
            self._bus.publish(event)
            return event
        except Exception as e:
            logger.error(f"[CustomerAppServiceV2] 发布事件失败: {e}")
            return None

    # ========== Level 2: 事件驱动核心方法 ==========

    async def register_customer(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        注册客户 - 事件驱动实现

        Level 2 事件驱动:
        1. 发布 customer.registered 事件
        2. 由领域处理器异步处理
        3. 触发后续欢迎邮件等事件链
        """
        try:
            customer_id = (
                data.get("customer_id") or f"CUST{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )
            correlation_id = self._create_correlation_id()

            event = CustomerRegisteredEvent(
                payload={
                    "customer_id": customer_id,
                    "customer_name": data.get("customer_name"),
                    "contact_info": {
                        "phone": data.get("phone"),
                        "email": data.get("email"),
                        "address": data.get("address"),
                    },
                    "purchase_unit": data.get("purchase_unit"),
                    "remark": data.get("remark"),
                    "created_by": data.get("created_by"),
                    "metadata": data.get("metadata", {}),
                },
                source="customerappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            logger.info(f"[CustomerAppServiceV2] 客户注册事件已发布: {customer_id}")

            return {
                "success": True,
                "customer_id": customer_id,
                "event_id": event.metadata.event_id,
                "correlation_id": correlation_id,
                "message": "客户注册事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[CustomerAppServiceV2] 注册客户失败: {e}")
            return {"success": False, "message": str(e), "error": str(e)}

    async def update_customer(self, customer_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        更新客户信息 - 事件驱动实现
        """
        try:
            correlation_id = self._create_correlation_id()

            event = CustomerUpdatedEvent(
                payload={
                    "customer_id": customer_id,
                    "updates": data,
                    "updated_at": datetime.now().isoformat(),
                },
                source="customerappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            logger.info(f"[CustomerAppServiceV2] 客户更新事件已发布: {customer_id}")

            return {
                "success": True,
                "customer_id": customer_id,
                "event_id": event.metadata.event_id,
                "correlation_id": correlation_id,
                "message": "客户更新事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[CustomerAppServiceV2] 更新客户失败: {e}")
            return {"success": False, "message": str(e), "error": str(e)}

    async def bind_purchase_unit(self, customer_id: str, purchase_unit: str) -> dict[str, Any]:
        """
        绑定购买单位 - 事件驱动实现
        """
        try:
            correlation_id = self._create_correlation_id()

            event = CustomerPurchaseUnitBoundEvent(
                payload={
                    "customer_id": customer_id,
                    "purchase_unit": purchase_unit,
                    "bound_at": datetime.now().isoformat(),
                },
                source="customerappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            logger.info(
                f"[CustomerAppServiceV2] 客户绑定单位事件已发布: {customer_id} -> {purchase_unit}"
            )

            return {
                "success": True,
                "customer_id": customer_id,
                "purchase_unit": purchase_unit,
                "event_id": event.metadata.event_id,
                "correlation_id": correlation_id,
                "message": "客户绑定单位事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[CustomerAppServiceV2] 绑定购买单位失败: {e}")
            return {"success": False, "message": str(e), "error": str(e)}

    async def update_preference(
        self, customer_id: str, preferences: dict[str, Any]
    ) -> dict[str, Any]:
        """
        更新客户偏好 - 事件驱动实现
        """
        try:
            correlation_id = self._create_correlation_id()

            event = CustomerPreferenceUpdatedEvent(
                payload={
                    "customer_id": customer_id,
                    "preferences": preferences,
                    "updated_at": datetime.now().isoformat(),
                },
                source="customerappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            logger.info(f"[CustomerAppServiceV2] 客户偏好更新事件已发布: {customer_id}")

            return {
                "success": True,
                "customer_id": customer_id,
                "event_id": event.metadata.event_id,
                "correlation_id": correlation_id,
                "message": "客户偏好更新事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[CustomerAppServiceV2] 更新偏好失败: {e}")
            return {"success": False, "message": str(e), "error": str(e)}

    async def deactivate_customer(
        self, customer_id: str, reason: str | None = None
    ) -> dict[str, Any]:
        """
        停用客户 - 事件驱动实现
        """
        try:
            correlation_id = self._create_correlation_id()

            event = CustomerDeactivatedEvent(
                payload={
                    "customer_id": customer_id,
                    "reason": reason,
                    "deactivated_at": datetime.now().isoformat(),
                },
                source="customerappservice_v2",
                correlation_id=correlation_id,
            )

            self._bus.publish(event)

            logger.info(f"[CustomerAppServiceV2] 客户停用事件已发布: {customer_id}")

            return {
                "success": True,
                "customer_id": customer_id,
                "event_id": event.metadata.event_id,
                "correlation_id": correlation_id,
                "message": "客户停用事件已提交",
                "mode": "event_driven",
            }

        except Exception as e:
            logger.exception(f"[CustomerAppServiceV2] 停用客户失败: {e}")
            return {"success": False, "message": str(e), "error": str(e)}

    # ========== 统一命令执行入口 ==========

    async def execute_command(self, command: str, data: dict[str, Any]) -> dict[str, Any]:
        """统一命令执行入口"""
        command_map = {
            "register_customer": self.register_customer,
            "update_customer": self.update_customer,
            "bind_purchase_unit": self.bind_purchase_unit,
            "update_preference": self.update_preference,
            "deactivate_customer": self.deactivate_customer,
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
_customer_app_service_v2: CustomerAppServiceV2 | None = None


def get_customer_app_service_v2() -> CustomerAppServiceV2:
    """获取 CustomerAppServiceV2 单例实例"""
    global _customer_app_service_v2
    if _customer_app_service_v2 is None:
        _customer_app_service_v2 = CustomerAppServiceV2()
    return _customer_app_service_v2
