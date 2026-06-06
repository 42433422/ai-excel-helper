"""
保命通道（Lifeline）

系统过载时保关键路径，丢弃低优先级
支持：
- 资源监控
- 动态降级
- 关键路径保护
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from threading import RLock

from app.neuro_bus.events.base import EventPriority, NeuroEvent

logger = logging.getLogger(__name__)


class SystemLoad(Enum):
    """系统负载级别"""

    NORMAL = "normal"  # 正常
    ELEVATED = "elevated"  # 较高
    HIGH = "high"  # 高
    CRITICAL = "critical"  # 临界
    EMERGENCY = "emergency"  # 紧急


@dataclass
class ResourceMetrics:
    """资源指标"""

    cpu_percent: float
    memory_percent: float
    queue_depth: int
    event_rate: float  # 事件/秒
    error_rate: float  # 错误率


class Lifeline:
    """
    保命通道

    系统过载时的最后一道防线
    """

    def __init__(
        self,
        queue_threshold_normal: int = 1000,
        queue_threshold_high: int = 5000,
        queue_threshold_critical: int = 8000,
    ):
        self._thresholds = {
            SystemLoad.NORMAL: queue_threshold_normal,
            SystemLoad.ELEVATED: queue_threshold_high * 0.7,
            SystemLoad.HIGH: queue_threshold_high,
            SystemLoad.CRITICAL: queue_threshold_critical,
            SystemLoad.EMERGENCY: queue_threshold_critical * 1.5,
        }

        self._current_load = SystemLoad.NORMAL
        self._last_check = time.time()
        self._check_interval = 1.0  # 检查间隔

        self._dropped_stats: dict[str, int] = {}
        self._protected_stats: dict[str, int] = {}

        self._lock = RLock()

        # 各负载级别允许的最低优先级
        self._min_priority = {
            SystemLoad.NORMAL: EventPriority.BACKGROUND,
            SystemLoad.ELEVATED: EventPriority.LOW,
            SystemLoad.HIGH: EventPriority.NORMAL,
            SystemLoad.CRITICAL: EventPriority.HIGH,
            SystemLoad.EMERGENCY: EventPriority.CRITICAL,
        }

        # 回调
        self._on_load_change: Callable[[SystemLoad, SystemLoad], None] | None = None

        logger.info("Lifeline initialized")

    def set_load_change_callback(self, callback: Callable[[SystemLoad, SystemLoad], None]):
        """设置负载变化回调"""
        self._on_load_change = callback

    def check_system_load(
        self,
        queue_depth: int,
        cpu_percent: float | None = None,
        memory_percent: float | None = None,
    ) -> SystemLoad:
        """
        检查系统负载

        基于队列深度和资源使用率判断
        """
        with self._lock:
            now = time.time()
            if now - self._last_check < self._check_interval:
                return self._current_load

            self._last_check = now
            old_load = self._current_load

            # 判断负载级别
            if queue_depth >= self._thresholds[SystemLoad.EMERGENCY]:
                new_load = SystemLoad.EMERGENCY
            elif queue_depth >= self._thresholds[SystemLoad.CRITICAL]:
                new_load = SystemLoad.CRITICAL
            elif queue_depth >= self._thresholds[SystemLoad.HIGH]:
                new_load = SystemLoad.HIGH
            elif queue_depth >= self._thresholds[SystemLoad.ELEVATED]:
                new_load = SystemLoad.ELEVATED
            else:
                new_load = SystemLoad.NORMAL

            # 考虑资源使用率
            if cpu_percent and cpu_percent > 90:
                new_load = min(SystemLoad(new_load.value), SystemLoad.CRITICAL)
            if memory_percent and memory_percent > 85:
                new_load = min(SystemLoad(new_load.value), SystemLoad.HIGH)

            # 触发回调
            if new_load != old_load:
                logger.warning(f"System load changed: {old_load.value} -> {new_load.value}")
                self._current_load = new_load

                if self._on_load_change:
                    try:
                        self._on_load_change(old_load, new_load)
                    except Exception as e:
                        logger.exception(f"Load change callback error: {e}")

            return self._current_load

    def should_process(self, event: NeuroEvent, queue_depth: int) -> bool:
        """
        判断是否应该处理该事件

        Returns:
            True: 应该处理
            False: 应该丢弃
        """
        with self._lock:
            load = self.check_system_load(queue_depth)
            min_priority = self._min_priority[load]

            # 优先级数值越小越重要
            if event.priority.value <= min_priority.value:
                self._protected_stats[event.event_type] = (
                    self._protected_stats.get(event.event_type, 0) + 1
                )
                return True

            # 丢弃
            self._dropped_stats[event.event_type] = self._dropped_stats.get(event.event_type, 0) + 1

            logger.warning(
                f"Lifeline dropped event: {event.event_type} "
                f"(priority={event.priority.name}, load={load.value})"
            )
            return False

    def get_emergency_recommendations(self) -> list[str]:
        """获取紧急状态下的建议"""
        load = self._current_load

        if load == SystemLoad.NORMAL:
            return []

        if load == SystemLoad.ELEVATED:
            return [
                "Monitor queue growth rate",
                "Consider scaling workers",
            ]

        if load == SystemLoad.HIGH:
            return [
                "Scale up worker instances",
                "Review high-frequency event sources",
                "Enable circuit breakers if not already",
            ]

        if load == SystemLoad.CRITICAL:
            return [
                "URGENT: Scale immediately",
                "Review and disable non-essential features",
                "Alert on-call team",
            ]

        if load == SystemLoad.EMERGENCY:
            return [
                "CRITICAL: Emergency response needed",
                "Only critical events are being processed",
                "Consider graceful degradation mode",
            ]

        return []

    def get_stats(self) -> dict:
        """获取统计"""
        with self._lock:
            return {
                "current_load": self._current_load.value,
                "thresholds": {k.value: v for k, v in self._thresholds.items()},
                "dropped_events": self._dropped_stats.copy(),
                "protected_events": self._protected_stats.copy(),
                "total_dropped": sum(self._dropped_stats.values()),
                "total_protected": sum(self._protected_stats.values()),
            }


class NeuroLifeline:
    """
    NeuroBus 保命通道

    集成到总线的事件处理流程中
    """

    def __init__(self):
        self._lifeline = Lifeline()
        self._queue_depth_fn: Callable[[], int] | None = None

    def set_queue_depth_provider(self, fn: Callable[[], int]):
        """设置队列深度获取函数"""
        self._queue_depth_fn = fn

    def check_event(self, event: NeuroEvent) -> bool:
        """
        检查事件是否可以通过保命通道

        Returns:
            True: 允许通过
            False: 被丢弃
        """
        if not self._queue_depth_fn:
            return True

        queue_depth = self._queue_depth_fn()
        return self._lifeline.should_process(event, queue_depth)

    def check_critical_only_mode(self) -> bool:
        """检查是否处于仅关键模式"""
        stats = self._lifeline.get_stats()
        return stats["current_load"] in ["critical", "emergency"]

    def get_stats(self) -> dict:
        """获取统计"""
        return self._lifeline.get_stats()

    def get_recommendations(self) -> list[str]:
        """获取当前建议"""
        return self._lifeline.get_emergency_recommendations()


# 关键路径定义

CRITICAL_PATH_DOMAINS = {
    "safety",
    "payment",
    "emergency",
}

CRITICAL_PATH_EVENTS = {
    "user.login",
    "user.logout",
    "payment.process",
    "emergency.stop",
    "system.error",
}


def is_critical_path(event: NeuroEvent) -> bool:
    """判断是否为关键路径事件"""
    if event.metadata.domain in CRITICAL_PATH_DOMAINS:
        return True
    if event.event_type in CRITICAL_PATH_EVENTS:
        return True
    if event.priority == EventPriority.CRITICAL:
        return True
    return False
