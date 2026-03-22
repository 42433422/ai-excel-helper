# -*- coding: utf-8 -*-
"""
重试机制模块

提供指数退避重试装饰器。
"""

import logging
from functools import wraps

from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


def retry_on_exception(
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 30.0,
    multiplier: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    重试装饰器

    Args:
        max_attempts: 最大重试次数
        initial_wait: 初始等待时间（秒）
        max_wait: 最大等待时间（秒）
        multiplier: 指数乘数
        exceptions: 需要重试的异常类型元组

    Returns:
        tenacity retry 装饰器
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=multiplier,
            min=initial_wait,
            max=max_wait
        ),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True
    )


def retry_ai_service(
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 30.0
):
    """
    AI 服务重试装饰器

    专门用于 AI 服务调用（如 DeepSeek、OCR 等），具有较长的超时时间。
    """
    return retry_on_exception(
        max_attempts=max_attempts,
        initial_wait=initial_wait,
        max_wait=max_wait,
        multiplier=2.0,
        exceptions=(
            ConnectionError,
            TimeoutError,
            OSError,
        )
    )


def retry_network_operation(
    max_attempts: int = 3,
    initial_wait: float = 0.5,
    max_wait: float = 10.0
):
    """
    网络操作重试装饰器

    用于网络相关的操作，如 HTTP 请求等。
    """
    return retry_on_exception(
        max_attempts=max_attempts,
        initial_wait=initial_wait,
        max_wait=max_wait,
        multiplier=2.0,
        exceptions=(
            ConnectionError,
            TimeoutError,
        )
    )