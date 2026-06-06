"""
SLA 超时控制器

分级超时控制：
- Reflex 级: < 1ms (99th percentile)
- Subconscious 级: < 10ms (95th percentile)
- Conscious 级: < 200ms (95th percentile)
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.neuro_bus.events.base import EventPriority, NeuroEvent

logger = logging.getLogger(__name__)


class SLALevel(Enum):
    """SLA 级别"""

    REFLEX = "reflex"  # < 1ms
    SUBCONSCIOUS = "subconscious"  # < 10ms
    CONSCIOUS = "conscious"  # < 200ms


@dataclass
class SLATimeout:
    """SLA 超时配置"""

    target_ms: float
    max_ms: float
    warning_threshold_ms: float


class SLAConfig:
    """SLA 配置"""

    REFLEX = SLATimeout(
        target_ms=1.0,
        max_ms=5.0,
        warning_threshold_ms=0.8,
    )

    SUBCONSCIOUS = SLATimeout(
        target_ms=10.0,
        max_ms=50.0,
        warning_threshold_ms=8.0,
    )

    CONSCIOUS = SLATimeout(
        target_ms=200.0,
        max_ms=5000.0,
        warning_threshold_ms=180.0,
    )

    @classmethod
    def get_for_level(cls, level: SLALevel) -> SLATimeout:
        """获取指定级别的配置"""
        return getattr(cls, level.value.upper())


class SLAMonitor:
    """
    SLA 监控器

    监控单个操作的 SLA 合规性
    """

    def __init__(self, sla_timeout: SLATimeout, operation_name: str):
        self._sla = sla_timeout
        self._operation_name = operation_name
        self._start_time = time.time()
        self._finished = False

    def check(self) -> dict[str, Any]:
        """检查当前 SLA 状态"""
        elapsed_ms = (time.time() - self._start_time) * 1000

        status = "ok"
        if elapsed_ms > self._sla.max_ms:
            status = "violated"
        elif elapsed_ms > self._sla.warning_threshold_ms:
            status = "warning"

        return {
            "operation": self._operation_name,
            "elapsed_ms": elapsed_ms,
            "target_ms": self._sla.target_ms,
            "max_ms": self._sla.max_ms,
            "status": status,
        }

    def finish(self) -> dict[str, Any]:
        """完成监控，返回报告"""
        self._finished = True
        result = self.check()

        if result["status"] == "violated":
            logger.error(
                f"SLA VIOLATED: {self._operation_name} took {result['elapsed_ms']:.2f}ms, "
                f"max allowed: {self._sla.max_ms}ms"
            )
        elif result["status"] == "warning":
            logger.warning(
                f"SLA WARNING: {self._operation_name} took {result['elapsed_ms']:.2f}ms, "
                f"target: {self._sla.target_ms}ms"
            )

        return result

    def is_violated(self) -> bool:
        """检查是否已违反 SLA"""
        return self.check()["status"] == "violated"


class SLAController:
    """
    SLA 控制器

    统一管理事件处理的 SLA
    """

    def __init__(self):
        self._active_monitors: dict[str, SLAMonitor] = {}
        self._violation_count = 0
        self._warning_count = 0

    def determine_sla_level(self, event: NeuroEvent) -> SLALevel:
        """
        根据事件特征确定 SLA 级别
        """
        # 基于事件类型判断
        event_type = event.event_type.lower()

        # Reflex 级事件（紧急、简单响应）
        reflex_patterns = ["reflex", "greeting", "emergency", "confirm", "deny", "ping"]
        if any(p in event_type for p in reflex_patterns):
            return SLALevel.REFLEX

        # Subconscious 级（后台、非关键）
        if event.priority in [EventPriority.LOW, EventPriority.BACKGROUND]:
            return SLALevel.SUBCONSCIOUS

        # Conscious 级（默认）
        return SLALevel.CONSCIOUS

    def start_monitoring(self, event: NeuroEvent) -> SLAMonitor:
        """开始监控事件处理"""
        sla_level = self.determine_sla_level(event)
        sla_timeout = SLAConfig.get_for_level(sla_level)

        monitor = SLAMonitor(
            sla_timeout=sla_timeout, operation_name=f"{event.event_type}@{event.metadata.domain}"
        )

        self._active_monitors[event.metadata.event_id] = monitor

        # 设置事件超时
        event.metadata.timeout_ms = int(sla_timeout.max_ms)

        return monitor

    def finish_monitoring(self, event_id: str) -> dict[str, Any] | None:
        """完成监控"""
        if event_id in self._active_monitors:
            monitor = self._active_monitors.pop(event_id)
            result = monitor.finish()

            if result["status"] == "violated":
                self._violation_count += 1
            elif result["status"] == "warning":
                self._warning_count += 1

            return result
        return None

    def check_violations(self) -> list:
        """检查所有活跃的 SLA 违规"""
        violations = []
        for event_id, monitor in list(self._active_monitors.items()):
            if monitor.is_violated():
                violations.append(
                    {
                        "event_id": event_id,
                        "operation": monitor._operation_name,
                    }
                )
        return violations

    def get_stats(self) -> dict:
        """获取统计"""
        return {
            "active_monitors": len(self._active_monitors),
            "total_violations": self._violation_count,
            "total_warnings": self._warning_count,
        }


# 超时装饰器


def with_sla(level: SLALevel, fallback=None):
    """
    SLA 超时装饰器

    用法:
        @with_sla(SLALevel.REFLEX)
        async def handle_greeting(event):
            pass
    """

    def decorator(func):
        sla_config = SLAConfig.get_for_level(level)

        async def wrapper(*args, **kwargs):
            start = time.time()

            try:
                # 使用 asyncio.wait_for 实现超时
                timeout_sec = sla_config.max_ms / 1000.0
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_sec)

                elapsed_ms = (time.time() - start) * 1000
                if elapsed_ms > sla_config.target_ms:
                    logger.warning(
                        f"SLA warning: {func.__name__} took {elapsed_ms:.2f}ms, "
                        f"target: {sla_config.target_ms}ms"
                    )

                return result

            except TimeoutError:
                logger.error(f"SLA violated: {func.__name__} exceeded {sla_config.max_ms}ms")
                if fallback:
                    return fallback(*args, **kwargs)
                raise SLAViolation(f"Operation exceeded SLA of {sla_config.max_ms}ms")

        return wrapper

    return decorator


class SLAViolation(Exception):
    """SLA 违规异常"""

    pass
