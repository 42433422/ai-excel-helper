"""
死信队列 (Dead Letter Queue) - Level 4 可靠性机制

处理无法成功处理的事件：
- 重试次数耗尽
- 不可恢复的异常
- 超时事件

提供：
- 死信存储
- 重播机制
- 告警通知
- 手动干预接口
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from app.neuro_bus.events.base import NeuroEvent

logger = logging.getLogger(__name__)


class DeadLetterReason(Enum):
    """进入死信队列的原因"""

    RETRY_EXHAUSTED = "retry_exhausted"  # 重试次数耗尽
    UNRECOVERABLE = "unrecoverable"  # 不可恢复异常
    TIMEOUT = "timeout"  # 处理超时
    INVALID_PAYLOAD = "invalid_payload"  # 无效载荷
    HANDLER_NOT_FOUND = "handler_not_found"  # 找不到处理器
    CIRCUIT_BREAKER = "circuit_breaker"  # 熔断器开启


@dataclass
class DeadLetterEntry:
    """死信条目"""

    entry_id: str
    original_event: NeuroEvent
    reason: DeadLetterReason
    error_message: str
    error_stack: str | None
    retry_count: int
    first_failure_time: datetime
    last_failure_time: datetime
    handler_name: str | None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def age_seconds(self) -> float:
        """条目年龄（秒）"""
        return (datetime.now() - self.first_failure_time).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """序列化"""
        return {
            "entry_id": self.entry_id,
            "original_event": {
                "event_id": self.original_event.metadata.event_id,
                "event_type": self.original_event.event_type,
                "payload": self.original_event.payload,
                "timestamp": self.original_event.metadata.timestamp,
            },
            "reason": self.reason.value,
            "error_message": self.error_message,
            "error_stack": self.error_stack,
            "retry_count": self.retry_count,
            "first_failure_time": self.first_failure_time.isoformat(),
            "last_failure_time": self.last_failure_time.isoformat(),
            "handler_name": self.handler_name,
            "metadata": self.metadata,
            "age_seconds": self.age_seconds,
        }


class DeadLetterQueue:
    """
    死信队列实现

    Level 4 可靠性机制:
    - 存储失败事件
    - 支持重播
    - 提供监控和告警
    """

    def __init__(self, max_size: int = 10000, retention_hours: int = 168):
        """
        Args:
            max_size: 最大条目数
            retention_hours: 保留时间（小时，默认 7 天）
        """
        self._entries: dict[str, DeadLetterEntry] = {}
        self._max_size = max_size
        self._retention_seconds = retention_hours * 3600
        self._alert_callbacks: list[Callable[[DeadLetterEntry], None]] = []
        self._replay_callbacks: list[Callable[[NeuroEvent], None]] = []
        self._stats = {
            "total_entries": 0,
            "replayed": 0,
            "expired": 0,
            "manually_resolved": 0,
        }

        logger.info(
            f"[DeadLetterQueue] 初始化完成 (max_size={max_size}, retention={retention_hours}h)"
        )

    # ========== 核心操作 ==========

    def enqueue(
        self,
        event: NeuroEvent,
        reason: DeadLetterReason,
        error_message: str,
        retry_count: int,
        handler_name: str | None = None,
        error_stack: str | None = None,
    ) -> str:
        """
        将事件加入死信队列

        Returns:
            死信条目 ID
        """
        entry_id = f"dlq-{uuid4().hex[:12]}"
        now = datetime.now()

        entry = DeadLetterEntry(
            entry_id=entry_id,
            original_event=event,
            reason=reason,
            error_message=error_message,
            error_stack=error_stack,
            retry_count=retry_count,
            first_failure_time=now,
            last_failure_time=now,
            handler_name=handler_name,
            metadata={
                "enqueue_time": now.isoformat(),
            },
        )

        # 容量检查
        if len(self._entries) >= self._max_size:
            self._evict_oldest()

        self._entries[entry_id] = entry
        self._stats["total_entries"] += 1

        logger.error(
            f"[DeadLetterQueue] 事件进入死信队列: {event.event_type} "
            f"(reason={reason.value}, entry_id={entry_id}, retries={retry_count})"
        )

        # 触发告警
        self._trigger_alert(entry)

        return entry_id

    def dequeue(self, entry_id: str) -> DeadLetterEntry | None:
        """取出条目（不移除）"""
        return self._entries.get(entry_id)

    def remove(self, entry_id: str) -> bool:
        """移除条目"""
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False

    def replay(self, entry_id: str) -> bool:
        """
        重播死信事件

        Returns:
            是否成功触发重播
        """
        entry = self._entries.get(entry_id)
        if not entry:
            logger.warning(f"[DeadLetterQueue] 重播失败：找不到条目 {entry_id}")
            return False

        logger.info(
            f"[DeadLetterQueue] 重播事件: {entry.original_event.event_type} (entry_id={entry_id})"
        )

        # 触发重播回调
        for callback in self._replay_callbacks:
            try:
                callback(entry.original_event)
            except Exception as e:
                logger.error(f"[DeadLetterQueue] 重播回调失败: {e}")

        # 更新统计
        self._stats["replayed"] += 1

        # 可选：重播后从队列移除
        # self.remove(entry_id)

        return True

    def replay_all(
        self,
        event_type: str | None = None,
        max_age_seconds: float | None = None,
    ) -> int:
        """
        批量重播

        Args:
            event_type: 筛选特定事件类型
            max_age_seconds: 最大年龄筛选

        Returns:
            重播数量
        """
        to_replay = []

        for entry_id, entry in self._entries.items():
            # 筛选条件
            if event_type and entry.original_event.event_type != event_type:
                continue
            if max_age_seconds and entry.age_seconds > max_age_seconds:
                continue

            to_replay.append(entry_id)

        count = 0
        for entry_id in to_replay:
            if self.replay(entry_id):
                count += 1

        logger.info(f"[DeadLetterQueue] 批量重播完成: {count}/{len(to_replay)} 个事件")
        return count

    # ========== 管理操作 ==========

    def resolve_manually(self, entry_id: str, resolution: str, resolved_by: str) -> bool:
        """
        手动解决死信

        用于人工干预后标记为已处理
        """
        entry = self._entries.get(entry_id)
        if not entry:
            return False

        logger.info(
            f"[DeadLetterQueue] 手动解决: {entry_id} "
            f"(resolution={resolution}, by={resolved_by})"
        )

        entry.metadata["resolved"] = True
        entry.metadata["resolution"] = resolution
        entry.metadata["resolved_by"] = resolved_by
        entry.metadata["resolved_at"] = datetime.now().isoformat()

        self._stats["manually_resolved"] += 1

        # 解决后从队列移除
        self.remove(entry_id)

        return True

    def cleanup_expired(self) -> int:
        """清理过期条目"""
        now = time.time()
        expired = [
            entry_id
            for entry_id, entry in self._entries.items()
            if entry.age_seconds > self._retention_seconds
        ]

        for entry_id in expired:
            del self._entries[entry_id]

        self._stats["expired"] += len(expired)

        if expired:
            logger.info(f"[DeadLetterQueue] 清理过期条目: {len(expired)} 个")

        return len(expired)

    # ========== 查询 ==========

    def get_all_entries(self) -> list[DeadLetterEntry]:
        """获取所有条目"""
        return list(self._entries.values())

    def get_entries_by_reason(self, reason: DeadLetterReason) -> list[DeadLetterEntry]:
        """按原因筛选"""
        return [e for e in self._entries.values() if e.reason == reason]

    def get_entries_by_event_type(self, event_type: str) -> list[DeadLetterEntry]:
        """按事件类型筛选"""
        return [e for e in self._entries.values() if e.original_event.event_type == event_type]

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        by_reason = {}
        for entry in self._entries.values():
            reason = entry.reason.value
            by_reason[reason] = by_reason.get(reason, 0) + 1

        return {
            "current_size": len(self._entries),
            "max_size": self._max_size,
            **self._stats,
            "by_reason": by_reason,
            "oldest_entry_age_hours": (
                min(e.age_seconds for e in self._entries.values()) / 3600 if self._entries else 0
            ),
        }

    # ========== 回调注册 ==========

    def on_alert(self, callback: Callable[[DeadLetterEntry], None]):
        """注册告警回调"""
        self._alert_callbacks.append(callback)

    def on_replay(self, callback: Callable[[NeuroEvent], None]):
        """注册重播回调"""
        self._replay_callbacks.append(callback)

    def _trigger_alert(self, entry: DeadLetterEntry):
        """触发告警"""
        for callback in self._alert_callbacks:
            try:
                callback(entry)
            except Exception as e:
                logger.error(f"[DeadLetterQueue] 告警回调失败: {e}")

    # ========== 内部方法 ==========

    def _evict_oldest(self):
        """驱逐最老的条目"""
        if not self._entries:
            return

        oldest = min(self._entries.values(), key=lambda e: e.first_failure_time)
        del self._entries[oldest.entry_id]
        logger.warning(f"[DeadLetterQueue] 驱逐最老条目: {oldest.entry_id}")


# ========== 与 NeuroBus 集成 ==========


class NeuroBusDLQIntegration:
    """
    NeuroBus 与死信队列的集成

    自动将处理失败的事件转入 DLQ
    """

    def __init__(self, dlq: DeadLetterQueue | None = None):
        self._dlq = dlq or DeadLetterQueue()
        self._max_retries = 3

    @property
    def dlq(self) -> DeadLetterQueue:
        return self._dlq

    def handle_failure(
        self,
        event: NeuroEvent,
        error: Exception,
        retry_count: int,
        handler_name: str | None = None,
    ) -> str:
        """
        处理失败，决定进入死信队列

        Returns:
            死信条目 ID
        """
        # 判断原因
        if retry_count >= self._max_retries:
            reason = DeadLetterReason.RETRY_EXHAUSTED
        elif isinstance(error, (TimeoutError, asyncio.TimeoutError)):
            reason = DeadLetterReason.TIMEOUT
        elif isinstance(error, ValueError):
            reason = DeadLetterReason.INVALID_PAYLOAD
        else:
            reason = DeadLetterReason.UNRECOVERABLE

        import traceback

        error_stack = traceback.format_exc()

        return self._dlq.enqueue(
            event=event,
            reason=reason,
            error_message=str(error),
            retry_count=retry_count,
            handler_name=handler_name,
            error_stack=error_stack,
        )

    def setup_replay_to_bus(self, bus):
        """设置重播到 NeuroBus"""

        def replay_callback(event: NeuroEvent):
            bus.publish(event)

        self._dlq.on_replay(replay_callback)


# 全局 DLQ 实例
_dlq_instance: DeadLetterQueue | None = None


def get_dead_letter_queue() -> DeadLetterQueue:
    """获取全局死信队列实例"""
    global _dlq_instance
    if _dlq_instance is None:
        _dlq_instance = DeadLetterQueue()
    return _dlq_instance


# 快捷函数


def enqueue_dead_letter(
    event: NeuroEvent,
    reason: str,
    error_message: str,
    retry_count: int = 0,
) -> str:
    """快捷函数：将事件加入死信队列"""
    dlq = get_dead_letter_queue()

    reason_enum = DeadLetterReason.UNRECOVERABLE
    try:
        reason_enum = DeadLetterReason(reason)
    except ValueError:
        pass

    return dlq.enqueue(
        event=event,
        reason=reason_enum,
        error_message=error_message,
        retry_count=retry_count,
    )


def get_dlq_stats() -> dict[str, Any]:
    """获取死信队列统计"""
    return get_dead_letter_queue().get_stats()
