# -*- coding: utf-8 -*-
"""
性能优化统一初始化器

整合所有性能优化模块，提供：
- 一键初始化
- 统一配置
- 自动注册
- 健康检查
"""

import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """
    性能优化管理器

    统一管理所有优化组件：
    - Redis 缓存
    - 查询优化器
    - 异步任务管理
    - 请求去重
    - 性能监控
    - 限流熔断
    """

    def __init__(self):
        self._initialized = False
        self._redis_cache = None
        self._query_optimizer = None
        self._async_task_manager = None
        self._request_deduplicator = None
        self._performance_monitor = None
        self._start_time = time.time()

    def initialize(self, app=None) -> Dict[str, bool]:
        """
        初始化所有优化组件

        Args:
            app: Flask 应用实例（可选）

        Returns:
            各组件初始化状态
        """
        if self._initialized:
            logger.warning("性能优化器已初始化，跳过重复初始化")
            return self.get_status()

        status = {}
        init_start = time.perf_counter()

        logger.info("=" * 60)
        logger.info("🚀 初始化 XCAGI 性能优化系统")
        logger.info("=" * 60)

        # 1. Redis 缓存
        try:
            from app.utils.redis_cache import init_redis_cache_from_app

            if app:
                self._redis_cache = init_redis_cache_from_app(app)
            else:
                from app.utils.redis_cache import get_redis_cache
                self._redis_cache = get_redis_cache()

            status["redis_cache"] = self._redis_cache is not None and self._redis_cache.is_available
            logger.info(f"✅ Redis 缓存: {'已连接' if status['redis_cache'] else '不可用 (使用本地缓存)'}")
        except Exception as e:
            status["redis_cache"] = False
            logger.warning(f"⚠️  Redis 缓存初始化失败: {e}")

        # 2. 查询优化器
        try:
            from app.utils.query_optimizer import get_query_optimizer
            self._query_optimizer = get_query_optimizer()
            status["query_optimizer"] = True
            logger.info("✅ 查询优化器: 已启用")
        except Exception as e:
            status["query_optimizer"] = False
            logger.error(f"❌ 查询优化器初始化失败: {e}")

        # 3. 异步任务管理
        try:
            from app.utils.async_tasks import get_async_task_manager
            self._async_task_manager = get_async_task_manager()
            status["async_tasks"] = True
            logger.info("✅ 异步任务管理: 已启用")
        except Exception as e:
            status["async_tasks"] = False
            logger.error(f"❌ 异步任务管理初始化失败: {e}")

        # 4. 请求去重
        try:
            from app.utils.request_deduplicator import get_request_deduplicator
            self._request_deduplicator = get_request_deduplicator()
            status["request_dedup"] = True
            logger.info("✅ 请求去重: 已启用")
        except Exception as e:
            status["request_dedup"] = False
            logger.error(f"❌ 请求去重初始化失败: {e}")

        # 5. 性能监控
        try:
            from app.utils.performance_monitor import get_performance_monitor
            self._performance_monitor = get_performance_monitor()
            status["performance_monitor"] = True
            logger.info("✅ 性能监控: 已启用")
        except Exception as e:
            status["performance_monitor"] = False
            logger.error(f"❌ 性能监控初始化失败: {e}")

        # 6. 限流器
        try:
            from app.utils.rate_limiter import get_rate_limiter
            _test_limiter = get_rate_limiter("health_check", max_requests=1000, window_seconds=60)
            status["rate_limiter"] = True
            logger.info("✅ 限流器: 已启用")
        except Exception as e:
            status["rate_limiter"] = False
            logger.error(f"❌ 限流器初始化失败: {e}")

        # 7. 熔断器预加载
        try:
            from app.utils.rate_limiter import get_circuit_breaker
            _test_breaker = get_circuit_breaker("health_check", failure_threshold=10, recovery_timeout=30)
            status["circuit_breaker"] = True
            logger.info("✅ 熔断器: 已启用")
        except Exception as e:
            status["circuit_breaker"] = False
            logger.error(f"❌ 熔断器初始化失败: {e}")

        self._initialized = True
        init_duration = (time.perf_counter() - init_start) * 1000

        success_count = sum(1 for v in status.values() if v)
        total_count = len(status)

        logger.info("=" * 60)
        logger.info(
            f"🎉 性能优化系统初始化完成 ({success_count}/{total_count} 成功, 耗时 {init_duration:.2f}ms)"
        )
        logger.info("=" * 60)

        return status

    def get_status(self) -> Dict[str, Any]:
        """获取所有组件状态"""
        status = {
            "initialized": self._initialized,
            "uptime_seconds": time.time() - self._start_time,
            "components": {},
        }

        if self._redis_cache:
            status["components"]["redis_cache"] = {
                "available": self._redis_cache.is_available,
                "stats": self._redis_cache.stats,
            }

        if self._query_optimizer:
            status["components"]["query_optimizer"] = self._query_optimizer.stats

        if self._async_task_manager:
            status["components"]["async_tasks"] = self._async_task_manager.stats

        if self._request_deduplicator:
            status["components"]["request_dedup"] = self._request_deduplicator.stats

        if self._performance_monitor:
            status["components"]["performance_monitor"] = self._performance_monitor.get_metrics_summary(minutes=5)

        return status

    def get_health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health = {
            "status": "healthy",
            "timestamp": time.time(),
            "checks": {},
        }

        issues = []

        # Redis 检查
        if self._redis_cache:
            redis_ok = self._redis_cache.is_available
            health["checks"]["redis"] = {"status": "ok" if redis_ok else "unavailable"}
            if not redis_ok:
                issues.append("Redis 不可用")

        # 内存检查
        try:
            import psutil
            process = psutil.Process(os.getpid())
            mem_mb = process.memory_info().rss / (1024 * 1024)
            mem_percent = process.memory_percent()

            memory_ok = mem_mb < 1024 and mem_percent < 90
            health["checks"]["memory"] = {
                "status": "ok" if memory_ok else "warning",
                "rss_mb": round(mem_mb, 2),
                "percent": round(mem_percent, 2),
            }

            if not memory_ok:
                issues.append(f"内存使用过高: {mem_mb:.1f}MB ({mem_percent:.1f}%)")

        except ImportError:
            health["checks"]["memory"] = {"status": "unknown"}

        # 任务队列检查
        if self._async_task_manager:
            active_count = len(self._async_task_manager.active_tasks)
            tasks_ok = active_count < 100
            health["checks"]["task_queue"] = {
                "status": "ok" if tasks_ok else "warning",
                "active_tasks": active_count,
            }

            if not tasks_ok:
                issues.append(f"活跃任务过多: {active_count}")

        if issues:
            health["status"] = "degraded"
            health["issues"] = issues

        return health

    @property
    def redis_cache(self):
        return self._redis_cache

    @property
    def query_optimizer(self):
        return self._query_optimizer

    @property
    def async_task_manager(self):
        return self._async_task_manager

    @property
    def request_deduplicator(self):
        return self._request_deduplicator

    @property
    def performance_monitor(self):
        return self._performance_monitor


_optimizer_instance: Optional[PerformanceOptimizer] = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """获取性能优化器单例"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = PerformanceOptimizer()
    return _optimizer_instance


def init_performance_optimization(app=None) -> PerformanceOptimizer:
    """
    一键初始化性能优化（应用启动时调用）

    用法：
        # 在 create_app() 或 main() 中
        from app.utils.performance_initializer import init_performance_optimization
        optimizer = init_performance_optimization(app)
    """
    optimizer = get_performance_optimizer()
    optimizer.initialize(app)

    # 注册 Flask 钩子（如果提供了 app）
    if app:
        _register_flask_hooks(app, optimizer)

    return optimizer


def _register_flask_hooks(app, optimizer: PerformanceOptimizer) -> None:
    """注册 Flask 请求钩子"""
    from flask import request, g

    @app.before_request
    def before_request_hook():
        g.request_start_time = time.perf_counter()

    @app.after_request
    def after_request_hook(response):
        if hasattr(g, 'request_start_time'):
            duration_ms = (time.perf_counter() - g.request_start_time) * 1000

            if optimizer.performance_monitor:
                optimizer.performance_monitor.record_api_call(
                    endpoint=request.endpoint or request.path,
                    method=request.method,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    ip=request.remote_addr
                )

        return response

    @app.teardown_appcontext
    def teardown(exception):
        pass


def optimized_service(service_class):
    """
    服务类装饰器：自动注入优化组件

    用法：
        @optimized_service
        class ProductsService:
            ...
    """
    original_init = service_class.__init__

    @functools.wraps(original_init)
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)

        optimizer = get_performance_optimizer()

        self._cache = optimizer.redis_cache
        self._query_optimizer = optimizer.query_optimizer
        self._async_manager = optimizer.async_task_manager
        self._deduplicator = optimizer.request_deduplicator
        self._monitor = optimizer.performance_monitor

    service_class.__init__ = new_init
    return service_class


import functools
