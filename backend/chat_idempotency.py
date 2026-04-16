"""
POST /api/chat 与 /api/chat/stream 的幂等缓存（TASK-1.8）。

行为（与常见支付 API 一致）：
- 客户端提供 Idempotency-Key（或 X-Idempotency-Key）；未提供则不启用。
- 首次成功响应按 TTL 缓存；相同 key + 相同请求指纹 → 返回缓存（带 Idempotency-Replayed: true）。
- 相同 key、不同指纹 → HTTP 409，避免误复用他人/旧客户端的 key。

存储：进程内 dict + TTL（多实例部署需后续接 Redis 等共享存储）。
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any, Mapping

# 与 dict 返回值区分：调用方用 `is IDEMPOTENCY_CONFLICT`
IDEMPOTENCY_CONFLICT: Any = object()
_CachedJson = dict[str, Any]
_CachedStream = bytes

_lock = threading.RLock()
_store: dict[str, dict[str, Any]] = {}

# 与 http_app 路由一一对应，避免拼写漂移
CHAT_JSON_ROUTE = "post:/api/chat"
CHAT_STREAM_ROUTE = "post:/api/chat/stream"


def _ttl_seconds() -> int:
    raw = os.environ.get("FHD_CHAT_IDEMPOTENCY_TTL_SECONDS", "3600").strip()
    try:
        n = int(raw)
    except ValueError:
        return 3600
    return max(60, min(n, 86400 * 7))


def _max_entries() -> int:
    raw = os.environ.get("FHD_CHAT_IDEMPOTENCY_MAX_ENTRIES", "5000").strip()
    try:
        n = int(raw)
    except ValueError:
        return 5000
    return max(16, min(n, 500_000))


def _max_stream_bytes() -> int:
    raw = os.environ.get("FHD_CHAT_IDEMPOTENCY_MAX_STREAM_BYTES", "2000000").strip()
    try:
        n = int(raw)
    except ValueError:
        return 2_000_000
    return max(4096, min(n, 50_000_000))


def normalize_idempotency_key(raw: str | None) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if len(s) > 256:
        s = s[:256]
    return s


def _storage_key(route: str, idempotency_key: str) -> str:
    base = f"{route}\n{idempotency_key}".encode("utf-8")
    return hashlib.sha256(base).hexdigest()


def fingerprint_chat(
    *,
    message: str,
    runtime_context: Mapping[str, Any] | None,
    system_prompt: str | None,
    mode: str | None,
    db_write_token: str | None,
) -> str:
    """与 Planner 入参一致的可序列化指纹（含 tier 注入后的 runtime_context）。"""
    tok = None
    if db_write_token:
        tok = hashlib.sha256(db_write_token.encode("utf-8")).hexdigest()
    payload = {
        "message": message,
        "runtime_context": dict(runtime_context) if isinstance(runtime_context, Mapping) else None,
        "system_prompt": system_prompt,
        "mode": mode,
        "db_write_token": tok,
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _now() -> float:
    return time.monotonic()


def _purge_expired_unlocked() -> None:
    t = _now()
    dead = [k for k, v in _store.items() if float(v.get("expires_mono", 0)) <= t]
    for k in dead:
        _store.pop(k, None)


def _trim_unlocked() -> None:
    cap = _max_entries()
    if len(_store) <= cap:
        return
    # 按过期时间淘汰一部分，避免无限增长
    items = sorted(_store.items(), key=lambda kv: float(kv[1].get("expires_mono", 0)))
    for k, _ in items[: max(1, len(items) - cap + 1)]:
        _store.pop(k, None)


def try_get_json(route: str, idempotency_key: str, fingerprint: str) -> _CachedJson | None | Any:
    with _lock:
        _purge_expired_unlocked()
        sk = _storage_key(route, idempotency_key)
        row = _store.get(sk)
        if not row:
            return None
        if float(row.get("expires_mono", 0)) <= _now():
            _store.pop(sk, None)
            return None
        if row.get("fingerprint") != fingerprint:
            return IDEMPOTENCY_CONFLICT
        if row.get("kind") != "json":
            return None
        payload = row.get("payload")
        return payload if isinstance(payload, dict) else None


def try_get_stream(route: str, idempotency_key: str, fingerprint: str) -> _CachedStream | None | Any:
    with _lock:
        _purge_expired_unlocked()
        sk = _storage_key(route, idempotency_key)
        row = _store.get(sk)
        if not row:
            return None
        if float(row.get("expires_mono", 0)) <= _now():
            _store.pop(sk, None)
            return None
        if row.get("fingerprint") != fingerprint:
            return IDEMPOTENCY_CONFLICT
        if row.get("kind") != "stream":
            return None
        body = row.get("body")
        return body if isinstance(body, (bytes, bytearray)) else None


def store_json(route: str, idempotency_key: str, fingerprint: str, payload: dict[str, Any]) -> None:
    with _lock:
        _purge_expired_unlocked()
        sk = _storage_key(route, idempotency_key)
        _store[sk] = {
            "kind": "json",
            "fingerprint": fingerprint,
            "payload": dict(payload),
            "expires_mono": _now() + float(_ttl_seconds()),
        }
        _trim_unlocked()


def store_stream(route: str, idempotency_key: str, fingerprint: str, body: bytes) -> None:
    if len(body) > _max_stream_bytes():
        return
    with _lock:
        _purge_expired_unlocked()
        sk = _storage_key(route, idempotency_key)
        _store[sk] = {
            "kind": "stream",
            "fingerprint": fingerprint,
            "body": bytes(body),
            "expires_mono": _now() + float(_ttl_seconds()),
        }
        _trim_unlocked()


def clear_for_tests() -> None:
    with _lock:
        _store.clear()
