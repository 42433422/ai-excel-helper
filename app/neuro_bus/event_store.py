"""
事件存储与重播 - Level 4 可靠性机制

提供：
- 事件持久化存储
- 事件溯源支持
- 快照管理
- 时间旅行（重播）
- 审计日志
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from app.neuro_bus.events.base import NeuroEvent

logger = logging.getLogger(__name__)


class EventStoreMode(Enum):
    """存储模式"""

    MEMORY = "memory"  # 内存存储（仅用于测试）
    JSON_FILE = "json"  # JSON 文件
    SQLITE = "sqlite"  # SQLite 数据库


@dataclass
class StoredEvent:
    """存储的事件记录"""

    store_id: str
    event: NeuroEvent
    stored_at: datetime
    sequence_number: int
    stream_id: str | None = None  # 事件流 ID（用于聚合根）
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "store_id": self.store_id,
            "event": {
                "event_id": self.event.metadata.event_id,
                "event_type": self.event.event_type,
                "payload": self.event.payload,
                "timestamp": self.event.metadata.timestamp,
                "source": self.event.metadata.source,
                "correlation_id": self.event.metadata.correlation_id,
                "priority": self.event.priority.value,
            },
            "stored_at": self.stored_at.isoformat(),
            "sequence_number": self.sequence_number,
            "stream_id": self.stream_id,
            "metadata": self.metadata,
        }


@dataclass
class Snapshot:
    """聚合根快照"""

    snapshot_id: str
    stream_id: str
    sequence_number: int
    state: dict[str, Any]
    created_at: datetime
    version: int = 1


class EventStore:
    """
    事件存储

    Level 4 可靠性机制:
    - 持久化所有领域事件
    - 支持事件溯源
    - 快照优化加载性能
    - 时间旅行调试
    """

    def __init__(
        self,
        mode: EventStoreMode = EventStoreMode.MEMORY,
        storage_path: str | None = None,
        max_events: int = 100000,
    ):
        self._mode = mode
        self._storage_path = storage_path
        self._max_events = max_events

        # 内存存储
        self._events: dict[str, StoredEvent] = {}
        self._stream_events: dict[str, list[str]] = {}  # stream_id -> [store_id]
        self._snapshots: dict[str, Snapshot] = {}

        # 序列号生成
        self._sequence_counter = 0

        # 回调
        self._append_callbacks: list[Callable[[StoredEvent], None]] = []

        logger.info(f"[EventStore] 初始化完成 (mode={mode.value}, max_events={max_events})")

    # ========== 存储操作 ==========

    def append(
        self,
        event: NeuroEvent,
        stream_id: str | None = None,
    ) -> str:
        """
        存储事件

        Returns:
            存储 ID
        """
        store_id = f"evt-{uuid4().hex[:12]}"

        self._sequence_counter += 1

        stored = StoredEvent(
            store_id=store_id,
            event=event,
            stored_at=datetime.now(),
            sequence_number=self._sequence_counter,
            stream_id=stream_id,
        )

        # 容量检查
        if len(self._events) >= self._max_events:
            self._cleanup_oldest()

        # 存储
        self._events[store_id] = stored

        # 按流索引
        if stream_id:
            if stream_id not in self._stream_events:
                self._stream_events[stream_id] = []
            self._stream_events[stream_id].append(store_id)

        logger.debug(f"[EventStore] 事件存储: {event.event_type} (store_id={store_id})")

        # 触发回调
        for callback in self._append_callbacks:
            try:
                callback(stored)
            except Exception as e:
                logger.error(f"[EventStore] 回调失败: {e}")

        return store_id

    def append_many(
        self,
        events: list[NeuroEvent],
        stream_id: str | None = None,
    ) -> list[str]:
        """批量存储事件"""
        return [self.append(e, stream_id) for e in events]

    # ========== 查询操作 ==========

    def get(self, store_id: str) -> StoredEvent | None:
        """获取单个事件"""
        return self._events.get(store_id)

    def get_all(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        event_type: str | None = None,
    ) -> Iterator[StoredEvent]:
        """
        获取事件流

        支持时间范围和事件类型筛选
        """
        for stored in sorted(self._events.values(), key=lambda e: e.sequence_number):
            # 时间筛选
            if start_time and stored.stored_at < start_time:
                continue
            if end_time and stored.stored_at > end_time:
                continue

            # 类型筛选
            if event_type and stored.event.event_type != event_type:
                continue

            yield stored

    def get_stream_events(
        self,
        stream_id: str,
        from_sequence: int = 0,
    ) -> list[StoredEvent]:
        """
        获取事件流中的所有事件

        用于事件溯源加载聚合根
        """
        store_ids = self._stream_events.get(stream_id, [])
        events = []

        for store_id in store_ids:
            stored = self._events.get(store_id)
            if stored and stored.sequence_number >= from_sequence:
                events.append(stored)

        return sorted(events, key=lambda e: e.sequence_number)

    def get_latest(self, limit: int = 100) -> list[StoredEvent]:
        """获取最新的事件"""
        sorted_events = sorted(self._events.values(), key=lambda e: e.sequence_number, reverse=True)
        return sorted_events[:limit]

    # ========== 快照管理 ==========

    def save_snapshot(
        self,
        stream_id: str,
        state: dict[str, Any],
        sequence_number: int,
    ) -> str:
        """
        保存聚合根快照

        用于优化事件溯源加载性能
        """
        snapshot_id = f"snap-{uuid4().hex[:12]}"

        snapshot = Snapshot(
            snapshot_id=snapshot_id,
            stream_id=stream_id,
            sequence_number=sequence_number,
            state=state,
            created_at=datetime.now(),
        )

        self._snapshots[stream_id] = snapshot

        logger.debug(
            f"[EventStore] 快照保存: {stream_id} " f"(seq={sequence_number}, snap_id={snapshot_id})"
        )

        return snapshot_id

    def get_snapshot(self, stream_id: str) -> Snapshot | None:
        """获取最新快照"""
        return self._snapshots.get(stream_id)

    def get_events_after_snapshot(self, stream_id: str) -> list[StoredEvent]:
        """获取快照后的事件（用于恢复聚合根）"""
        snapshot = self._snapshots.get(stream_id)
        if not snapshot:
            # 没有快照，返回所有事件
            return self.get_stream_events(stream_id)

        # 返回快照之后的事件
        return self.get_stream_events(stream_id, from_sequence=snapshot.sequence_number + 1)

    # ========== 重播机制 ==========

    def replay(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        event_types: list[str] | None = None,
        stream_id: str | None = None,
        callback: Callable[[NeuroEvent], None] | None = None,
    ) -> int:
        """
        重播事件

        支持：
        - 时间范围筛选
        - 事件类型筛选
        - 特定流重播

        Returns:
            重播的事件数量
        """
        count = 0

        if stream_id:
            # 重播特定流
            events = self.get_stream_events(stream_id)
        else:
            # 重播所有事件
            events = list(self.get_all(start_time, end_time))

        for stored in events:
            # 类型筛选
            if event_types and stored.event.event_type not in event_types:
                continue

            # 执行重播
            if callback:
                try:
                    callback(stored.event)
                    count += 1
                except Exception as e:
                    logger.error(f"[EventStore] 重播失败: {e}")
            else:
                # 默认：只记录
                logger.info(
                    f"[EventStore] 重播: {stored.event.event_type} (store_id={stored.store_id})"
                )
                count += 1

        logger.info(f"[EventStore] 重播完成: {count} 个事件")
        return count

    def replay_stream(
        self,
        stream_id: str,
        use_snapshot: bool = True,
        callback: Callable[[NeuroEvent], None] | None = None,
    ) -> dict[str, Any]:
        """
        重播事件流（用于恢复聚合根）

        Returns:
            恢复的状态和元数据
        """
        snapshot = None
        start_sequence = 0

        if use_snapshot:
            snapshot = self.get_snapshot(stream_id)
            if snapshot:
                start_sequence = snapshot.sequence_number + 1

        events = self.get_stream_events(stream_id, from_sequence=start_sequence)

        applied_count = 0
        for stored in events:
            if callback:
                callback(stored.event)
            applied_count += 1

        result = {
            "stream_id": stream_id,
            "applied_events": applied_count,
            "snapshot_used": snapshot is not None,
        }

        if snapshot:
            result["snapshot_sequence"] = snapshot.sequence_number
            result["snapshot_age_seconds"] = (datetime.now() - snapshot.created_at).total_seconds()

        logger.info(f"[EventStore] 流重播完成: {stream_id} (applied={applied_count})")

        return result

    # ========== 审计 ==========

    def get_audit_log(
        self,
        stream_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """获取审计日志"""
        if stream_id:
            events = self.get_stream_events(stream_id)
        else:
            events = list(self.get_all(start_time, end_time))

        return [
            {
                "timestamp": e.stored_at.isoformat(),
                "event_type": e.event.event_type,
                "event_id": e.event.metadata.event_id,
                "source": e.event.metadata.source,
                "correlation_id": e.event.metadata.correlation_id,
                "payload_keys": list(e.event.payload.keys()),
            }
            for e in events
        ]

    # ========== 统计 ==========

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        by_type = {}
        for stored in self._events.values():
            et = stored.event.event_type
            by_type[et] = by_type.get(et, 0) + 1

        by_stream = {
            stream_id: len(store_ids) for stream_id, store_ids in self._stream_events.items()
        }

        return {
            "total_events": len(self._events),
            "max_events": self._max_events,
            "streams": len(self._stream_events),
            "snapshots": len(self._snapshots),
            "by_event_type": by_type,
            "by_stream": by_stream,
            "oldest_event": (
                min(e.stored_at for e in self._events.values()).isoformat()
                if self._events
                else None
            ),
            "newest_event": (
                max(e.stored_at for e in self._events.values()).isoformat()
                if self._events
                else None
            ),
        }

    # ========== 管理 ==========

    def delete_stream(self, stream_id: str) -> int:
        """删除整个事件流"""
        store_ids = self._stream_events.get(stream_id, [])
        count = 0

        for store_id in store_ids:
            if store_id in self._events:
                del self._events[store_id]
                count += 1

        if stream_id in self._stream_events:
            del self._stream_events[stream_id]

        if stream_id in self._snapshots:
            del self._snapshots[stream_id]

        logger.info(f"[EventStore] 删除流: {stream_id} ({count} 个事件)")
        return count

    def clear(self):
        """清空所有数据"""
        self._events.clear()
        self._stream_events.clear()
        self._snapshots.clear()
        self._sequence_counter = 0
        logger.info("[EventStore] 已清空")

    def on_append(self, callback: Callable[[StoredEvent], None]):
        """注册追加回调"""
        self._append_callbacks.append(callback)

    def _cleanup_oldest(self, count: int = 1000):
        """清理最老的事件"""
        sorted_events = sorted(self._events.values(), key=lambda e: e.sequence_number)
        to_remove = sorted_events[:count]

        for stored in to_remove:
            del self._events[stored.store_id]

            # 从流索引中移除
            if stored.stream_id and stored.stream_id in self._stream_events:
                stream_list = self._stream_events[stored.stream_id]
                if stored.store_id in stream_list:
                    stream_list.remove(stored.store_id)

        logger.warning(f"[EventStore] 清理旧事件: {len(to_remove)} 个")


# ========== 全局实例 ==========

_event_store_instance: EventStore | None = None


def get_event_store() -> EventStore:
    """获取全局事件存储实例"""
    global _event_store_instance
    if _event_store_instance is None:
        _event_store_instance = EventStore()
    return _event_store_instance


# 快捷函数


def store_event(event: NeuroEvent, stream_id: str | None = None) -> str:
    """快捷函数：存储事件"""
    return get_event_store().append(event, stream_id)


def replay_events(**kwargs) -> int:
    """快捷函数：重播事件"""
    return get_event_store().replay(**kwargs)


def get_event_stats() -> dict[str, Any]:
    """快捷函数：获取统计"""
    return get_event_store().get_stats()
