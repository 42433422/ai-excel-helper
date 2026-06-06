"""
NeuroBus 初始化器

确保所有 Level 4 可靠性机制在应用启动时正确初始化。
"""

import logging

from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.circuit_breaker import get_circuit_breaker
from app.neuro_bus.dead_letter_queue import get_dead_letter_queue
from app.neuro_bus.deduplicator import get_deduplicator
from app.neuro_bus.event_store import EventStoreMode, get_event_store
from app.neuro_bus.health_monitor import get_health_monitor
from app.neuro_bus.retry_handler import get_retry_handler

logger = logging.getLogger(__name__)


class NeuroBusInitializer:
    """
    NeuroBus 初始化器

    负责在应用启动时初始化所有 Level 4 可靠性机制。
    """

    def __init__(self):
        self._initialized = False
        self._bus = None
        self._dlq = None
        self._event_store = None
        self._health_monitor = None
        self._retry_handler = None
        self._circuit_breaker = None
        self._deduplicator = None

    def initialize(self, event_store_mode: EventStoreMode = EventStoreMode.MEMORY) -> bool:
        """
        初始化所有 NeuroBus 组件

        Args:
            event_store_mode: 事件存储模式

        Returns:
            bool: 是否成功初始化
        """
        if self._initialized:
            logger.info("[NeuroBusInitializer] 已经初始化，跳过")
            return True

        try:
            logger.info("[NeuroBusInitializer] 开始初始化 NeuroBus 系统...")

            # 1. 初始化核心总线
            self._bus = get_neuro_bus()
            logger.info("[NeuroBusInitializer] ✓ NeuroBus 核心总线已初始化")

            # 2. 初始化死信队列
            self._dlq = get_dead_letter_queue()
            logger.info("[NeuroBusInitializer] ✓ 死信队列 (DLQ) 已初始化")

            # 3. 初始化事件存储
            self._event_store = get_event_store(mode=event_store_mode)
            logger.info(
                f"[NeuroBusInitializer] ✓ 事件存储已初始化 (模式: {event_store_mode.value})"
            )

            # 4. 初始化健康监控
            self._health_monitor = get_health_monitor()
            self._health_monitor.start_monitoring()
            logger.info("[NeuroBusInitializer] ✓ 健康监控已初始化并启动")

            # 5. 初始化重试处理器
            self._retry_handler = get_retry_handler()
            logger.info("[NeuroBusInitializer] ✓ 重试处理器已初始化")

            # 6. 初始化熔断器
            self._circuit_breaker = get_circuit_breaker()
            logger.info("[NeuroBusInitializer] ✓ 熔断保护器已初始化")

            # 7. 初始化去重器
            self._deduplicator = get_deduplicator()
            logger.info("[NeuroBusInitializer] ✓ 去重器已初始化")

            self._initialized = True

            logger.info("[NeuroBusInitializer] ================================")
            logger.info("[NeuroBusInitializer] ✓✓✓ NeuroBus 系统初始化完成 ✓✓✓")
            logger.info("[NeuroBusInitializer] ================================")
            logger.info("[NeuroBusInitializer] 已启用可靠性机制:")
            logger.info("  - 去重器 (Deduplicator)")
            logger.info("  - 链路追踪 (Tracer)")
            logger.info("  - 熔断保护 (Circuit Breaker)")
            logger.info("  - 限流控制 (Rate Limiter)")
            logger.info("  - SLA超时控制 (SLA Controller)")
            logger.info("  - 重试机制 (Retry Handler)")
            logger.info("  - 沙盒预演 (Sandbox)")
            logger.info("  - 保命通道 (Lifeline)")
            logger.info("  - 死信队列 (DLQ)")
            logger.info("  - 事件存储 (Event Store)")
            logger.info("  - 健康监控 (Health Monitor)")

            return True

        except Exception as e:
            logger.error(f"[NeuroBusInitializer] 初始化失败: {e}")
            return False

    def shutdown(self) -> None:
        """关闭所有组件"""
        if not self._initialized:
            return

        try:
            logger.info("[NeuroBusInitializer] 正在关闭 NeuroBus 系统...")

            if self._health_monitor:
                self._health_monitor.stop_monitoring()
                logger.info("[NeuroBusInitializer] ✓ 健康监控已停止")

            self._initialized = False
            logger.info("[NeuroBusInitializer] ✓ NeuroBus 系统已关闭")

        except Exception as e:
            logger.error(f"[NeuroBusInitializer] 关闭时出错: {e}")

    def get_status(self) -> dict:
        """获取初始化状态"""
        return {
            "initialized": self._initialized,
            "components": {
                "neuro_bus": self._bus is not None,
                "dead_letter_queue": self._dlq is not None,
                "event_store": self._event_store is not None,
                "health_monitor": self._health_monitor is not None,
                "retry_handler": self._retry_handler is not None,
                "circuit_breaker": self._circuit_breaker is not None,
                "deduplicator": self._deduplicator is not None,
            },
        }


# ========== 全局初始化器实例 ==========
_initializer: NeuroBusInitializer | None = None


def get_initializer() -> NeuroBusInitializer:
    """获取初始化器单例"""
    global _initializer
    if _initializer is None:
        _initializer = NeuroBusInitializer()
    return _initializer


def initialize_neuro_bus(event_store_mode: EventStoreMode = EventStoreMode.MEMORY) -> bool:
    """便捷函数：初始化 NeuroBus"""
    return get_initializer().initialize(event_store_mode)


def shutdown_neuro_bus() -> None:
    """便捷函数：关闭 NeuroBus"""
    get_initializer().shutdown()
