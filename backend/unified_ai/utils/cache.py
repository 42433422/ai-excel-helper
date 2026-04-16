"""
缓存管理模块
"""

import time
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    timestamp: float
    hits: int = 0


class AICache:
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if time.time() - entry.timestamp > self._ttl_seconds:
                del self._cache[key]
                return None

            entry.hits += 1
            self._cache.move_to_end(key)
            return entry.value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self._max_size:
                    self._cache.popitem(last=False)

            self._cache[key] = CacheEntry(value=value, timestamp=time.time())

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            total_hits = sum(e.hits for e in self._cache.values())
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "total_hits": total_hits,
                "ttl_seconds": self._ttl_seconds
            }


_cache: AICache | None = None


def get_cache() -> AICache:
    global _cache
    if _cache is None:
        from .config import get_config
        config = get_config()
        _cache = AICache(max_size=config.CACHE_SIZE, ttl_seconds=config.CACHE_TTL_SECONDS)
    return _cache
