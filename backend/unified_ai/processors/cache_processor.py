"""
缓存处理器 - <10ms 缓存查询
"""

import hashlib
import time
import logging
from dataclasses import dataclass
from typing import Any

from ..utils.cache import get_cache
from ..utils.metrics import get_metrics

logger = logging.getLogger(__name__)


@dataclass
class CacheResult:
    hit: bool
    data: Any = None
    processing_time_ms: float = 0.0
    cache_key: str = ""


class CacheProcessor:
    def __init__(self):
        self._cache = get_cache()
        self._enabled = True

    def _make_key(self, user_input: str, intent: str | None = None) -> str:
        combined = f"{intent or 'default'}:{user_input}"
        return hashlib.md5(combined.encode()).hexdigest()

    def get(self, user_input: str, intent: str | None = None) -> CacheResult:
        if not self._enabled:
            return CacheResult(hit=False)

        start = time.perf_counter()
        key = self._make_key(user_input, intent)

        try:
            data = self._cache.get(key)
            elapsed_ms = (time.perf_counter() - start) * 1000

            if data is not None:
                get_metrics().histogram("cache_processor.duration_ms", elapsed_ms)
                get_metrics().inc("cache_processor.hit")
                logger.debug(f"[CacheProcessor] 命中缓存: {key[:8]}... ({elapsed_ms:.2f}ms)")

                return CacheResult(
                    hit=True,
                    data=data,
                    processing_time_ms=elapsed_ms,
                    cache_key=key
                )

            return CacheResult(hit=False, processing_time_ms=elapsed_ms, cache_key=key)

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.warning(f"[CacheProcessor] 获取缓存异常: {e}")
            return CacheResult(hit=False, processing_time_ms=elapsed_ms)

    def set(self, user_input: str, data: Any, intent: str | None = None) -> None:
        if not self._enabled:
            return

        key = self._make_key(user_input, intent)
        self._cache.set(key, data)
        logger.debug(f"[CacheProcessor] 写入缓存: {key[:8]}...")

    def invalidate(self, user_input: str, intent: str | None = None) -> None:
        key = self._make_key(user_input, intent)
        self._cache.delete(key)
        logger.debug(f"[CacheProcessor] 失效缓存: {key[:8]}...")

    def clear(self) -> None:
        self._cache.clear()
        logger.info("[CacheProcessor] 缓存已清空")

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def get_stats(self) -> dict[str, Any]:
        return self._cache.get_stats()
