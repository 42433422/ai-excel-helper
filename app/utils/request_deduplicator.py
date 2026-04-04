# -*- coding: utf-8 -*-
"""
请求去重器

防止重复请求导致的：
- 重复数据处理
- 资源浪费
- 数据不一致

支持：
- 基于请求内容的去重
- 基于用户+操作的去重
- 时间窗口去重
- 幂等性保证
"""

import hashlib
import logging
import os
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import wraps
from threading import Lock
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

DEDUP_WINDOW_SECONDS = int(os.environ.get("XCAGI_DEDUP_WINDOW", "60"))
DEDUP_MAX_KEYS = int(os.environ.get("XCAGI_DEDUP_MAX_KEYS", "10000"))


@dataclass
class DedupRecord:
    """去重记录"""
    key: str
    result: Optional[Any] = None
    timestamp: float = field(default_factory=time.time)
    is_processing: bool = False
    waiters: list = field(default_factory=list)


class RequestDeduplicator:
    """
    请求去重器

    策略：
    1. 精确匹配：完全相同的请求参数
    2. 语义匹配：相同用户+相同操作类型
    3. 时间窗口：在指定时间内的重复请求
    """

    def __init__(
        self,
        window_seconds: int = DEDUP_WINDOW_SECONDS,
        max_keys: int = DEDUP_MAX_KEYS
    ):
        self._window_seconds = window_seconds
        self._max_keys = max_keys
        self._records: OrderedDict[str, DedupRecord] = OrderedDict()
        self._lock = Lock()
        self._stats = {
            "total_requests": 0,
            "deduplicated": 0,
            "cache_hits": 0,
            "processing": 0,
        }

    def _make_key(self, *args, **kwargs) -> str:
        """生成去重键"""
        parts = []
        for arg in args:
            if hasattr(arg, '__dict__'):
                parts.append(str(sorted(arg.__dict__.items())))
            else:
                parts.append(str(arg))
        parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_str = "|".join(parts)
        return hashlib.sha256(key_str.encode('utf-8')).hexdigest()[:32]

    def _cleanup_expired(self) -> int:
        """清理过期记录"""
        cutoff = time.time() - self._window_seconds
        expired = [k for k, v in self._records.items() if v.timestamp < cutoff]

        for k in expired:
            del self._records[k]

        return len(expired)

    def deduplicate(
        self,
        func: Callable,
        *args,
        use_cache: bool = True,
        cache_result: bool = True,
        **kwargs
    ) -> Tuple[bool, Any]:
        """
        执行去重检查并调用函数

        Returns:
            (is_deduplicated, result)
        """
        key = self._make_key(func.__name__, *args, **kwargs)

        with self._lock:
            self._stats["total_requests"] += 1
            self._cleanup_expired()

            record = self._records.get(key)

            if record and not record.is_processing:
                elapsed = time.time() - record.timestamp
                if elapsed < self._window_seconds:
                    self._stats["deduplicated"] += 1
                    if use_cache and record.result is not None:
                        self._stats["cache_hits"] += 1
                        logger.debug(f"请求去重命中 (缓存): {func.__name__}")
                        return (True, record.result)
                    logger.debug(f"请求去重命中 (处理中): {func.__name__}")
                    return (True, None)

            new_record = DedupRecord(key=key, is_processing=True)
            self._records[key] = new_record
            if len(self._records) > self._max_keys:
                self._records.popitem(last=False)

        try:
            result = func(*args, **kwargs)

            with self._lock:
                new_record.result = result
                new_record.is_processing = False
                new_record.timestamp = time.time()
                if not cache_result:
                    del self._records[key]

            return (False, result)

        except Exception as e:
            with self._lock:
                if key in self._records:
                    del self._records[key]
            raise e

    def check_and_wait(
        self,
        func: Callable,
        *args,
        timeout: float = 30.0,
        **kwargs
    ) -> Tuple[bool, Any]:
        """
        检查重复，如果正在处理则等待结果

        用于处理并发重复请求场景
        """
        key = self._make_key(func.__name__, *args, **kwargs)

        with self._lock:
            self._stats["total_requests"] += 1
            record = self._records.get(key)

            if record and record.is_processing:
                self._stats["processing"] += 1
                start_wait = time.time()

                while record.is_processing and (time.time() - start_wait) < timeout:
                    self._lock.release()
                    time.sleep(0.05)
                    self._lock.acquire()

                if record.result is not None:
                    self._stats["cache_hits"] += 1
                    return (True, record.record)

                return (False, None)

            new_record = DedupRecord(key=key, is_processing=True)
            self._records[key] = new_record

        try:
            result = func(*args, **kwargs)

            with self._lock:
                new_record.result = result
                new_record.is_processing = False

            return (False, result)

        except Exception as e:
            with self._lock:
                if key in self._records:
                    del self._records[key]
            raise e

    def invalidate(self, func: Callable = None, *args, **kwargs) -> int:
        """使缓存失效"""
        if func:
            key = self._make_key(func.__name__, *args, **kwargs)
            if key in self._records:
                del self._records[key]
                return 1
            return 0
        else:
            count = len(self._records)
            self._records.clear()
            return count

    @property
    def stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self._stats.get("total_requests", 1)
        if total == 0:
            return {
                **self._stats,
                "dedup_rate": 0.0,
                "active_records": len(self._records),
            }
        return {
            **self._stats,
            "dedup_rate": round(self._stats.get("deduplicated", 0) / total * 100, 2),
            "active_records": len(self._records),
        }

    def reset_stats(self) -> None:
        """重置统计"""
        for k in self._stats:
            self._stats[k] = 0


_deduplicator_instance: Optional[RequestDeduplicator] = None


def get_request_deduplicator() -> RequestDeduplicator:
    """获取请求去重器单例"""
    global _deduplicator_instance
    if _deduplicator_instance is None:
        _deduplicator_instance = RequestDeduplicator()
    return _deduplicator_instance


def deduplicate_request(window_seconds: int = DEDUP_WINDOW_SECONDS):
    """
    请求去重装饰器

    用法：
        @deduplicate_request(window_seconds=30)
        def create_order(customer_id, product_id, quantity):
            ...

        # 相同参数在 30 秒内只会执行一次
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            deduplicator = get_request_deduplicator()
            is_dup, result = deduplicator.deduplicate(func, *args, **kwargs)
            return result
        return wrapper
    return decorator


def idempotent_operation(idempotency_key_func: Optional[Callable] = None, ttl: int = 86400):
    """
    幂等性操作装饰器

    保证相同的业务操作只执行一次（基于业务键）

    用法：
        @idempotent_operation(lambda order_no: f"order:{order_no}")
        def process_payment(order_no, amount):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            deduplicator = get_request_deduplicator()

            if idempotency_key_func:
                key = idempotency_key_func(*args, **kwargs)
            else:
                key = f"idempotent:{func.__name__}:{str(args)}:{str(kwargs)}"

            is_dup, result = deduplicator.deduplicate(
                func, *args,
                use_cache=True,
                cache_result=True,
                **kwargs
            )

            if is_dup:
                logger.info(f"幂等操作跳过: {key}")

            return result
        return wrapper
    return decorator
