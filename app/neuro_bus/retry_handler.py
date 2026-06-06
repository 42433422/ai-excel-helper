"""
错误反馈与重试处理器

智能退避策略：
- 指数退避
- 抖动（Jitter）
- 最大重试次数
- 可重试异常类型判断
"""

import asyncio
import logging
import random
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.1,  # 初始延迟（秒）
        max_delay: float = 60.0,  # 最大延迟（秒）
        exponential_base: float = 2.0,  # 指数基数
        jitter: bool = True,  # 启用抖动
        jitter_max: float = 0.1,  # 最大抖动（秒）
        retryable_exceptions: tuple[type[Exception], ...] | None = None,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.jitter_max = jitter_max
        self.retryable_exceptions = retryable_exceptions or (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        )


class RetryContext:
    """重试上下文"""

    def __init__(self, config: RetryConfig, operation_name: str):
        self._config = config
        self._operation_name = operation_name
        self._attempt = 0
        self._last_error: Exception | None = None
        self._success = False
        self._total_delay = 0.0

    def should_retry(self, error: Exception) -> bool:
        """判断是否应该重试"""
        # 检查重试次数
        if self._attempt >= self._config.max_retries:
            return False

        # 检查异常类型
        if not isinstance(error, self._config.retryable_exceptions):
            return False

        self._attempt += 1
        self._last_error = error
        return True

    def get_delay(self) -> float:
        """计算下次重试延迟"""
        # 指数退避
        delay = self._config.base_delay * (self._config.exponential_base ** (self._attempt - 1))

        # 上限控制
        delay = min(delay, self._config.max_delay)

        # 抖动
        if self._config.jitter:
            jitter = random.uniform(0, self._config.jitter_max)
            delay += jitter

        self._total_delay += delay
        return delay

    def record_success(self):
        """记录成功"""
        self._success = True

    def get_report(self) -> dict:
        """获取重试报告"""
        return {
            "operation": self._operation_name,
            "attempts": self._attempt + (1 if self._success else 0),
            "max_retries": self._config.max_retries,
            "success": self._success,
            "total_delay_sec": self._total_delay,
            "last_error": str(self._last_error) if self._last_error else None,
        }


class RetryHandler:
    """
    重试处理器

    提供同步和异步的重试执行
    """

    def __init__(self, config: RetryConfig | None = None):
        self._config = config or RetryConfig()

    async def execute(
        self,
        operation: Callable,
        *args,
        operation_name: str | None = None,
        on_retry: Callable[[Exception, int], None] | None = None,
        **kwargs,
    ) -> Any:
        """
        异步执行，带重试
        """
        context = RetryContext(self._config, operation_name or operation.__name__)

        while True:
            try:
                result = await operation(*args, **kwargs)
                context.record_success()

                if context._attempt > 0:
                    report = context.get_report()
                    logger.info(
                        f"Retry succeeded after {report['attempts']} attempts: {operation_name}"
                    )

                return result

            except Exception as e:
                if not context.should_retry(e):
                    # 不可重试或次数耗尽
                    report = context.get_report()
                    logger.error(
                        f"Retry exhausted for {operation_name}: "
                        f"{report['attempts']} attempts, last error: {e}"
                    )
                    raise

                # 计算延迟
                delay = context.get_delay()

                logger.warning(
                    f"Retry {context._attempt}/{self._config.max_retries} "
                    f"for {operation_name} after {delay:.2f}s delay, error: {e}"
                )

                if on_retry:
                    on_retry(e, context._attempt)

                await asyncio.sleep(delay)

    def execute_sync(
        self,
        operation: Callable,
        *args,
        operation_name: str | None = None,
        on_retry: Callable[[Exception, int], None] | None = None,
        **kwargs,
    ) -> Any:
        """
        同步执行，带重试
        """
        context = RetryContext(self._config, operation_name or operation.__name__)

        while True:
            try:
                result = operation(*args, **kwargs)
                context.record_success()
                return result

            except Exception as e:
                if not context.should_retry(e):
                    raise

                delay = context.get_delay()

                logger.warning(
                    f"Retry {context._attempt}/{self._config.max_retries} "
                    f"for {operation_name} after {delay:.2f}s delay"
                )

                if on_retry:
                    on_retry(e, context._attempt)

                time.sleep(delay)


class NeuroRetryHandler:
    """
    NeuroBus 专用重试处理器

    为不同领域提供定制化重试策略
    """

    DOMAIN_CONFIGS = {
        "payment": RetryConfig(
            max_retries=2,  # 支付重试少，快速失败
            base_delay=0.5,
            retryable_exceptions=(ConnectionError, TimeoutError),
        ),
        "wechat": RetryConfig(
            max_retries=3,
            base_delay=0.5,
        ),
        "ai_service": RetryConfig(
            max_retries=5,  # AI 服务重试多
            base_delay=1.0,
            max_delay=30.0,
        ),
        "default": RetryConfig(),
    }

    def __init__(self):
        self._handlers: dict = {}

    def get_handler(self, domain: str) -> RetryHandler:
        """获取领域的重试处理器"""
        if domain not in self._handlers:
            config = self.DOMAIN_CONFIGS.get(domain, self.DOMAIN_CONFIGS["default"])
            self._handlers[domain] = RetryHandler(config)
        return self._handlers[domain]

    async def execute_for_event(self, domain: str, operation: Callable, *args, **kwargs) -> Any:
        """为事件执行操作，带领域特定的重试"""
        handler = self.get_handler(domain)
        return await handler.execute(operation, *args, **kwargs)


# 装饰器


def with_retry(
    max_retries: int = 3,
    base_delay: float = 0.1,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
):
    """
    重试装饰器

    用法:
        @with_retry(max_retries=5, base_delay=1.0)
        async def fetch_data():
            pass
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        retryable_exceptions=retryable_exceptions,
    )
    handler = RetryHandler(config)

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await handler.execute(func, *args, **kwargs)

        return wrapper

    return decorator


_neuro_retry_handler: NeuroRetryHandler | None = None


def get_retry_handler() -> NeuroRetryHandler:
    """NeuroBus 初始化器使用的单例（与 ``NeuroRetryHandler`` 一致）。"""
    global _neuro_retry_handler
    if _neuro_retry_handler is None:
        _neuro_retry_handler = NeuroRetryHandler()
    return _neuro_retry_handler
