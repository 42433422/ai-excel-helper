# -*- coding: utf-8 -*-
"""
性能监控器

提供全面的性能监控和指标收集：
- API 响应时间监控
- 内存使用监控
- 函数执行计时
- 性能瓶颈检测
- 告警机制
- Prometheus 指标导出
"""

import functools
import logging
import os
import time
import traceback
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

PERFORMANCE_HISTORY_SIZE = int(os.environ.get("XCAGI_PERF_HISTORY_SIZE", "1000"))
SLOW_API_THRESHOLD_MS = float(os.environ.get("XCAGI_SLOW_API_THRESHOLD", "1000"))
MEMORY_WARNING_MB = int(os.environ.get("XCAGI_MEMORY_WARNING", "512"))


@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    duration_ms: float
    timestamp: float = field(default_factory=time.time)
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class APIMetric:
    """API 指标"""
    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    timestamp: float = field(default_factory=time.time)
    user_id: Optional[str] = None
    ip: Optional[str] = None


@dataclass
class MemorySnapshot:
    """内存快照"""
    timestamp: float
    rss_mb: float
    vms_mb: float
    percent: float
    cache_objects: int = 0


@dataclass
class PerformanceAlert:
    """性能告警"""
    level: str  # warning, critical
    metric_type: str
    message: str
    value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)


class PerformanceMonitor:
    """
    性能监控器

    功能：
    - 实时性能指标收集
    - 历史数据存储
    - 自动告警
    - 统计分析
    - Prometheus 格式导出
    """

    def __init__(self, history_size: int = PERFORMANCE_HISTORY_SIZE):
        self._history_size = history_size
        self._metrics: Deque[PerformanceMetric] = deque(maxlen=history_size)
        self._api_metrics: Deque[APIMetric] = deque(maxlen=history_size)
        self._alerts: Deque[PerformanceAlert] = deque(maxlen=100)
        self._memory_history: Deque[MemorySnapshot] = deque(maxlen=3600)
        self._lock = Lock()
        self._function_timers: Dict[str, List[float]] = {}
        self._slow_api_threshold = SLOW_API_THRESHOLD_MS

    def record_metric(
        self,
        name: str,
        duration_ms: float,
        success: bool = True,
        **metadata
    ) -> None:
        """记录性能指标"""
        metric = PerformanceMetric(
            name=name,
            duration_ms=duration_ms,
            success=success,
            metadata=metadata
        )

        with self._lock:
            self._metrics.append(metric)

        if not success or duration_ms > self._slow_api_threshold:
            logger.warning(f"性能异常 [{name}]: {duration_ms:.2f}ms")

    def record_api_call(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        ip: Optional[str] = None
    ) -> None:
        """记录 API 调用"""
        api_metric = APIMetric(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            ip=ip
        )

        with self._lock:
            self._api_metrics.append(api_metric)

        if duration_ms > self._slow_api_threshold:
            alert = PerformanceAlert(
                level="warning",
                metric_type="slow_api",
                message=f"慢API: {method} {endpoint}",
                value=duration_ms,
                threshold=self._slow_api_threshold
            )
            self._add_alert(alert)

    def record_memory(self) -> MemorySnapshot:
        """记录内存使用情况"""
        try:
            import psutil

            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()

            snapshot = MemorySnapshot(
                timestamp=time.time(),
                rss_mb=mem_info.rss / (1024 * 1024),
                vms_mb=mem_info.vms / (1024 * 1024),
                percent=process.memory_percent(),
            )

            with self._lock:
                self._memory_history.append(snapshot)

            if snapshot.rss_mb > MEMORY_WARNING_MB:
                alert = PerformanceAlert(
                    level="warning",
                    metric_type="high_memory",
                    message=f"内存使用过高: {snapshot.rss_mb:.1f}MB",
                    value=snapshot.rss_mb,
                    threshold=MEMORY_WARNING_MB
                )
                self._add_alert(alert)

            return snapshot

        except ImportError:
            return MemorySnapshot(timestamp=time.time(), rss_mb=0, vms_mb=0, percent=0)

    def _add_alert(self, alert: PerformanceAlert) -> None:
        """添加告警"""
        with self._lock:
            self._alerts.append(alert)

        log_func = logger.warning if alert.level == "warning" else logger.critical
        log_func(f"[{alert.level.upper()}] {alert.message}: {alert.value:.2f} (阈值: {alert.threshold})")

    @contextmanager
    def track(self, name: str, **metadata):
        """
        性能跟踪上下文管理器

        用法：
            with monitor.track("database_query"):
                result = db.session.query(...)
        """
        start_time = time.perf_counter()
        error_occurred = False

        try:
            yield
        except Exception as e:
            error_occurred = True
            metadata["error"] = str(e)
            raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.record_metric(name, duration_ms, success=not error_occurred, **metadata)

    def timer(self, name: Optional[str] = None, include_args: bool = False):
        """
        计时装饰器

        用法：
            @monitor.timer("expensive_function")
            def my_function():
                ...
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                metric_name = name or f"{func.__module__}.{func.__name__}"
                if include_args:
                    metric_name = f"{metric_name}:{str(args)[:50]}"

                start_time = time.perf_counter()

                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    self.record_metric(metric_name, duration_ms, success=True)
                    return result

                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    self.record_metric(metric_name, duration_ms, success=False, error=str(e))
                    raise

            return wrapper
        return decorator

    def api_timer(self):
        """
        API 计时装饰器（用于 Flask 路由）

        用法：
            @app.route("/api/data")
            @monitor.api_timer()
            def get_data():
                ...
        """
        from flask import request, g

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                g.request_start_time = start_time

                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start_time) * 1000

                    self.record_api_call(
                        endpoint=request.endpoint or request.path,
                        method=request.method,
                        status_code=getattr(g, 'response_status_code', 200),
                        duration_ms=duration_ms,
                        user_id=str(g.get('user_id', '')) or None,
                        ip=request.remote_addr
                    )

                    return result

                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    self.record_api_call(
                        endpoint=request.endpoint or request.path,
                        method=request.method,
                        status_code=500,
                        duration_ms=duration_ms,
                        ip=request.remote_addr
                    )
                    raise

            return wrapper
        return decorator

    def get_metrics_summary(self, minutes: int = 5) -> Dict[str, Any]:
        """获取指标摘要（最近 N 分钟）"""
        cutoff = time.time() - (minutes * 60)

        recent_metrics = [m for m in self._metrics if m.timestamp >= cutoff]
        recent_api = [a for a in self._api_metrics if a.timestamp >= cutoff]

        if not recent_metrics and not recent_api:
            return {"message": "暂无数据"}

        durations = [m.duration_ms for m in recent_metrics]
        api_durations = [a.duration_ms for a in recent_api]

        summary = {
            "period_minutes": minutes,
            "total_calls": len(recent_metrics) + len(recent_api),
            "avg_duration_ms": round(sum(durations) / len(durations), 3) if durations else 0,
            "max_duration_ms": round(max(durations), 3) if durations else 0,
            "min_duration_ms": round(min(durations), 3) if durations else 0,
            "p95_duration_ms": round(sorted(durations)[int(len(durations) * 0.95)], 3) if len(durations) > 20 else 0,
            "p99_duration_ms": round(sorted(durations)[int(len(durations) * 0.99)], 3) if len(durations) > 100 else 0,
            "success_rate": round(sum(1 for m in recent_metrics if m.success) / len(recent_metrics) * 100, 2) if recent_metrics else 100,
            "api_stats": {
                "total": len(recent_api),
                "avg_ms": round(sum(api_durations) / len(api_durations), 3) if api_durations else 0,
                "slow_count": sum(1 for a in recent_api if a.duration_ms > self._slow_api_threshold),
                "error_4xx": sum(1 for a in recent_api if 400 <= a.status_code < 500),
                "error_5xx": sum(1 for a in recent_api if a.status_code >= 500),
            },
            "top_slow_endpoints": self._get_top_slow_endpoints(recent_api, limit=10),
            "active_alerts": len([a for a in self._alerts if a.timestamp >= cutoff]),
        }

        latest_memory = list(self._memory_history)[-1] if self._memory_history else None
        if latest_memory:
            summary["memory"] = {
                "rss_mb": round(latest_memory.rss_mb, 2),
                "vms_mb": round(latest_memory.vms_mb, 2),
                "percent": round(latest_memory.percent, 2),
            }

        return summary

    def _get_top_slow_endpoints(self, api_list: List[APIMetric], limit: int = 10) -> List[Dict]:
        """获取最慢的端点"""
        endpoint_times: Dict[str, List[float]] = {}

        for api in api_list:
            key = f"{api.method} {api.endpoint}"
            if key not in endpoint_times:
                endpoint_times[key] = []
            endpoint_times[key].append(api.duration_ms)

        sorted_endpoints = sorted(
            endpoint_times.items(),
            key=lambda x: sum(x[1]) / len(x[1]),
            reverse=True
        )[:limit]

        return [
            {
                "endpoint": ep,
                "avg_ms": round(sum(times) / len(times), 2),
                "count": len(times),
                "max_ms": round(max(times), 2),
            }
            for ep, times in sorted_endpoints
        ]

    def get_prometheus_metrics(self) -> str:
        """导出 Prometheus 格式指标"""
        lines = []

        lines.append("# HELP xcagi_request_duration_seconds Request duration in seconds")
        lines.append("# TYPE xcagi_request_duration_seconds summary")

        for metric in list(self._metrics)[-100:]:
            labels = f'{{name="{metric.name}",success="{str(metric.success).lower()}"}}'
            lines.append(f"xcagi_request_duration_seconds{labels} {metric.duration_ms / 1000:.6f}")

        lines.append("")
        lines.append("# HELP xcagi_api_requests_total Total API requests")
        lines.append("# TYPE xcagi_api_requests_total counter")

        endpoint_counts: Dict[str, int] = {}
        for api in list(self._api_metrics)[-500:]:
            key = f'{api.method}_{api.endpoint.replace("/", "_")}'
            endpoint_counts[key] = endpoint_counts.get(key, 0) + 1

        for endpoint, count in endpoint_counts.items():
            lines.append(f'xcagi_api_requests_total{{endpoint="{endpoint}"}} {count}')

        return "\n".join(lines)

    def get_alerts(self, level: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """获取告警列表"""
        alerts = list(self._alerts)

        if level:
            alerts = [a for a in alerts if a.level == level]

        return [
            {
                "level": a.level,
                "type": a.metric_type,
                "message": a.message,
                "value": round(a.value, 3),
                "threshold": a.threshold,
                "timestamp": a.timestamp,
            }
            for a in alerts[-limit:]
        ]

    def clear_history(self) -> None:
        """清除历史数据"""
        with self._lock:
            self._metrics.clear()
            self._api_metrics.clear()
            self._alerts.clear()


_performance_monitor_instance: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器单例"""
    global _performance_monitor_instance
    if _performance_monitor_instance is None:
        _performance_monitor_instance = PerformanceMonitor()
    return _performance_monitor_instance


def performance_timer(name: Optional[str] = None):
    """性能计时装饰器（快捷方式）"""
    monitor = get_performance_monitor()
    return monitor.timer(name=name)
