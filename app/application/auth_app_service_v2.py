"""
auth_app_service V2 - 事件驱动版本

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
from app.neuro_bus.events.auth_events import *

if TYPE_CHECKING:
    pass  # 根据实际需要添加类型引用

logger = logging.getLogger(__name__)


class AuthAppServiceV2:
    """
    AuthAppService V2 - 事件驱动版本
    """

    def __init__(self):
        self._bus = get_neuro_bus()
        self._correlation_prefix = "auth"

    def _create_correlation_id(self) -> str:
        """创建事件关联 ID"""
        return f"{self._correlation_prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{id(self)}"

    async def execute_command(self, command_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        通用命令执行方法

        Args:
            command_type: 命令类型 (对应事件类型)
            payload: 命令数据

        Returns:
            执行结果
        """
        try:
            correlation_id = self._create_correlation_id()

            # 构建事件类型
            event_type = f"auth.{command_type}"

            # 创建事件
            from app.neuro_bus.events.base import NeuroEvent

            event = NeuroEvent(
                event_type=event_type,
                payload=payload,
                source="authappservice_v2",
                correlation_id=correlation_id,
            )

            # 发布事件
            self._bus.publish(event)

            logger.info(
                f"[AuthAppServiceV2] 命令已发布: {command_type} (event_id={event.metadata.event_id})"
            )

            return {
                "success": True,
                "event_id": event.metadata.event_id,
                "correlation_id": correlation_id,
                "message": f"{command_type} 命令已提交",
            }

        except Exception as e:
            logger.exception(f"[AuthAppServiceV2] 执行命令失败: {e}")
            return {"success": False, "message": str(e)}


# 注册到 instrumentation
from app.neuro_bus.neuro_application_instrumentation import instrument_application_service_class

instrument_application_service_class(AuthAppServiceV2, service_name="AuthAppServiceV2")

# 单例管理
_authappservice_v2_instance = None


def get_auth_app_service_v2() -> AuthAppServiceV2:
    """获取 AuthAppServiceV2 单例"""
    global _authappservice_v2_instance
    if _authappservice_v2_instance is None:
        _authappservice_v2_instance = AuthAppServiceV2()
    return _authappservice_v2_instance
