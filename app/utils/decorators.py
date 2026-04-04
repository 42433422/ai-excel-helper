# -*- coding: utf-8 -*-
"""
XCAGI 服务优化装饰器集合

提供一键式性能优化装饰器，适用于任何服务类或函数：
- 缓存装饰器
- 限流装饰器
- 监控装饰器
- 去重装饰器
- 异步任务装饰器
- 熔断装饰器
"""

import functools
import hashlib
import logging
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


def get_optimizer_components():
    """获取所有优化组件（懒加载）"""
    components = {
        'cache': None,
        'monitor': None,
        'deduplicator': None,
        'async_manager': None,
    }

    try:
        from app.utils.performance_initializer import get_performance_optimizer
        optimizer = get_performance_optimizer()

        if optimizer.redis_cache:
            components['cache'] = optimizer.redis_cache
        if optimizer.performance_monitor:
            components['monitor'] = optimizer.performance_monitor
        if optimizer.request_deduplicator:
            components['deduplicator'] = optimizer.request_deduplicator
        if optimizer.async_task_manager:
            components['async_manager'] = optimizer.async_task_manager

    except Exception as e:
        logger.debug(f"优化组件加载失败: {e}")

    return components


class OptimizedServiceMixin:
    """
    服务优化混入类

    用法：
        class MyService(OptimizedServiceMixin):
            def __init__(self):
                self._init_optimizers()

            @cached(ttl=300)
            @rate_limited(max_requests=30)
            @monitored("my_method")
            def my_expensive_method(self, param):
                ...
    """

    def _init_optimizers(self):
        """初始化所有优化组件"""
        components = get_optimizer_components()

        self._cache = components['cache']
        self._monitor = components['monitor']
        self._deduplicator = components['deduplicator']
        self._async_manager = components['async_manager']

        logger.debug(f"服务 {self.__class__.__name__} 优化组件已初始化")


def cached(
    ttl: int = 300,
    key_prefix: str = "",
    cache_instance=None,
    skip_args: Optional[List[int]] = None
):
    """
    Redis缓存装饰器

    自动缓存函数返回值，支持TTL过期

    Args:
        ttl: 缓存时间(秒)
        key_prefix: 键前缀
        cache_instance: 自定义缓存实例(可选)
        skip_args: 跳过的参数索引(如self)

    示例：
        @cached(ttl=600, key_prefix="product:")
        def get_product(product_id):
            return db.query(Product).get(product_id)
    """
    skip_args = skip_args or []

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取缓存实例
            cache = cache_instance
            if not cache:
                components = get_optimizer_components()
                cache = components.get('cache')

            if not cache:
                return func(*args, **kwargs)

            # 生成缓存键
            try:
                parts = [func.__name__]
                for i, arg in enumerate(args):
                    if i not in skip_args:
                        parts.append(str(arg))
                for k, v in sorted(kwargs.items()):
                    parts.append(f"{k}={v}")

                key_str = ":".join(parts)
                cache_key = f"{key_prefix}{hashlib.md5(key_str.encode()).hexdigest()}"

                # 尝试从缓存获取
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # 执行并缓存
                result = func(*args, **kwargs)

                if result is not None:
                    cache.set(cache_key, result, ttl=ttl)

                return result

            except Exception as e:
                logger.warning(f"缓存操作失败 [{func.__name__}]: {e}")
                return func(*args, **kwargs)

        wrapper.invalidate_cache = lambda *a, **kw: (
            cache.delete(f"{key_prefix}{hashlib.md5(str(a + tuple(sorted(kw.items()))).encode()).hexdigest()}")
            if cache else None
        )

        return wrapper
    return decorator


def rate_limited(
    max_requests: int = 60,
    window_seconds: int = 60,
    key_func: Optional[Callable] = None
):
    """
    限流装饰器

    基于用户/会话的请求频率限制

    Args:
        max_requests: 最大请求数
        window_seconds: 时间窗口(秒)
        key_func: 自定义键生成函数

    示例：
        @rate_limited(max_requests=30, window_seconds=60)
        def ai_chat(user_id, message):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                from app.utils.rate_limiter import check_rate_limit

                identifier = None
                if key_func:
                    identifier = key_func(*args, **kwargs)
                elif args and hasattr(args[0], '__dict__'):
                    identifier = str(id(args[0]))
                elif args:
                    identifier = str(args[0])

                if identifier:
                    result = check_rate_limit(identifier, func.__name__, max_requests, window_seconds)
                    if not result.get('allowed', True):
                        from flask import jsonify
                        return jsonify({
                            "error": "请求过于频繁",
                            "retry_after": result.get('retry_after'),
                        }), 429

                return func(*args, **kwargs)

            except Exception as e:
                logger.warning(f"限流检查失败 [{func.__name__}]: {e}")
                return func(*args, **kwargs)

        return wrapper
    return decorator


def monitored(name: Optional[str] = None, slow_threshold_ms: float = 1000.0):
    """
    性能监控装饰器

    记录函数执行时间和状态

    Args:
        name: 指标名称(默认使用函数名)
        slow_threshold_ms: 慢调用阈值(ms)

    示例：
        @monitored("database_query", slow_threshold_ms=500)
        def query_users():
            ...
    """
    def decorator(func: Callable) -> Callable:
        metric_name = name or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            components = get_optimizer_components()
            monitor = components.get('monitor')

            if not monitor:
                return func(*args, **kwargs)

            start_time = time.perf_counter()

            try:
                with monitor.track(metric_name):
                    result = func(*args, **kwargs)

                duration_ms = (time.perf_counter() - start_time) * 1000

                if duration_ms > slow_threshold_ms:
                    logger.warning(
                        f"慢调用检测 [{metric_name}]: {duration_ms:.2f}ms > {slow_threshold_ms:.0f}ms"
                    )

                return result

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                monitor.record_metric(metric_name, duration_ms, success=False, error=str(e)[:200])
                raise

        return wrapper
    return decorator


def deduplicated(window_seconds: int = 30, by_content: bool = True):
    """
    请求去重装饰器

    防止相同参数的重复调用

    Args:
        window_seconds: 去重时间窗口(秒)
        by_content: 是否基于内容去重(True)还是仅基于参数数量(False)

    示例：
        @deduplicated(window_seconds=60)
        def create_order(customer_id, product_id):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            components = get_optimizer_components()
            deduplicator = components.get('deduplicator')

            if not deduplicator:
                return func(*args, **kwargs)

            is_dup, result = deduplicator.deduplicate(
                func, *args, **kwargs
            )

            if is_dup:
                logger.debug(f"去重命中 [{func.__name__}]")

            return result

        return wrapper
    return decorator


def async_task(
    task_name: Optional[str] = None,
    queue: str = "normal",
    timeout: int = 300,
    retry_on_failure: bool = True
):
    """
    异步任务装饰器

    将同步函数转换为可异步执行的版本

    Args:
        task_name: 任务名称
        queue: 队列名称(normal/heavy/urgent/wechat)
        timeout: 超时时间(秒)
        retry_on_failure: 失败时是否自动重试

    示例：
        @async_task(queue="heavy", timeout=600)
        def generate_report(month, year):
            ...

        # 同步调用：result = generate_report("01", 2026)
        # 异步调用：task = generate_report.async_submit("01", 2026)
    """
    def decorator(func: Callable) -> Callable:
        name = task_name or f"task_{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            components = get_optimizer_components()
            async_manager = components.get('async_manager')

            force_sync = __import__('os').environ.get('XCAGI_FORCE_SYNC_TASKS', '0') == '1'

            if force_sync or not async_manager:
                return func(*args, **kwargs)

            task_result = async_manager.submit(
                name, args, kwargs, queue=queue
            )

            if task_result.is_success:
                return task_result.result

            if task_result.is_failed:
                raise Exception(task_result.error or "任务执行失败")

            return {"task_id": task_result.task_id, "status": task_result.status.value}

        def async_submit(*a, **kw):
            """异步提交方法"""
            components = get_optimizer_components()
            async_manager = components.get('async_manager')

            if async_manager:
                return async_manager.submit(name, a, kw, queue=queue)

            raise RuntimeError("异步任务管理器未初始化")

        wrapper.async_submit = staticmethod(async_submit)
        wrapper.task_name = name
        wrapper.queue = queue

        return wrapper
    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 30,
    fallback_func: Optional[Callable] = None
):
    """
    熔断装饰器

    当连续失败达到阈值时，暂时停止调用，直接返回降级结果

    Args:
        failure_threshold: 触发熔断的连续失败次数
        recovery_timeout: 熔断恢复等待时间(秒)
        fallback_func: 降级函数(可选)

    示例：
        @circuit_breaker(failure_threshold=3, recovery_timeout=60)
        def call_external_api():
            ...

        @circuit_breaker(failure_threshold=5, fallback_func=lambda: {"data": []})
        def fetch_remote_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        state = {
            'failures': 0,
            'last_failure_time': 0,
            'is_open': False,
        }

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()

            # 检查是否在熔断状态
            if state['is_open']:
                if current_time - state['last_failure_time'] < recovery_timeout:
                    if fallback_func:
                        logger.info(f"熔断降级 [{func.__name__}]")
                        return fallback_func(*args, **kwargs)
                    raise Exception(f"服务熔断中，{recovery_timeout}s后重试")
                else:
                    state['is_open'] = False
                    state['failures'] = 0
                    logger.info(f"熔断恢复 [{func.__name__}]")

            try:
                result = func(*args, **kwargs)
                state['failures'] = 0
                return result

            except Exception as e:
                state['failures'] += 1
                state['last_failure_time'] = current_time

                if state['failures'] >= failure_threshold:
                    state['is_open'] = True
                    logger.error(
                        f"熔断触发 [{func.__name__}]: 连续失败 {state['failures']} 次"
                    )

                raise

        return wrapper
    return decorator


def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    重试装饰器

    失败时自动重试，支持指数退避

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟(秒)
        backoff_factor: 退避因子
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数

    示例：
        @retry(max_retries=3, delay=2, backoff_factor=2, exceptions=(ConnectionError,))
        def unreliable_api_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        if on_retry:
                            on_retry(attempt + 1, max_retries, e)

                        logger.warning(
                            f"重试 [{func.__name__}] 第 {attempt + 1}/{max_retries} 次 "
                            f"(等待 {current_delay:.1f}s): {str(e)[:200]}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(f"重试耗尽 [{func.__name__}]: {e}")

            raise last_exception

        return wrapper
    return decorator


def combined_optimization(
    cache_ttl: int = 0,
    rate_limit: int = 0,
    monitor_slow_ms: float = 0,
    dedup_window: int = 0,
    circuit_failures: int = 0,
    retry_times: int = 0,
):
    """
    组合优化装饰器工厂

    根据配置自动组合多个优化策略

    Args:
        cache_ttl: >0 时启用缓存
        rate_limit: >0 时启用限流
        monitor_slow_ms: >0 时启用监控
        dedup_window: >0 时启用去重
        circuit_failures: >0 时启用熔断
        retry_times: >0 时启用重试

    示例：
        @combined_optimization(
            cache_ttl=300,
            rate_limit=30,
            monitor_slow_ms=500,
            dedup_window=60,
            circuit_failures=5,
            retry_times=3
        )
        def critical_api():
            ...
    """
    def decorator(func: Callable) -> Callable:

        # 按顺序应用装饰器（从外到内）
        decorated = func

        if retry_times > 0:
            decorated = retry(max_retries=retry_times)(decorated)

        if circuit_failures > 0:
            decorated = circuit_breaker(failure_threshold=circuit_failures)(decorated)

        if dedup_window > 0:
            decorated = deduplicated(window_seconds=dedup_window)(decorated)

        if rate_limit > 0:
            decorated = rate_limited(max_requests=rate_limit)(decorated)

        if cache_ttl > 0:
            decorated = cached(ttl=cache_ttl)(decorated)

        if monitor_slow_ms > 0:
            decorated = monitored(slow_threshold_ms=monitor_slow_ms)(decorated)

        return decorated

    return decorator


# 快捷方式导出
__all__ = [
    'OptimizedServiceMixin',
    'cached',
    'rate_limited',
    'monitored',
    'deduplicated',
    'async_task',
    'circuit_breaker',
    'retry',
    'combined_optimization',
]
