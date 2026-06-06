"""
神经域基类

定义领域事件通道的标准接口
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.neuro_bus.bus import NeuroBus, get_neuro_bus
from app.neuro_bus.events.base import AsyncEventHandler, EventPriority, NeuroEvent

logger = logging.getLogger(__name__)


class DomainChannel(Enum):
    """
    领域通道类型

    不同通道对应不同的可靠性机制组合
    """

    FAST = "fast"  # 快速通道：最小可靠性开销
    STANDARD = "standard"  # 标准通道：默认机制
    RELIABLE = "reliable"  # 可靠通道：全机制启用
    CRITICAL = "critical"  # 关键通道：最高可靠性


@dataclass
class DomainHandler:
    """领域处理器定义"""

    event_type: str
    handler: AsyncEventHandler
    priority: int = 0
    channel: DomainChannel = DomainChannel.STANDARD
    filter_fn: Callable[[NeuroEvent], bool] | None = None


class NeuroDomain(ABC):
    """
    神经域基类

    所有领域域的基类，提供：
    - 专用消息通道
    - 领域事件定义
    - 处理器注册装饰器
    - 链路追踪上下文
    """

    # 领域名称，子类必须覆盖
    domain_name: str = ""

    # 默认通道
    default_channel: DomainChannel = DomainChannel.STANDARD

    def __init__(self, bus: NeuroBus | None = None):
        if not self.domain_name:
            raise ValueError("NeuroDomain subclass must define domain_name")

        self._bus = bus or get_neuro_bus()
        self._handlers: list[DomainHandler] = []
        self._registered = False

        logger.info(f"NeuroDomain [{self.domain_name}] initialized")

    @property
    def bus(self) -> NeuroBus:
        """获取事件总线"""
        return self._bus

    def register(self):
        """
        注册领域处理器到总线

        应在应用启动时调用一次
        """
        if self._registered:
            logger.warning(f"Domain [{self.domain_name}] already registered")
            return

        for handler_def in self._handlers:
            self._bus.subscribe_to_domain(
                domain=self.domain_name,
                event_type=handler_def.event_type,
                handler=handler_def.handler,
                priority=handler_def.priority,
            )
            logger.debug(f"Registered handler for {self.domain_name}.{handler_def.event_type}")

        self._registered = True
        logger.info(f"Domain [{self.domain_name}] registered with {len(self._handlers)} handlers")

    def unregister(self):
        """注销领域"""
        # 目前总线不支持单个注销，需重新初始化
        self._registered = False
        logger.info(f"Domain [{self.domain_name}] unregistered")

    def add_handler(
        self,
        event_type: str,
        handler: AsyncEventHandler,
        priority: int = 0,
        channel: DomainChannel | None = None,
        filter_fn: Callable[[NeuroEvent], bool] | None = None,
    ):
        """
        添加事件处理器

        通常通过 on() 装饰器使用
        """
        handler_def = DomainHandler(
            event_type=event_type,
            handler=handler,
            priority=priority,
            channel=channel or self.default_channel,
            filter_fn=filter_fn,
        )
        self._handlers.append(handler_def)

    def on(
        self,
        event_type: str,
        priority: int = 0,
        channel: DomainChannel | None = None,
    ):
        """
        事件处理器装饰器

        用法:
            class MyDomain(NeuroDomain):
                domain_name = "my_domain"

                @self.on("event.created", priority=1)
                async def handle_created(self, event: NeuroEvent):
                    pass
        """

        def decorator(func: AsyncEventHandler) -> AsyncEventHandler:
            self.add_handler(
                event_type=event_type,
                handler=func,
                priority=priority,
                channel=channel,
            )
            return func

        return decorator

    def emit(
        self,
        event_type: str,
        payload: dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        **kwargs,
    ) -> bool:
        """
        发送领域事件

        便捷方法，自动设置领域
        """
        event = NeuroEvent(event_type=event_type, payload=payload, priority=priority, **kwargs)
        event.with_domain(self.domain_name)
        event.with_source(self.domain_name)

        return self._bus.publish(event)

    @abstractmethod
    async def initialize(self):
        """
        初始化领域

        子类应在此执行领域特定的初始化
        """
        pass

    @abstractmethod
    async def shutdown(self):
        """
        关闭领域

        子类应在此执行清理操作
        """
        pass

    def get_stats(self) -> dict[str, Any]:
        """获取领域统计"""
        return {
            "domain": self.domain_name,
            "handlers": len(self._handlers),
            "registered": self._registered,
        }


class DomainRegistry:
    """
    领域注册表

    管理所有领域实例
    """

    def __init__(self):
        self._domains: dict[str, NeuroDomain] = {}

    def register(self, domain: NeuroDomain):
        """注册领域实例"""
        self._domains[domain.domain_name] = domain
        domain.register()

    def get(self, domain_name: str) -> NeuroDomain | None:
        """获取领域实例"""
        return self._domains.get(domain_name)

    def list_domains(self) -> list[str]:
        """列出所有领域"""
        return list(self._domains.keys())

    async def initialize_all(self):
        """初始化所有领域"""
        for domain in self._domains.values():
            await domain.initialize()

    async def shutdown_all(self):
        """关闭所有领域"""
        for domain in self._domains.values():
            await domain.shutdown()

    def get_all_stats(self) -> dict[str, Any]:
        """获取所有领域统计"""
        return {name: domain.get_stats() for name, domain in self._domains.items()}


# 全局注册表
_domain_registry: DomainRegistry | None = None


def get_domain_registry() -> DomainRegistry:
    """获取全局领域注册表"""
    global _domain_registry
    if _domain_registry is None:
        _domain_registry = DomainRegistry()
    return _domain_registry


def register_domain(domain: NeuroDomain) -> NeuroDomain:
    """
    注册领域便捷函数

    用法:
        @register_domain
        class MyDomain(NeuroDomain):
            domain_name = "my_domain"
            ...
    """
    registry = get_domain_registry()
    registry.register(domain)
    return domain
