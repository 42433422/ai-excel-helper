"""
NeuroBus 初始化配置

提供总线启动、关闭和与 FastAPI 生命周期集成
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.neuro_bus.bus import NeuroBus, get_neuro_bus
from app.neuro_bus.events.base import EventPriority, NeuroEvent

logger = logging.getLogger(__name__)


class NeuroBusManager:
    """
    NeuroBus 生命周期管理器

    处理启动、关闭、健康检查
    """

    def __init__(self):
        self._bus: NeuroBus | None = None
        self._started = False

    async def start(self):
        """启动 NeuroBus"""
        if self._started:
            logger.warning("NeuroBus already started")
            return

        self._bus = get_neuro_bus()
        await self._bus.start()
        self._started = True

        # 注册系统事件处理器
        self._register_system_handlers()

        logger.info("NeuroBusManager: NeuroBus started successfully")

    async def stop(self):
        """停止 NeuroBus"""
        if not self._started or not self._bus:
            return

        await self._bus.stop()
        self._started = False
        logger.info("NeuroBusManager: NeuroBus stopped")

    def _register_system_handlers(self):
        """注册系统级事件处理器"""

        async def on_system_event(event: NeuroEvent):
            """系统事件日志"""
            logger.debug(f"System event: {event.event_type} from {event.metadata.source}")

        # 订阅所有系统事件
        self._bus.subscribe("system.*", on_system_event, priority=100)

    def get_bus(self) -> NeuroBus | None:
        """获取总线实例"""
        return self._bus

    def is_running(self) -> bool:
        """检查是否运行中"""
        return self._started and self._bus is not None

    def get_health(self) -> dict:
        """获取健康状态"""
        if not self._bus:
            return {
                "status": "down",
                "running": False,
                "queue_size": 0,
            }

        stats = self._bus.get_stats()
        return {
            "status": "healthy" if self._started else "degraded",
            "running": self._started,
            **stats,
        }


# 全局管理器实例
_neuro_bus_manager: NeuroBusManager | None = None


def get_neuro_bus_manager() -> NeuroBusManager:
    """获取 NeuroBus 管理器（单例）"""
    global _neuro_bus_manager
    if _neuro_bus_manager is None:
        _neuro_bus_manager = NeuroBusManager()
    return _neuro_bus_manager


async def setup_neuro_bus():
    """初始化 NeuroBus（用于应用启动时调用）"""
    manager = get_neuro_bus_manager()
    await manager.start()
    return manager.get_bus()


def init_neuro_bus(app: FastAPI | None = None) -> NeuroBus | None:
    """
    同步初始化入口（旧脚本 / XCAGI/test_neuro_chain.py）。
    在已有 asyncio 事件循环的进程内请使用 ``await setup_neuro_bus()``（由 FastAPI lifespan 调用）。
    """

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(setup_neuro_bus())
    else:
        logger.debug("init_neuro_bus: event loop already running; returning singleton bus")

    try:
        from app.neuro_bus.domains.intent_domain import get_intent_domain

        get_intent_domain()
    except Exception as e:
        logger.warning("init_neuro_bus: intent domain setup: %s", e)

    return get_neuro_bus()


async def teardown_neuro_bus():
    """关闭 NeuroBus（用于应用关闭时调用）"""
    manager = get_neuro_bus_manager()
    await manager.stop()


@asynccontextmanager
async def neuro_bus_lifespan():
    """
    NeuroBus 生命周期上下文管理器

    用于手动管理总线生命周期
    """
    await setup_neuro_bus()
    try:
        yield get_neuro_bus()
    finally:
        await teardown_neuro_bus()


def create_neuro_bus_lifespan(app: FastAPI):
    """
    创建 FastAPI 生命周期管理器

    用法:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with create_neuro_bus_lifespan(app):
                yield

        app = FastAPI(lifespan=lifespan)
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("NeuroBus: Initializing...")
        await setup_neuro_bus()

        # 获取管理器并注册到应用状态
        manager = get_neuro_bus_manager()
        app.state.neuro_bus_manager = manager

        logger.info("NeuroBus: Ready")
        yield

        logger.info("NeuroBus: Shutting down...")
        await teardown_neuro_bus()

    return lifespan


# 便捷函数


def publish_event(
    event_type: str,
    payload: dict,
    priority: EventPriority = EventPriority.NORMAL,
    domain: str = "global",
    **kwargs,
) -> bool:
    """
    便捷函数：发布事件

    Args:
        event_type: 事件类型
        payload: 事件数据
        priority: 优先级
        domain: 领域
        **kwargs: 额外元数据

    Returns:
        是否成功发布
    """
    bus = get_neuro_bus()
    if not bus:
        logger.warning("Cannot publish: NeuroBus not initialized")
        return False

    event = NeuroEvent(event_type=event_type, payload=payload, priority=priority, **kwargs)
    event.with_domain(domain)

    return bus.publish(event)


def subscribe_event(
    event_type: str,
    handler,
    priority: int = 0,
    is_async: bool = True,
):
    """
    便捷函数：订阅事件

    用法示例:
        @subscribe_event("user.login", priority=1)
        async def on_user_login(event: NeuroEvent):
            print(f"User logged in: {event.payload}")
    """
    bus = get_neuro_bus()
    if not bus:
        logger.warning("Cannot subscribe: NeuroBus not initialized")
        return None

    return bus.subscribe(event_type, handler, priority, is_async)


# 装饰器方式订阅


def on_event(
    event_type: str,
    priority: int = 0,
    is_async: bool = True,
):
    """
    事件订阅装饰器

    用法:
        @on_event("order.created", priority=1)
        async def handle_order_created(event: NeuroEvent):
            # 处理事件
            pass
    """

    def decorator(func):
        subscribe_event(event_type, func, priority, is_async)
        return func

    return decorator
