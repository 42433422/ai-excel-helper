# -*- coding: utf-8 -*-
"""
熔断器实现

防止级联失败的熔断器模式实现。
"""

import logging
import threading
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_circuit_breakers: dict[str, "CircuitBreaker"] = {}
_breakers_lock = threading.RLock()


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    熔断器实现

    状态机:
    - CLOSED: 正常状态，请求通过，失败计数
    - OPEN: 熔断状态，请求被拒绝，快速失败
    - HALF_OPEN: 半开状态，允许试探性请求
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 10,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
        expected_exceptions: tuple = (Exception,)
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.expected_exceptions = expected_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.RLock()
        self._call_count = 0
        self._success_count = 0
        self._failure_count_total = 0

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
            return self._state

    @property
    def state_value(self) -> int:
        state_map = {
            CircuitState.CLOSED: 0,
            CircuitState.HALF_OPEN: 1,
            CircuitState.OPEN: 2
        }
        return state_map.get(self.state, 0)

    def _should_attempt_reset(self) -> bool:
        if self._last_failure_time is None:
            return True
        return (time.time() - self._last_failure_time) >= self.recovery_timeout

    def _update_metrics(self):
        try:
            from app.utils.metrics import circuit_breaker_failures_total, circuit_breaker_state
            circuit_breaker_state.labels(name=self.name).set(self.state_value)
            if self._failure_count_total > 0:
                circuit_breaker_failures_total.labels(
                    name=self.name,
                    circuit_state=self._state.value
                ).inc(self._failure_count_total)
        except Exception:
            pass

    def _record_success(self):
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                if self._half_open_calls >= self.half_open_max_calls:
                    logger.info(f"Circuit {self.name}: Resetting to CLOSED")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._update_metrics()
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0
            self._success_count += 1

    def _record_failure(self):
        with self._lock:
            self._failure_count += 1
            self._failure_count_total += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit {self.name}: Failure in HALF_OPEN, opening")
                self._state = CircuitState.OPEN
                self._update_metrics()

            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    logger.warning(f"Circuit {self.name}: Failure threshold reached, opening")
                    self._state = CircuitState.OPEN
                    self._update_metrics()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过熔断器调用函数
        """
        self._call_count += 1
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpen(f"Circuit {self.name} is OPEN")

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exceptions as e:
            self._record_failure()
            raise

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper

    def get_stats(self) -> dict:
        """获取熔断器统计信息"""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "call_count": self._call_count,
                "success_count": self._success_count,
                "failure_count": self._failure_count_total,
                "failure_rate": self._failure_count_total / max(self._call_count, 1)
            }


class CircuitBreakerOpen(Exception):
    """熔断器开启异常"""
    pass


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 10,
    recovery_timeout: float = 30.0,
    half_open_max_calls: int = 1
) -> CircuitBreaker:
    """获取或创建命名熔断器"""
    with _breakers_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                half_open_max_calls=half_open_max_calls
            )
        return _circuit_breakers[name]


def circuit_breaker(
    name: str,
    failure_threshold: int = 10,
    recovery_timeout: float = 30.0,
    half_open_max_calls: int = 1
):
    """熔断器装饰器"""
    def decorator(func: Callable) -> Callable:
        cb = get_circuit_breaker(name, failure_threshold, recovery_timeout, half_open_max_calls)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)
        return wrapper
    return decorator


def get_all_circuit_breakers() -> dict[str, CircuitBreaker]:
    """获取所有熔断器实例"""
    with _breakers_lock:
        return dict(_circuit_breakers)
