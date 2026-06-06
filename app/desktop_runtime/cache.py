"""Small in-process cache used when XCAGI runs as a desktop app."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any


class DesktopMemoryCache:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._values: dict[str, tuple[Any, float | None]] = {}

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            item = self._values.get(key)
            if item is None:
                return default
            value, expires_at = item
            if expires_at is not None and expires_at <= time.time():
                self._values.pop(key, None)
                return default
            return value

    def set(self, key: str, value: Any, ttl: int | float | None = None) -> None:
        expires_at = time.time() + ttl if ttl else None
        with self._lock:
            self._values[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._values.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._values.clear()

    def get_or_set(
        self, key: str, factory: Callable[[], Any], ttl: int | float | None = None
    ) -> Any:
        value = self.get(key, default=None)
        if value is not None:
            return value
        value = factory()
        self.set(key, value, ttl=ttl)
        return value


_cache = DesktopMemoryCache()


def get_desktop_cache() -> DesktopMemoryCache:
    return _cache
