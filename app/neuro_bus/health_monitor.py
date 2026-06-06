"""
健康检查与监控 - Level 4 可靠性机制

提供：
- 系统健康检查
- 性能监控
- 告警机制
- 仪表盘数据
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.neuro_bus.bus import get_neuro_bus

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """健康状态"""

    HEALTHY = "healthy"  # 健康
    DEGRADED = "degraded"  # 降级
    UNHEALTHY = "unhealthy"  # 不健康
    UNKNOWN = "unknown"  # 未知


class AlertLevel(Enum):
    """告警级别"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class HealthCheckResult:
    """健康检查结果"""

    component: str
    status: HealthStatus
    message: str
    latency_ms: float
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=datetime.now)


@dataclass
class Alert:
    """告警"""

    alert_id: str
    level: AlertLevel
    component: str
    message: str
    created_at: datetime
    resolved_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class HealthMonitor:
    """
    健康监控器

    Level 4 可靠性机制:
    - 定期检查各组件健康状态
    - 收集性能指标
    - 触发告警
    - 提供监控数据
    """

    def __init__(self, check_interval_seconds: int = 30):
        self._check_interval = check_interval_seconds
        self._checks: dict[str, Callable[[], HealthCheckResult]] = {}
        self._last_results: dict[str, HealthCheckResult] = {}
        self._alerts: deque = deque(maxlen=1000)
        self._active_alerts: dict[str, Alert] = {}
        self._metrics_history: dict[str, deque] = {}
        self._is_running = False
        self._task: asyncio.Task | None = None

        # 告警回调
        self._alert_callbacks: list[Callable[[Alert], None]] = []

        # 注册默认检查
        self._register_default_checks()

        logger.info(f"[HealthMonitor] 初始化完成 (interval={check_interval_seconds}s)")

    def _register_default_checks(self):
        """注册默认健康检查"""
        self.register_check("neuro_bus", self._check_neuro_bus)
        self.register_check("event_queue", self._check_event_queue)
        self.register_check("memory", self._check_memory)

    # ========== 健康检查注册 ==========

    def register_check(self, name: str, check_fn: Callable[[], HealthCheckResult]):
        """注册健康检查"""
        self._checks[name] = check_fn
        self._metrics_history[name] = deque(maxlen=100)
        logger.info(f"[HealthMonitor] 注册检查: {name}")

    def unregister_check(self, name: str):
        """注销健康检查"""
        if name in self._checks:
            del self._checks[name]
            del self._last_results[name]
            del self._metrics_history[name]

    # ========== 健康检查实现 ==========

    def _check_neuro_bus(self) -> HealthCheckResult:
        """检查 NeuroBus 状态"""
        t0 = time.perf_counter()

        try:
            bus = get_neuro_bus()
            stats = bus.get_stats()

            latency_ms = (time.perf_counter() - t0) * 1000

            # 判断状态
            if not stats.get("running"):
                status = HealthStatus.UNHEALTHY
                message = "NeuroBus 未运行"
            elif stats.get("queue_size", 0) > 5000:
                status = HealthStatus.DEGRADED
                message = f"队列积压: {stats['queue_size']}"
            elif stats.get("errors", 0) > stats.get("processed", 1) * 0.1:
                status = HealthStatus.DEGRADED
                message = f"错误率过高: {stats['errors']}/{stats.get('processed', 0)}"
            else:
                status = HealthStatus.HEALTHY
                message = "NeuroBus 运行正常"

            return HealthCheckResult(
                component="neuro_bus",
                status=status,
                message=message,
                latency_ms=latency_ms,
                details=stats,
            )

        except Exception as e:
            return HealthCheckResult(
                component="neuro_bus",
                status=HealthStatus.UNHEALTHY,
                message=f"检查失败: {str(e)}",
                latency_ms=(time.perf_counter() - t0) * 1000,
                details={"error": str(e)},
            )

    def _check_event_queue(self) -> HealthCheckResult:
        """检查事件队列状态"""
        t0 = time.perf_counter()

        try:
            bus = get_neuro_bus()
            stats = bus.get_stats()
            queue_size = stats.get("queue_size", 0)
            dropped = stats.get("dropped", 0)

            latency_ms = (time.perf_counter() - t0) * 1000

            if queue_size > 8000:
                status = HealthStatus.UNHEALTHY
                message = f"队列严重积压: {queue_size}"
            elif queue_size > 5000:
                status = HealthStatus.DEGRADED
                message = f"队列积压: {queue_size}"
            elif dropped > 100:
                status = HealthStatus.DEGRADED
                message = f"事件丢弃过多: {dropped}"
            else:
                status = HealthStatus.HEALTHY
                message = f"队列正常: {queue_size}"

            return HealthCheckResult(
                component="event_queue",
                status=status,
                message=message,
                latency_ms=latency_ms,
                details={
                    "queue_size": queue_size,
                    "dropped": dropped,
                },
            )

        except Exception as e:
            return HealthCheckResult(
                component="event_queue",
                status=HealthStatus.UNHEALTHY,
                message=f"检查失败: {str(e)}",
                latency_ms=(time.perf_counter() - t0) * 1000,
            )

    def _check_memory(self) -> HealthCheckResult:
        """检查内存使用"""
        t0 = time.perf_counter()

        try:
            import psutil

            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            latency_ms = (time.perf_counter() - t0) * 1000

            if memory_mb > 1024:  # 1GB
                status = HealthStatus.DEGRADED
                message = f"内存使用较高: {memory_mb:.1f}MB"
            else:
                status = HealthStatus.HEALTHY
                message = f"内存使用正常: {memory_mb:.1f}MB"

            return HealthCheckResult(
                component="memory",
                status=status,
                message=message,
                latency_ms=latency_ms,
                details={"memory_mb": memory_mb},
            )

        except ImportError:
            return HealthCheckResult(
                component="memory",
                status=HealthStatus.UNKNOWN,
                message="无法检查（psutil 未安装）",
                latency_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as e:
            return HealthCheckResult(
                component="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"检查失败: {str(e)}",
                latency_ms=(time.perf_counter() - t0) * 1000,
            )

    # ========== 检查执行 ==========

    async def run_check(self, name: str) -> HealthCheckResult | None:
        """运行单个检查"""
        check_fn = self._checks.get(name)
        if not check_fn:
            return None

        try:
            # 支持异步和同步检查
            if asyncio.iscoroutinefunction(check_fn):
                result = await check_fn()
            else:
                result = check_fn()

            self._last_results[name] = result
            self._metrics_history[name].append(result)

            # 检查是否需要告警
            self._evaluate_alert(result)

            return result

        except Exception as e:
            logger.error(f"[HealthMonitor] 检查失败 {name}: {e}")
            return None

    async def run_all_checks(self) -> dict[str, HealthCheckResult]:
        """运行所有检查"""
        results = {}

        for name in self._checks:
            result = await self.run_check(name)
            if result:
                results[name] = result

        return results

    def _evaluate_alert(self, result: HealthCheckResult):
        """评估是否需要告警"""
        if result.status == HealthStatus.HEALTHY:
            # 检查是否恢复
            self._resolve_alert_if_exists(result.component)
            return

        # 生成告警
        level = (
            AlertLevel.WARNING if result.status == HealthStatus.DEGRADED else AlertLevel.CRITICAL
        )

        alert_id = f"alert-{result.component}-{int(time.time())}"

        alert = Alert(
            alert_id=alert_id,
            level=level,
            component=result.component,
            message=result.message,
            created_at=datetime.now(),
            metadata={
                "latency_ms": result.latency_ms,
                "details": result.details,
            },
        )

        self._alerts.append(alert)
        self._active_alerts[result.component] = alert

        # 触发告警回调
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"[HealthMonitor] 告警回调失败: {e}")

        logger.warning(
            f"[HealthMonitor] 告警: [{level.value}] {result.component} - {result.message}"
        )

    def _resolve_alert_if_exists(self, component: str):
        """解决告警"""
        if component in self._active_alerts:
            alert = self._active_alerts[component]
            alert.resolved_at = datetime.now()
            del self._active_alerts[component]

            logger.info(f"[HealthMonitor] 告警已解决: {component}")

    # ========== 监控循环 ==========

    async def start_monitoring(self):
        """启动监控循环"""
        if self._is_running:
            return

        self._is_running = True
        logger.info("[HealthMonitor] 监控循环已启动")

        while self._is_running:
            try:
                await self.run_all_checks()
                await asyncio.sleep(self._check_interval)
            except Exception as e:
                logger.error(f"[HealthMonitor] 监控循环错误: {e}")
                await asyncio.sleep(5)

    def stop_monitoring(self):
        """停止监控循环"""
        self._is_running = False
        logger.info("[HealthMonitor] 监控循环已停止")

    # ========== 查询 ==========

    def get_health_summary(self) -> dict[str, Any]:
        """获取健康摘要"""
        status_counts = {s.value: 0 for s in HealthStatus}

        for result in self._last_results.values():
            status_counts[result.status.value] += 1

        overall = HealthStatus.HEALTHY
        if status_counts[HealthStatus.UNHEALTHY.value] > 0:
            overall = HealthStatus.UNHEALTHY
        elif status_counts[HealthStatus.DEGRADED.value] > 0:
            overall = HealthStatus.DEGRADED
        elif status_counts[HealthStatus.UNKNOWN.value] > 0:
            overall = HealthStatus.UNKNOWN

        return {
            "overall_status": overall.value,
            "components": len(self._last_results),
            "status_breakdown": status_counts,
            "active_alerts": len(self._active_alerts),
            "last_check": max(
                (r.checked_at.isoformat() for r in self._last_results.values()), default=None
            ),
        }

    def get_component_health(self, component: str) -> HealthCheckResult | None:
        """获取组件健康状态"""
        return self._last_results.get(component)

    def get_all_components_health(self) -> dict[str, HealthCheckResult]:
        """获取所有组件健康状态"""
        return self._last_results.copy()

    def get_active_alerts(self) -> list[Alert]:
        """获取活动告警"""
        return list(self._active_alerts.values())

    def get_alert_history(self, limit: int = 100) -> list[Alert]:
        """获取告警历史"""
        return list(self._alerts)[-limit:]

    def get_metrics_history(self, component: str) -> list[HealthCheckResult]:
        """获取指标历史"""
        return list(self._metrics_history.get(component, []))

    # ========== 回调注册 ==========

    def on_alert(self, callback: Callable[[Alert], None]):
        """注册告警回调"""
        self._alert_callbacks.append(callback)


class DashboardDataProvider:
    """
    仪表盘数据提供者

    为监控仪表盘提供数据
    """

    def __init__(self, monitor: HealthMonitor | None = None):
        self._monitor = monitor or HealthMonitor()

    def get_dashboard_data(self) -> dict[str, Any]:
        """获取完整的仪表盘数据"""
        from app.neuro_bus.dead_letter_queue import get_dead_letter_queue
        from app.neuro_bus.event_store import get_event_store

        bus = get_neuro_bus()
        dlq = get_dead_letter_queue()
        store = get_event_store()

        return {
            "timestamp": datetime.now().isoformat(),
            "health": self._monitor.get_health_summary(),
            "neuro_bus": bus.get_stats(),
            "dead_letter_queue": dlq.get_stats(),
            "event_store": store.get_stats(),
            "active_alerts": [
                {
                    "id": a.alert_id,
                    "level": a.level.value,
                    "component": a.component,
                    "message": a.message,
                    "created_at": a.created_at.isoformat(),
                }
                for a in self._monitor.get_active_alerts()
            ],
        }


# ========== 全局实例 ==========

_health_monitor_instance: HealthMonitor | None = None


def get_health_monitor() -> HealthMonitor:
    """获取全局健康监控器"""
    global _health_monitor_instance
    if _health_monitor_instance is None:
        _health_monitor_instance = HealthMonitor()
    return _health_monitor_instance


# 快捷函数


def get_health() -> dict[str, Any]:
    """快捷函数：获取健康状态"""
    return get_health_monitor().get_health_summary()


def check_component(component: str) -> HealthCheckResult | None:
    """快捷函数：检查组件"""
    return get_health_monitor().get_component_health(component)


def get_system_status() -> str:
    """快捷函数：获取系统状态字符串"""
    summary = get_health()
    return summary.get("overall_status", "unknown")
