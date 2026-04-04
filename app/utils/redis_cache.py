# -*- coding: utf-8 -*-
"""
Redis 分布式缓存层

提供高性能的 Redis 缓存实现，支持：
- 多级缓存策略（L1 本地 + L2 Redis）
- 缓存穿透/击穿/雪崩防护
- 自动序列化/反序列化
- 命中率统计和监控
- 批量操作支持
"""

import functools
import hashlib
import json
import logging
import os
import pickle
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

REDIS_CACHE_PREFIX = os.environ.get("XCAGI_REDIS_CACHE_PREFIX", "xcagi:")
DEFAULT_REDIS_TTL = int(os.environ.get("XCAGI_DEFAULT_CACHE_TTL", "300"))
CACHE_NULL_TTL = int(os.environ.get("XCAGI_CACHE_NULL_TTL", "60"))


class RedisCache:
    """
    Redis 分布式缓存封装

    特性：
    - 支持 string/hash/list/set 等数据结构
    - 自动 TTL 管理
    - 空值防护（防止缓存穿透）
    - 分布式锁支持
    - Pipeline 批量操作
    """

    def __init__(self, redis_client=None, prefix: str = REDIS_CACHE_PREFIX):
        self._redis = redis_client
        self._prefix = prefix
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }
        self._local_cache: Dict[str, Tuple[Any, float]] = {}
        self._local_cache_size = int(os.environ.get("XCAGI_LOCAL_CACHE_SIZE", "1000"))
        self._local_cache_ttl = int(os.environ.get("XCAGI_LOCAL_CACHE_TTL", "10"))

    @property
    def is_available(self) -> bool:
        """检查 Redis 是否可用"""
        if self._redis is None:
            return False
        try:
            return self._redis.ping()
        except Exception:
            return False

    def _make_key(self, key: str) -> str:
        """生成带前缀的键"""
        return f"{self._prefix}{key}"

    def _serialize(self, value: Any) -> str:
        """序列化值"""
        try:
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False, default=str)
            return pickle.dumps(value).hex() if not isinstance(value, str) else value
        except Exception as e:
            logger.error(f"序列化失败: {e}")
            return str(value)

    def _deserialize(self, data: str, is_json: bool = True) -> Any:
        """反序列化值"""
        if data is None:
            return None
        try:
            if is_json:
                return json.loads(data)
            return pickle.fromhex(data)
        except (json.JSONDecodeError, pickle.UnpicklingError, ValueError, Exception):
            return data

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        获取缓存值（L1 本地缓存优先）

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            缓存的值或默认值
        """
        full_key = self._make_key(key)

        # L1: 检查本地缓存
        local_hit = self._get_local(full_key)
        if local_hit is not None:
            self._stats["hits"] += 1
            return local_hit

        # L2: 查询 Redis
        if not self.is_available:
            self._stats["misses"] += 1
            return default

        try:
            data = self._redis.get(full_key)
            if data is None:
                self._stats["misses"] += 1
                return default

            value = self._deserialize(data.decode('utf-8') if isinstance(data, bytes) else data)

            # 写入本地缓存
            self._set_local(full_key, value)

            self._stats["hits"] += 1
            return value

        except Exception as e:
            logger.error(f"Redis GET 失败 [{key}]: {e}")
            self._stats["errors"] += 1
            return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: int = DEFAULT_REDIS_TTL,
        nx: bool = False,
        prevent_null: bool = True
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            nx: 仅当键不存在时设置
            prevent_null: 是否防止空值缓存（防止缓存穿透）

        Returns:
            是否成功
        """
        full_key = self._make_key(key)

        # 防止空值缓存
        if prevent_null and value is None:
            return self._set_null_key(full_key)

        if not self.is_available:
            self._set_local(full_key, value)
            return True

        try:
            serialized = self._serialize(value)
            result = self._redis.set(full_key, serialized, ex=ttl, nx=nx)

            # 更新本地缓存
            self._set_local(full_key, value)

            if result:
                self._stats["sets"] += 1
            return bool(result)

        except Exception as e:
            logger.error(f"Redis SET 失败 [{key}]: {e}")
            self._stats["errors"] += 1
            return False

    def delete(self, *keys: str) -> int:
        """删除一个或多个键"""
        if not keys:
            return 0

        full_keys = [self._make_key(k) for k in keys]

        # 清除本地缓存
        for k in full_keys:
            self._local_cache.pop(k, None)

        if not self.is_available:
            return len(keys)

        try:
            deleted = self._redis.delete(*full_keys)
            self._stats["deletes"] += deleted
            return deleted
        except Exception as e:
            logger.error(f"Redis DELETE 失败: {e}")
            self._stats["errors"] += 1
            return 0

    def exists(self, *keys: str) -> bool:
        """检查键是否存在"""
        if not keys:
            return False

        for k in keys:
            if self._exists_local(self._make_key(k)):
                return True

        if not self.is_available:
            return False

        try:
            full_keys = [self._make_key(k) for k in keys]
            return bool(self._redis.exists(*full_keys))
        except Exception as e:
            logger.error(f"Redis EXISTS 失败: {e}")
            return False

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取多个键的值"""
        result = {}
        missing_keys = []

        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
            else:
                missing_keys.append(key)

        return result

    def set_many(
        self,
        mapping: Dict[str, Any],
        ttl: int = DEFAULT_REDIS_TTL
    ) -> int:
        """批量设置多个键值对"""
        if not mapping or not self.is_available:
            return 0

        try:
            pipe = self._redis.pipeline(transaction=False)
            for key, value in mapping.items():
                full_key = self._make_key(key)
                serialized = self._serialize(value)
                pipe.setex(full_key, ttl, serialized)
                self._set_local(full_key, value)

            results = pipe.execute()
            success_count = sum(1 for r in results if r)
            self._stats["sets"] += success_count
            return success_count

        except Exception as e:
            logger.error(f"Redis MSET 失败: {e}")
            self._stats["errors"] += 1
            return 0

    def incr(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """原子递增"""
        full_key = self._make_key(key)

        if not self.is_available:
            return 0

        try:
            pipe = self._redis.pipeline()
            pipe.incrby(full_key, amount)
            if ttl:
                pipe.expire(full_key, ttl)
            results = pipe.execute()
            return results[0]
        except Exception as e:
            logger.error(f"Redis INCR 失败 [{key}]: {e}")
            self._stats["errors"] += 1
            return 0

    def expire(self, key: str, ttl: int) -> bool:
        """设置键的过期时间"""
        if not self.is_available:
            return False

        try:
            return bool(self._redis.expire(self._make_key(key), ttl))
        except Exception as e:
            logger.error(f"Redis EXPIRE 失败 [{key}]: {e}")
            return False

    def ttl(self, key: str) -> int:
        """获取键的剩余过期时间"""
        if not self.is_available:
            return -1

        try:
            return self._redis.ttl(self._make_key(key))
        except Exception:
            return -1

    def lock(
        self,
        key: str,
        timeout: int = 10,
        blocking_timeout: Optional[int] = None
    ) -> bool:
        """
        获取分布式锁

        Args:
            key: 锁名称
            timeout: 锁超时时间（秒）
            blocking_timeout: 阻塞等待时间（秒），None 为非阻塞

        Returns:
            是否获取成功
        """
        lock_key = self._make_key(f"lock:{key}")

        if not self.is_available:
            return True  # Redis 不可用时跳过锁

        try:
            acquired = self._redis.set(
                lock_key,
                "1",
                nx=True,
                ex=timeout
            )

            if blocking_timeout and not acquired:
                start = time.time()
                while time.time() - start < blocking_timeout:
                    time.sleep(0.05)
                    acquired = self._redis.set(lock_key, "1", nx=True, ex=timeout)
                    if acquired:
                        break

            return bool(acquired)

        except Exception as e:
            logger.error(f"获取分布式锁失败 [{key}]: {e}")
            return False

    def unlock(self, key: str) -> bool:
        """释放分布式锁"""
        lock_key = self._make_key(f"lock:{key}")

        if not self.is_available:
            return True

        try:
            return bool(self._redis.delete(lock_key))
        except Exception as e:
            logger.error(f"释放分布式锁失败 [{key}]: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """根据模式清除匹配的键"""
        if not self.is_available:
            return 0

        try:
            full_pattern = self._make_key(pattern)
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = self._redis.scan(cursor, match=full_pattern, count=100)
                if keys:
                    deleted += self._redis.delete(*keys)
                if cursor == 0:
                    break

            # 清除本地缓存中的匹配项
            local_keys_to_remove = [
                k for k in self._local_cache.keys()
                if k.startswith(self._prefix + pattern.replace("*", ""))
            ]
            for k in local_keys_to_remove:
                del self._local_cache[k]

            return deleted

        except Exception as e:
            logger.error(f"清除模式失败 [{pattern}]: {e}")
            return 0

    def _get_local(self, key: str) -> Optional[Any]:
        """从本地缓存获取"""
        if key in self._local_cache:
            value, timestamp = self._local_cache[key]
            if time.time() - timestamp < self._local_cache_ttl:
                return value
            else:
                del self._local_cache[key]
        return None

    def _set_local(self, key: str, value: Any) -> None:
        """写入本地缓存"""
        if len(self._local_cache) >= self._local_cache_size:
            oldest_key = next(iter(self._local_cache))
            del self._local_cache[oldest_key]
        self._local_cache[key] = (value, time.time())

    def _exists_local(self, key: str) -> bool:
        """检查本地缓存是否存在"""
        return self._get_local(key) is not None

    def _set_null_key(self, key: str) -> bool:
        """设置空值标记（防止缓存穿透）"""
        if not self.is_available:
            return True

        try:
            return bool(self._redis.setex(key, CACHE_NULL_TTL, "__NULL__"))
        except Exception:
            return False

    def clear_local_cache(self) -> None:
        """清空本地缓存"""
        self._local_cache.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0

        return {
            **self._stats,
            "hit_rate": round(hit_rate, 2),
            "local_cache_size": len(self._local_cache),
            "is_available": self.is_available,
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        for key in self._stats:
            self._stats[key] = 0


def cache_decorator(
    cache_instance: RedisCache,
    ttl: int = DEFAULT_REDIS_TTL,
    key_prefix: str = "",
    skip_args: Optional[List[int]] = None
):
    """
    缓存装饰器工厂

    用法：
        @cache_decorator(redis_cache, ttl=300, key_prefix="product:")
        def get_product(product_id):
            ...

    Args:
        cache_instance: RedisCache 实例
        ttl: 缓存过期时间
        key_prefix: 键前缀
        skip_args: 要跳过的参数索引列表（如 self）
    """
    skip_args = skip_args or []

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                cache_key_parts = [
                    str(arg) for i, arg in enumerate(args)
                    if i not in skip_args
                ]
                cache_key_parts.extend(
                    f"{k}={v}" for k, v in sorted(kwargs.items())
                )
                cache_key_str = ":".join(cache_key_parts)
                cache_key = f"{key_prefix}{func.__name__}:{hashlib.md5(cache_key_str.encode()).hexdigest()}"

                cached = cache_instance.get(cache_key)
                if cached is not None:
                    return cached

                result = func(*args, **kwargs)
                cache_instance.set(cache_key, result, ttl=ttl)
                return result

            except Exception as e:
                logger.error(f"缓存装饰器执行失败 [{func.__name__}]: {e}")
                return func(*args, **kwargs)

        return wrapper
    return decorator


def async_cache_decorator(
    cache_instance: RedisCache,
    ttl: int = DEFAULT_REDIS_TTL,
    key_prefix: str = ""
):
    """
    异步结果缓存装饰器

    用于包装 Celery 任务，先返回缓存结果，后台异步更新
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}{func.__name__}:{hashlib.md5(str(args + tuple(sorted(kwargs.items()))).encode()).hexdigest()}"

            cached = cache_instance.get(cache_key)
            if cached is not None:
                return {"cached": True, "data": cached}

            try:
                result = func(*args, **kwargs)
                cache_instance.set(cache_key, result, ttl=ttl)
                return {"cached": False, "data": result}
            except Exception as e:
                logger.error(f"异步缓存装饰器失败 [{func.__name__}]: {e}")
                raise

        wrapper.cache_key = lambda *a, **kw: f"{key_prefix}{func.__name__}:{hashlib.md5(str(a + tuple(sorted(kw.items()))).encode()).hexdigest()}"
        return wrapper
    return decorator


_redis_cache_instance: Optional[RedisCache] = None


def get_redis_cache(redis_client=None) -> RedisCache:
    """获取 Redis 缓存单例"""
    global _redis_cache_instance
    if _redis_cache_instance is None:
        _redis_cache_instance = RedisCache(redis_client)
    return _redis_cache_instance


def init_redis_cache_from_app(app) -> Optional[RedisCache]:
    """从 Flask 应用初始化 Redis 缓存"""
    global _redis_cache_instance

    redis_client = getattr(app.extensions.get('cache'), '_client', None) if hasattr(app, 'extensions') else None

    if redis_client is None:
        try:
            import redis
            redis_url = app.config.get('CACHE_REDIS_URL', 'redis://localhost:6379/0')
            redis_client = redis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.warning(f"无法连接 Redis: {e}")
            return None

    _redis_cache_instance = RedisCache(redis_client)
    logger.info("Redis 缓存初始化完成")
    return _redis_cache_instance
