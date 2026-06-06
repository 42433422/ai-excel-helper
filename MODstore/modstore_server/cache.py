"""Small JSON cache adapter used by legacy API modules.

The refactor keeps this module as an infrastructure compatibility layer while
new code moves toward explicit ports under ``modstore_server.infrastructure``.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any


_memory_cache: dict[str, tuple[float, Any]] = {}


def _redis_client():
    url = (os.environ.get("REDIS_URL") or "").strip()
    if not url:
        return None
    try:
        import redis

        return redis.Redis.from_url(url, decode_responses=True)
    except Exception:
        return None


def get_json(key: str) -> Any | None:
    client = _redis_client()
    if client is not None:
        try:
            raw = client.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            return None

    ent = _memory_cache.get(key)
    if not ent:
        return None
    expires_at, value = ent
    if expires_at and expires_at < time.time():
        _memory_cache.pop(key, None)
        return None
    return value


def set_json(key: str, value: Any, ttl_seconds: int = 300) -> None:
    client = _redis_client()
    if client is not None:
        try:
            client.setex(key, max(1, int(ttl_seconds)), json.dumps(value, ensure_ascii=False, default=str))
            return
        except Exception:
            pass

    expires_at = time.time() + max(1, int(ttl_seconds)) if ttl_seconds else 0
    _memory_cache[key] = (expires_at, value)


def delete(key: str) -> None:
    client = _redis_client()
    if client is not None:
        try:
            client.delete(key)
        except Exception:
            pass
    _memory_cache.pop(key, None)
