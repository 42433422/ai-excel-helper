"""
去重器（Deduplicator）

基于事件内容生成去重键，防止重复处理相同事件
结合 TTL 机制自动清理过期记录
"""

import logging
import time
from dataclasses import dataclass
from threading import RLock
from typing import Any

from app.neuro_bus.events.base import NeuroEvent

logger = logging.getLogger(__name__)


@dataclass
class DedupEntry:
    """去重条目"""

    dedup_key: str
    event_id: str
    timestamp: float
    processed: bool
    result: Any | None = None


class EventDeduplicator:
    """
    事件去重器

    提供基于内存的高效去重，支持：
    - SHA-256 内容哈希
    - TTL 自动过期
    - 并发安全
    """

    def __init__(
        self,
        ttl_seconds: float = 60.0,
        max_entries: int = 10000,
        cleanup_interval: float = 30.0,
    ):
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._cleanup_interval = cleanup_interval

        # 存储结构: dedup_key -> DedupEntry
        self._entries: dict[str, DedupEntry] = {}
        self._event_to_key: dict[str, str] = {}  # event_id -> dedup_key

        self._lock = RLock()
        self._last_cleanup = time.time()

        logger.info(f"EventDeduplicator initialized (ttl={ttl_seconds}s, max={max_entries})")

    def is_duplicate(self, event: NeuroEvent) -> bool:
        """
        检查是否为重复事件

        Returns:
            True: 是重复事件（已存在且未过期）
            False: 新事件
        """
        dedup_key = event.get_dedup_key()

        with self._lock:
            self._maybe_cleanup()

            if dedup_key in self._entries:
                entry = self._entries[dedup_key]
                age = time.time() - entry.timestamp

                if age < self._ttl:
                    logger.debug(f"Duplicate detected: {dedup_key[:16]}... (age={age:.1f}s)")
                    return True
                else:
                    # 已过期，删除旧记录
                    del self._entries[dedup_key]
                    if entry.event_id in self._event_to_key:
                        del self._event_to_key[entry.event_id]

            return False

    def mark_processing(self, event: NeuroEvent) -> bool:
        """
        标记事件正在处理

        Returns:
            True: 成功标记为新事件
            False: 重复事件或已在处理
        """
        dedup_key = event.get_dedup_key()

        with self._lock:
            self._maybe_cleanup()

            # 检查是否已存在
            if dedup_key in self._entries:
                entry = self._entries[dedup_key]
                age = time.time() - entry.timestamp

                if age < self._ttl and entry.processed:
                    # 已处理完成，是重复事件
                    return False

                if age < self._ttl and not entry.processed:
                    # 正在处理中，视为重复
                    logger.warning(f"Event already processing: {dedup_key[:16]}...")
                    return False

            # 容量检查
            if len(self._entries) >= self._max_entries:
                self._evict_oldest()

            # 创建新条目
            entry = DedupEntry(
                dedup_key=dedup_key,
                event_id=event.metadata.event_id,
                timestamp=time.time(),
                processed=False,
            )

            self._entries[dedup_key] = entry
            self._event_to_key[event.metadata.event_id] = dedup_key

            return True

    def mark_processed(self, event: NeuroEvent, result: Any | None = None):
        """标记事件已处理完成"""
        dedup_key = event.get_dedup_key()

        with self._lock:
            if dedup_key in self._entries:
                entry = self._entries[dedup_key]
                entry.processed = True
                entry.result = result
                logger.debug(f"Marked processed: {dedup_key[:16]}...")

    def get_result(self, event: NeuroEvent) -> Any | None:
        """获取已处理事件的结果（用于幂等返回）"""
        dedup_key = event.get_dedup_key()

        with self._lock:
            if dedup_key in self._entries:
                entry = self._entries[dedup_key]
                if entry.processed:
                    return entry.result
            return None

    def remove(self, event: NeuroEvent):
        """手动移除事件记录"""
        dedup_key = event.get_dedup_key()

        with self._lock:
            if dedup_key in self._entries:
                del self._entries[dedup_key]
            if event.metadata.event_id in self._event_to_key:
                del self._event_to_key[event.metadata.event_id]

    def _maybe_cleanup(self):
        """触发清理检查"""
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = now

    def _cleanup_expired(self):
        """清理过期条目"""
        now = time.time()
        expired_keys = [
            key for key, entry in self._entries.items() if now - entry.timestamp > self._ttl
        ]

        for key in expired_keys:
            entry = self._entries.pop(key, None)
            if entry and entry.event_id in self._event_to_key:
                del self._event_to_key[entry.event_id]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired entries")

    def _evict_oldest(self):
        """淘汰最老的条目（LRU策略）"""
        if not self._entries:
            return

        oldest_key = min(self._entries.keys(), key=lambda k: self._entries[k].timestamp)

        entry = self._entries.pop(oldest_key)
        if entry.event_id in self._event_to_key:
            del self._event_to_key[entry.event_id]

        logger.debug(f"Evicted oldest entry: {oldest_key[:16]}...")

    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            return {
                "total_entries": len(self._entries),
                "processing": sum(1 for e in self._entries.values() if not e.processed),
                "processed": sum(1 for e in self._entries.values() if e.processed),
                "ttl_seconds": self._ttl,
                "max_entries": self._max_entries,
            }


class NeuroBusDeduplicator:
    """
    NeuroBus 去重包装器

    为 NeuroBus 提供去重功能
    """

    def __init__(self, ttl_seconds: float = 60.0):
        self._dedup = EventDeduplicator(ttl_seconds=ttl_seconds)

    def check_and_acquire(self, event: NeuroEvent) -> bool:
        """
        检查并获取处理权

        Returns:
            True: 可以处理（非重复）
            False: 重复事件，应跳过
        """
        return self._dedup.mark_processing(event)

    def release(self, event: NeuroEvent, result: Any | None = None):
        """释放事件并记录结果"""
        self._dedup.mark_processed(event, result)

    def is_duplicate(self, event: NeuroEvent) -> bool:
        """检查是否为重复"""
        return self._dedup.is_duplicate(event)

    def get_cached_result(self, event: NeuroEvent) -> Any | None:
        """获取缓存结果"""
        return self._dedup.get_result(event)


_neuro_bus_deduplicator: NeuroBusDeduplicator | None = None


def get_deduplicator() -> NeuroBusDeduplicator:
    """NeuroBus 初始化器使用的单例。"""
    global _neuro_bus_deduplicator
    if _neuro_bus_deduplicator is None:
        _neuro_bus_deduplicator = NeuroBusDeduplicator()
    return _neuro_bus_deduplicator
