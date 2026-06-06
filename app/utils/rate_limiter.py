"""
限流和熔断工具模块

提供基于 Redis（可选）或内存的请求限流和熔断机制。
"""

from __future__ import annotations

import logging
import os
import time
from collections import OrderedDict
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

_redis_client: Any | None = None
_redis_init_attempted = False


def _get_redis_client():
    global _redis_client, _redis_init_attempted
    if _redis_init_attempted:
        return _redis_client
    _redis_init_attempted = True
    url = (
        os.environ.get("CACHE_REDIS_URL")
        or os.environ.get("REDIS_URL")
        or os.environ.get("XCAGI_REDIS_URL")
        or ""
    ).strip()
    if not url:
        return None
    try:
        import redis

        _redis_client = redis.from_url(url, decode_responses=True)
        _redis_client.ping()
        logger.info("Rate limiter using Redis backend")
    except Exception as exc:
        logger.warning("Rate limiter Redis unavailable, using in-memory: %s", exc)
        _redis_client = None
    return _redis_client


class _InMemoryRateLimiter:
    """内存限流器（无 Redis 时使用）"""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: OrderedDict[str, list] = OrderedDict()
        self._lock = Lock()

    def _clean_old(self, key: str) -> None:
        now = time.time()
        cutoff = now - self._window_seconds
        self._requests[key] = [t for t in self._requests.get(key, []) if t > cutoff]
        if not self._requests[key]:
            del self._requests[key]

    def is_allowed(self, key: str) -> bool:
        with self._lock:
            self._clean_old(key)
            now = time.time()
            if key not in self._requests:
                self._requests[key] = []
            if len(self._requests[key]) < self._max_requests:
                self._requests[key].append(now)
                return True
            return False

    def get_remaining(self, key: str) -> int:
        with self._lock:
            self._clean_old(key)
            return max(0, self._max_requests - len(self._requests.get(key, [])))

    def get_reset_time(self, key: str) -> float | None:
        with self._lock:
            self._clean_old(key)
            if key in self._requests and self._requests[key]:
                return self._requests[key][0] + self._window_seconds
            return None


class _RedisRateLimiter:
    """基于 Redis 的固定窗口计数（多副本共享）。"""

    def __init__(self, max_requests: int, window_seconds: int):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._redis = _get_redis_client()

    def _window_key(self, key: str) -> str:
        bucket = int(time.time()) // self._window_seconds
        return f"ratelimit:{key}:{bucket}"

    def is_allowed(self, key: str) -> bool:
        if self._redis is None:
            return True
        rk = self._window_key(key)
        pipe = self._redis.pipeline()
        pipe.incr(rk)
        pipe.expire(rk, self._window_seconds + 1)
        count, _ = pipe.execute()
        return int(count) <= self._max_requests

    def get_remaining(self, key: str) -> int:
        if self._redis is None:
            return self._max_requests
        try:
            count = int(self._redis.get(self._window_key(key)) or 0)
        except Exception:
            return 0
        return max(0, self._max_requests - count)

    def get_reset_time(self, key: str) -> float | None:
        now = time.time()
        bucket = int(now) // self._window_seconds
        return (bucket + 1) * self._window_seconds


class _CircuitBreaker:
    """熔断器实现"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._expected_exception = expected_exception
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._state = "closed"
        self._lock = Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == "open":
                if (
                    self._last_failure_time
                    and time.time() - self._last_failure_time > self._recovery_timeout
                ):
                    self._state = "half-open"
                    logger.info("Circuit breaker transitioning to half-open")
            return self._state

    def call(self, func, *args, **kwargs):
        if self.state == "open":
            raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            with self._lock:
                if self._state == "half-open":
                    self._state = "closed"
                    self._failure_count = 0
                    logger.info("Circuit breaker closed after successful call")
            return result
        except self._expected_exception as e:
            with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.time()
                if self._failure_count >= self._failure_threshold:
                    self._state = "open"
                    logger.warning(f"Circuit breaker opened after {self._failure_count} failures")
            raise e

    def reset(self) -> None:
        with self._lock:
            self._state = "closed"
            self._failure_count = 0
            self._last_failure_time = None


_rate_limiters: dict[str, _InMemoryRateLimiter | _RedisRateLimiter] = {}
_circuit_breakers: dict[str, _CircuitBreaker] = {}
_limiter_lock = Lock()


def get_rate_limiter(
    name: str, max_requests: int = 100, window_seconds: int = 60
) -> _InMemoryRateLimiter | _RedisRateLimiter:
    with _limiter_lock:
        if name not in _rate_limiters:
            if _get_redis_client() is not None:
                _rate_limiters[name] = _RedisRateLimiter(max_requests, window_seconds)
            else:
                _rate_limiters[name] = _InMemoryRateLimiter(max_requests, window_seconds)
        return _rate_limiters[name]


def check_rate_limit(
    user_id: str, endpoint: str, max_requests: int = 100, window_seconds: int = 60
) -> dict[str, Any]:
    key = f"{endpoint}:{user_id}"
    limiter = get_rate_limiter(endpoint, max_requests, window_seconds)

    if limiter.is_allowed(key):
        return {
            "allowed": True,
            "remaining": limiter.get_remaining(key),
            "reset_time": limiter.get_reset_time(key),
            "retry_after": None,
        }
    reset_time = limiter.get_reset_time(key)
    retry_after = int(reset_time - time.time()) if reset_time else window_seconds
    return {
        "allowed": False,
        "remaining": 0,
        "reset_time": reset_time,
        "retry_after": retry_after,
    }


def get_circuit_breaker(
    name: str, failure_threshold: int = 5, recovery_timeout: int = 60
) -> _CircuitBreaker:
    with _limiter_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = _CircuitBreaker(failure_threshold, recovery_timeout)
        return _circuit_breakers[name]


def reset_circuit_breaker(name: str) -> None:
    with _limiter_lock:
        if name in _circuit_breakers:
            _circuit_breakers[name].reset()
