"""
HTTP 按客户端 IP 的令牌桶限流（TASK-1.10）。

环境变量（未设置或无效则关闭对应桶）：
- ``FHD_RATE_LIMIT_RPM``：非公开 ``/api/*`` 路径的每分钟请求上限。
- ``FHD_RATE_LIMIT_CHAT_RPM``：``POST /api/chat``、``POST /api/chat/stream`` 的每分钟上限；
  若单独设置，仅限制聊天；若与 ``FHD_RATE_LIMIT_RPM`` 同时设置，聊天请求须通过聊天桶，
  其它非公开 API 仅通过通用桶。

令牌桶：容量 = RPM，补充速率 = RPM/60 token/s；超限返回 ``Retry-After``（估算秒数）。
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass

from backend.routers.api_security import is_api_public_path

logger = logging.getLogger(__name__)

_lock = threading.RLock()
_buckets: dict[str, _Bucket] = {}


@dataclass
class _Bucket:
    tokens: float
    last_mono: float


def reset_for_tests() -> None:
    with _lock:
        _buckets.clear()


def _parse_positive_int(name: str) -> int | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        n = int(raw)
    except ValueError:
        logger.warning("invalid %s=%r", name, raw)
        return None
    if n <= 0:
        return None
    return min(n, 60_000)


def _rpm_general() -> int | None:
    return _parse_positive_int("FHD_RATE_LIMIT_RPM")


def _rpm_chat() -> int | None:
    return _parse_positive_int("FHD_RATE_LIMIT_CHAT_RPM")


def client_ip_from_asgi(scope: dict, headers_lower: dict[str, str]) -> str:
    ff = (headers_lower.get("x-forwarded-for") or "").strip()
    if ff:
        return ff.split(",")[0].strip() or "unknown"
    client = scope.get("client")
    if client and client[0]:
        return str(client[0])
    return "unknown"


def _is_chat_post(method: str, path_norm: str) -> bool:
    if method.upper() != "POST":
        return False
    p = path_norm.rstrip("/") or "/"
    return p in ("/api/chat", "/api/chat/stream")


def _should_apply_general_api_limit(path_norm: str) -> bool:
    if not path_norm.startswith("/api"):
        return False
    return not is_api_public_path(path_norm)


def _consume(key: str, rpm: int) -> tuple[bool, int]:
    """
    尝试消耗 1 token。返回 (是否允许, 拒绝时建议的 Retry-After 秒数)。
    """
    rate = float(rpm) / 60.0
    capacity = float(rpm)
    now = time.monotonic()
    with _lock:
        b = _buckets.get(key)
        if b is None:
            _buckets[key] = _Bucket(capacity - 1.0, now)
            if len(_buckets) > 100_000:
                _trim_unlocked()
            return True, 0
        elapsed = now - b.last_mono
        b.tokens = min(capacity, b.tokens + elapsed * rate)
        b.last_mono = now
        if b.tokens >= 1.0:
            b.tokens -= 1.0
            return True, 0
        need = 1.0 - b.tokens
        retry_after = max(1, int(need / rate + 0.999)) if rate > 0 else 60
        return False, retry_after


def _trim_unlocked() -> None:
    """粗略淘汰：清空一半 key（极端滥用时防止内存无限涨）。"""
    keys = list(_buckets.keys())
    for k in keys[: len(keys) // 2]:
        _buckets.pop(k, None)


def check_http_rate_limit(
    *,
    method: str,
    path_norm: str,
    scope: dict,
    headers_lower: dict[str, str],
) -> tuple[bool, int | None]:
    """
    返回 (allowed, retry_after_seconds)。
    ``retry_after_seconds`` 仅在 ``allowed is False`` 时有意义。
    """
    g = _rpm_general()
    c = _rpm_chat()
    if g is None and c is None:
        return True, None

    if method.upper() in ("OPTIONS", "HEAD"):
        return True, None

    ip = client_ip_from_asgi(scope, headers_lower)
    chat_post = _is_chat_post(method, path_norm)
    private_api = _should_apply_general_api_limit(path_norm)

    if chat_post and c is not None:
        ok, ra = _consume(f"{ip}|chat", c)
        if not ok:
            return False, ra

    if g is not None and private_api:
        ok, ra = _consume(f"{ip}|api", g)
        if not ok:
            return False, ra

    return True, None
