"""
动态限流器（Rate Limiter）

支持动态调整的限流器，可基于领域、事件类型等维度进行限流
"""

import logging
import time
from dataclasses import dataclass
from threading import RLock

from app.neuro_bus.events.base import EventPriority, NeuroEvent

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """限流配置"""

    requests_per_second: float = 10.0
    burst_size: int = 20
    window_size: float = 1.0  # 秒
    dynamic_adjust: bool = True


class SlidingWindowCounter:
    """滑动窗口计数器"""

    def __init__(self, window_size: float = 1.0):
        self._window_size = window_size
        self._timestamps: list = []
        self._lock = RLock()

    def add(self) -> int:
        """添加一个请求，返回当前窗口内计数"""
        now = time.time()

        with self._lock:
            # 清理过期
            cutoff = now - self._window_size
            self._timestamps = [t for t in self._timestamps if t > cutoff]

            # 添加新请求
            self._timestamps.append(now)

            return len(self._timestamps)

    def count(self) -> int:
        """获取当前窗口计数"""
        now = time.time()

        with self._lock:
            cutoff = now - self._window_size
            self._timestamps = [t for t in self._timestamps if t > cutoff]
            return len(self._timestamps)

    def reset(self):
        """重置计数器"""
        with self._lock:
            self._timestamps.clear()


class DynamicRateLimiter:
    """
    动态限流器

    支持：
    - 多维度限流（全局、领域、事件类型）
    - 动态调整限流策略
    - 优先级白名单
    """

    def __init__(
        self,
        default_config: RateLimitConfig | None = None,
        priority_whitelist: list | None = None,
    ):
        self._default_config = default_config or RateLimitConfig()
        self._priority_whitelist = priority_whitelist or [
            EventPriority.CRITICAL,
            EventPriority.HIGH,
        ]

        # 各维度计数器
        self._global_counter = SlidingWindowCounter()
        self._domain_counters: dict[str, SlidingWindowCounter] = {}
        self._event_counters: dict[str, SlidingWindowCounter] = {}

        # 各维度配置
        self._domain_configs: dict[str, RateLimitConfig] = {}
        self._event_configs: dict[str, RateLimitConfig] = {}

        self._lock = RLock()

        # 统计
        self._allowed_count = 0
        self._rejected_count = 0

        logger.info("DynamicRateLimiter initialized")

    def set_domain_limit(self, domain: str, config: RateLimitConfig):
        """设置领域限流配置"""
        with self._lock:
            self._domain_configs[domain] = config

    def set_event_limit(self, event_type: str, config: RateLimitConfig):
        """设置事件类型限流配置"""
        with self._lock:
            self._event_configs[event_type] = config

    def allow(self, event: NeuroEvent) -> bool:
        """
        检查是否允许处理该事件

        Returns:
            True: 允许通过
            False: 被限流
        """
        # 高优先级白名单
        if event.priority in self._priority_whitelist:
            return True

        with self._lock:
            # 1. 检查全局限流
            global_config = self._default_config
            global_count = self._global_counter.add()

            if global_count > global_config.burst_size:
                self._rejected_count += 1
                logger.warning(
                    f"Global rate limit exceeded: {global_count}/{global_config.burst_size}"
                )
                return False

            # 2. 检查领域限流
            domain = event.metadata.domain
            if domain:
                if domain not in self._domain_counters:
                    self._domain_counters[domain] = SlidingWindowCounter()

                domain_config = self._domain_configs.get(domain, global_config)
                domain_count = self._domain_counters[domain].add()

                if domain_count > domain_config.burst_size:
                    self._rejected_count += 1
                    logger.warning(
                        f"Domain rate limit exceeded [{domain}]: {domain_count}/{domain_config.burst_size}"
                    )
                    return False

            # 3. 检查事件类型限流
            event_type = event.event_type
            if event_type not in self._event_counters:
                self._event_counters[event_type] = SlidingWindowCounter()

            event_config = self._event_configs.get(event_type, global_config)
            event_count = self._event_counters[event_type].add()

            if event_count > event_config.burst_size:
                self._rejected_count += 1
                logger.warning(
                    f"Event type rate limit exceeded [{event_type}]: {event_count}/{event_config.burst_size}"
                )
                return False

            self._allowed_count += 1
            return True

    def get_stats(self) -> dict:
        """获取统计"""
        with self._lock:
            return {
                "allowed": self._allowed_count,
                "rejected": self._rejected_count,
                "global_count": self._global_counter.count(),
                "domains": list(self._domain_counters.keys()),
                "event_types": list(self._event_counters.keys()),
            }


class NeuroRateLimiter:
    """
    NeuroBus 专用限流器

    提供领域感知的限流策略
    """

    # 各领域的默认限流配置
    DOMAIN_LIMITS = {
        "intent": RateLimitConfig(
            requests_per_second=50.0,  # 意图识别高频
            burst_size=100,
        ),
        "payment": RateLimitConfig(
            requests_per_second=5.0,  # 支付保守
            burst_size=10,
        ),
        "wechat": RateLimitConfig(
            requests_per_second=30.0,  # 微信中等
            burst_size=50,
        ),
        "default": RateLimitConfig(
            requests_per_second=20.0,
            burst_size=40,
        ),
    }

    def __init__(self):
        self._limiter = DynamicRateLimiter(default_config=self.DOMAIN_LIMITS["default"])

        # 设置各领域限流
        for domain, config in self.DOMAIN_LIMITS.items():
            if domain != "default":
                self._limiter.set_domain_limit(domain, config)

    def check_rate(self, event: NeuroEvent) -> bool:
        """检查事件是否通过限流"""
        return self._limiter.allow(event)

    def get_stats(self) -> dict:
        """获取统计"""
        return self._limiter.get_stats()
