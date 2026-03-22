# -*- coding: utf-8 -*-
"""
统一缓存管理器

提供多种缓存策略：
- LRU (最近最少使用)
- LRU with TTL
- 定时过期缓存

支持：
- 命中率统计
- 容量限制
- 线程安全
"""

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0

    @property
    def total(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.hits / self.total

    def __str__(self) -> str:
        return f"hits={self.hits}, misses={self.misses}, hit_rate={self.hit_rate:.2%}"


class LRUCache:
    """
    LRU 缓存实现

    特点：
    - 按访问顺序淘汰
    - 支持容量限制
    - 线程安全
    """

    def __init__(self, max_size: int = 1000, name: str = "lru"):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._lock = threading.RLock()
        self._name = name
        self._stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._stats.hits += 1
                return self._cache[key]
            self._stats.misses += 1
            return None

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self._max_size:
                    self._cache.popitem(last=False)
                    self._stats.evictions += 1
            self._cache[key] = value
            self._stats.sets += 1

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def remove(self, key: str) -> bool:
        """删除指定键"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def has(self, key: str) -> bool:
        """检查键是否存在"""
        with self._lock:
            return key in self._cache

    @property
    def size(self) -> int:
        """当前缓存大小"""
        with self._lock:
            return len(self._cache)

    @property
    def stats(self) -> CacheStats:
        return self._stats

    def __len__(self) -> int:
        return self.size


class LRUTTLCache:
    """
    LRU + TTL 缓存

    特点：
    - 按访问顺序淘汰
    - 支持过期时间
    - 容量限制
    - 线程安全
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300, name: str = "lru_ttl"):
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self._name = name
        self._stats = CacheStats()

    def _is_expired(self, key: str) -> bool:
        """检查键是否过期"""
        if key not in self._timestamps:
            return True
        elapsed = time.time() - self._timestamps[key]
        return elapsed > self._ttl_seconds

    def _evict_expired(self) -> int:
        """淘汰过期键"""
        expired_keys = [
            k for k in list(self._cache.keys())
            if self._is_expired(k)
        ]
        for key in expired_keys:
            del self._cache[key]
            del self._timestamps[key]
            self._stats.evictions += 1
        return len(expired_keys)

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key in self._cache:
                if self._is_expired(key):
                    del self._cache[key]
                    del self._timestamps[key]
                    self._stats.misses += 1
                    return None
                self._cache.move_to_end(key)
                self._stats.hits += 1
                return self._cache[key]
            self._stats.misses += 1
            return None

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        with self._lock:
            self._evict_expired()

            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self._max_size:
                    oldest = next(iter(self._cache))
                    del self._cache[oldest]
                    del self._timestamps[oldest]
                    self._stats.evictions += 1

            self._cache[key] = value
            self._timestamps[key] = time.time()
            self._stats.sets += 1

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

    def remove(self, key: str) -> bool:
        """删除指定键"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._timestamps:
                    del self._timestamps[key]
                return True
            return False

    def has(self, key: str) -> bool:
        """检查键是否存在且未过期"""
        with self._lock:
            if key not in self._cache:
                return False
            if self._is_expired(key):
                del self._cache[key]
                del self._timestamps[key]
                return False
            return True

    @property
    def size(self) -> int:
        """当前缓存大小"""
        with self._lock:
            return len(self._cache)

    @property
    def stats(self) -> CacheStats:
        return self._stats

    def cleanup(self) -> int:
        """手动触发过期清理"""
        with self._lock:
            return self._evict_expired()

    def __len__(self) -> int:
        return self.size


class TimedCache:
    """
    定时过期缓存

    特点：
    - 所有键统一过期时间
    - 定时清理
    - 适合临时性缓存
    """

    def __init__(self, ttl_seconds: int = 60, name: str = "timed"):
        self._cache: Dict[str, tuple] = {}
        self._ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self._name = name
        self._stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp <= self._ttl_seconds:
                    self._stats.hits += 1
                    return value
                else:
                    del self._cache[key]
            self._stats.misses += 1
            return None

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        with self._lock:
            self._cache[key] = (value, time.time())
            self._stats.sets += 1

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    @property
    def stats(self) -> CacheStats:
        return self._stats


def cache_key(*args, **kwargs) -> str:
    """生成缓存键"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_str = "|".join(key_parts)
    return hashlib.md5(key_str.encode()).hexdigest()


def with_cache(cache: LRUCache, key_func: Optional[Callable] = None):
    """
    缓存装饰器

    用法：
    @with_cache(my_cache)
    def expensive_function(arg1, arg2):
        ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = cache_key(func.__name__, *args, **kwargs)

            cached = cache.get(key)
            if cached is not None:
                return cached

            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        return wrapper
    return decorator


class CacheManager:
    """
    缓存管理器

    统一管理所有缓存实例
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._caches: Dict[str, Any] = {}
        self._create_default_caches()

    def _create_default_caches(self):
        """创建默认缓存实例"""
        self._caches["intent_rule"] = LRUCache(max_size=1000, name="intent_rule")
        self._caches["intent_deepseek"] = LRUTTLCache(max_size=500, ttl_seconds=300, name="intent_deepseek")
        self._caches["ai_response"] = LRUTTLCache(max_size=500, ttl_seconds=300, name="ai_response")
        self._caches["purchase_unit"] = LRUCache(max_size=500, name="purchase_unit")
        self._caches["product"] = LRUCache(max_size=500, name="product")

    def get_cache(self, name: str) -> Optional[Any]:
        """获取指定名称的缓存"""
        return self._caches.get(name)

    def register_cache(self, name: str, cache: Any) -> None:
        """注册新的缓存实例"""
        self._caches[name] = cache

    def clear_all(self) -> None:
        """清空所有缓存"""
        for cache in self._caches.values():
            cache.clear()

    def get_stats(self) -> Dict[str, CacheStats]:
        """获取所有缓存的统计信息"""
        return {name: cache.stats for name, cache in self._caches.items()}

    def print_stats(self) -> None:
        """打印缓存统计"""
        logger.info("=== 缓存统计 ===")
        for name, stats in self.get_stats().items():
            logger.info(f"  {name}: {stats}")


_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """获取缓存管理器单例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def get_intent_rule_cache() -> LRUCache:
    """获取意图规则缓存"""
    return get_cache_manager().get_cache("intent_rule")


def get_intent_deepseek_cache() -> LRUTTLCache:
    """获取DeepSeek意图缓存"""
    return get_cache_manager().get_cache("intent_deepseek")


def get_ai_response_cache() -> LRUTTLCache:
    """获取AI响应缓存"""
    return get_cache_manager().get_cache("ai_response")


def get_purchase_unit_cache() -> LRUCache:
    """获取购买单位缓存"""
    return get_cache_manager().get_cache("purchase_unit")


def clear_all_caches() -> None:
    """清空所有缓存"""
    get_cache_manager().clear_all()
