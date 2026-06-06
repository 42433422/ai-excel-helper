"""
熔断保护器（Circuit Breaker）

防止级联故障，当错误率超过阈值时自动熔断
支持 CLOSED/OPEN/HALF_OPEN 三种状态
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""

    CLOSED = "closed"  # 正常，请求通过
    OPEN = "open"  # 熔断，拒绝请求
    HALF_OPEN = "half_open"  # 半开，试探性允许


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""

    failure_threshold: int = 5  # 触发熔断的失败次数
    success_threshold: int = 3  # 半开状态恢复所需成功次数
    timeout_seconds: float = 60.0  # 熔断后尝试恢复的时间
    half_open_max_calls: int = 3  # 半开状态最大试探请求数


class CircuitBreaker:
    """
    熔断器

    基于失败率和成功率的自动熔断机制
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ):
        self._name = name
        self._config = config or CircuitBreakerConfig()

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._half_open_calls = 0

        self._lock = RLock()

        logger.info(f"CircuitBreaker [{name}] initialized")

    @property
    def state(self) -> CircuitState:
        """当前状态"""
        with self._lock:
            return self._state

    def can_execute(self) -> bool:
        """
        检查是否可以执行

        Returns:
            True: 允许执行
            False: 熔断中，拒绝执行
        """
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # 检查是否到达恢复时间
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed > self._config.timeout_seconds:
                        logger.info(f"Circuit [{self._name}] transitioning to HALF_OPEN")
                        self._state = CircuitState.HALF_OPEN
                        self._half_open_calls = 0
                        return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                # 半开状态限制试探请求数
                if self._half_open_calls < self._config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

            return True

    def record_success(self):
        """记录成功"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1

                if self._success_count >= self._config.success_threshold:
                    logger.info(f"Circuit [{self._name}] transitioning to CLOSED")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._half_open_calls = 0

            elif self._state == CircuitState.CLOSED:
                # 重置失败计数
                if self._failure_count > 0:
                    self._failure_count = 0

    def record_failure(self):
        """记录失败"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # 半开状态再次失败，重新熔断
                logger.warning(f"Circuit [{self._name}] failed in HALF_OPEN, returning to OPEN")
                self._state = CircuitState.OPEN
                self._half_open_calls = 0

            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self._config.failure_threshold:
                    logger.warning(
                        f"Circuit [{self._name}] OPEN due to {self._failure_count} failures"
                    )
                    self._state = CircuitState.OPEN

    def execute(self, fn: Callable, *args, **kwargs) -> Any:
        """
        执行函数，自动处理熔断逻辑

        Args:
            fn: 要执行的函数
            *args, **kwargs: 函数参数

        Returns:
            函数返回值

        Raises:
            CircuitBreakerOpen: 熔断器打开时抛出
        """
        if not self.can_execute():
            raise CircuitBreakerOpen(f"Circuit [{self._name}] is OPEN")

        try:
            result = fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    async def execute_async(self, fn: Callable, *args, **kwargs) -> Any:
        """异步执行"""
        if not self.can_execute():
            raise CircuitBreakerOpen(f"Circuit [{self._name}] is OPEN")

        try:
            result = await fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    def get_stats(self) -> dict:
        """获取统计"""
        with self._lock:
            return {
                "name": self._name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "half_open_calls": self._half_open_calls,
                "last_failure": self._last_failure_time,
            }


class CircuitBreakerOpen(Exception):
    """熔断器打开异常"""

    pass


class NeuroCircuitBreakerManager:
    """
    NeuroBus 熔断管理器

    管理多个熔断器，按领域和事件类型划分
    """

    # 各领域的熔断配置
    DOMAIN_CONFIGS = {
        "payment": CircuitBreakerConfig(
            failure_threshold=3,  # 支付敏感，低阈值
            timeout_seconds=30.0,  # 快速恢复尝试
        ),
        "wechat": CircuitBreakerConfig(
            failure_threshold=5,
            timeout_seconds=60.0,
        ),
        "intent": CircuitBreakerConfig(
            failure_threshold=10,  # 意图识别容忍度高
            timeout_seconds=30.0,
        ),
        "default": CircuitBreakerConfig(),
    }

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = RLock()

    def get_breaker(self, domain: str, event_type: str | None = None) -> CircuitBreaker:
        """获取或创建熔断器"""
        key = f"{domain}:{event_type}" if event_type else domain

        with self._lock:
            if key not in self._breakers:
                config = self.DOMAIN_CONFIGS.get(domain, self.DOMAIN_CONFIGS["default"])
                self._breakers[key] = CircuitBreaker(key, config)

            return self._breakers[key]

    def check(self, domain: str, event_type: str | None = None) -> bool:
        """检查是否可以通过"""
        breaker = self.get_breaker(domain, event_type)
        return breaker.can_execute()

    def record_success(self, domain: str, event_type: str | None = None):
        """记录成功"""
        breaker = self.get_breaker(domain, event_type)
        breaker.record_success()

    def record_failure(self, domain: str, event_type: str | None = None):
        """记录失败"""
        breaker = self.get_breaker(domain, event_type)
        breaker.record_failure()

    def get_all_stats(self) -> dict:
        """获取所有熔断器统计"""
        with self._lock:
            return {key: breaker.get_stats() for key, breaker in self._breakers.items()}


_neuro_circuit_manager: NeuroCircuitBreakerManager | None = None


def get_circuit_breaker() -> NeuroCircuitBreakerManager:
    """NeuroBus 初始化器使用的单例。"""
    global _neuro_circuit_manager
    if _neuro_circuit_manager is None:
        _neuro_circuit_manager = NeuroCircuitBreakerManager()
    return _neuro_circuit_manager
