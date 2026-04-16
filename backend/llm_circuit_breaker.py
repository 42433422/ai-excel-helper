"""
Planner 大模型上游熔断（TASK-1.11）。

开启：``FHD_LLM_CIRCUIT_ENABLED=1``（或 true/yes/on）。
连续 ``FHD_LLM_CB_FAILURE_THRESHOLD`` 次（默认 5）判定为上游故障后，在 ``FHD_LLM_CB_OPEN_SECONDS`` 秒（默认 45）
内拒绝新的 LLM 请求，抛出 ``RuntimeError``（由 http 层映射为 503）。单次成功调用会清零失败计数。

仅统计连接/超时/5xx 类错误；鉴权、限流等不触发熔断。
"""

from __future__ import annotations

import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

_lock = threading.RLock()
_failures = 0
_open_until_mono: float = 0.0


def reset_for_tests() -> None:
    global _failures, _open_until_mono
    with _lock:
        _failures = 0
        _open_until_mono = 0.0


def _enabled() -> bool:
    return os.environ.get("FHD_LLM_CIRCUIT_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")


def _failure_threshold() -> int:
    raw = os.environ.get("FHD_LLM_CB_FAILURE_THRESHOLD", "5").strip()
    try:
        n = int(raw)
    except ValueError:
        return 5
    return max(2, min(n, 100))


def _open_seconds() -> float:
    raw = os.environ.get("FHD_LLM_CB_OPEN_SECONDS", "45").strip()
    try:
        s = float(raw)
    except ValueError:
        return 45.0
    return max(5.0, min(s, 3600.0))


def is_llm_upstream_failure(exc: BaseException) -> bool:
    """是否视为「上游不可用」并计入熔断失败次数。"""
    import httpx
    from openai import (
        APIConnectionError,
        APIError,
        APITimeoutError,
        AuthenticationError,
        RateLimitError,
    )

    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return True
    if isinstance(exc, (AuthenticationError, RateLimitError)):
        return False
    if isinstance(exc, APIError):
        st = getattr(exc, "status_code", None)
        if st is None:
            return True
        try:
            return int(st) >= 500
        except (TypeError, ValueError):
            return True
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException, httpx.ReadError, httpx.RemoteProtocolError)):
        return True
    return False


def before_llm_call() -> None:
    """在发起单次 LLM HTTP 请求前调用；熔断开路时抛出 RuntimeError。"""
    if not _enabled():
        return
    now = time.monotonic()
    with _lock:
        global _open_until_mono
        if now < _open_until_mono:
            wait = int(_open_until_mono - now) + 1
            raise RuntimeError(
                f"大模型服务已熔断，请约 {wait} 秒后再试（FHD_LLM_CIRCUIT_ENABLED）"
            )
        _open_until_mono = 0.0


def record_llm_success() -> None:
    if not _enabled():
        return
    global _failures
    with _lock:
        _failures = 0


def record_llm_failure() -> None:
    if not _enabled():
        return
    global _failures, _open_until_mono
    with _lock:
        _failures += 1
        if _failures >= _failure_threshold():
            _open_until_mono = time.monotonic() + _open_seconds()
            logger.warning(
                "llm circuit opened for %.0fs after %s consecutive upstream failures",
                _open_seconds(),
                _failure_threshold(),
            )
            _failures = 0
