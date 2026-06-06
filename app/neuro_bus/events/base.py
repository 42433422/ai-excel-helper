"""
神经事件基类

提供标准化的事件定义、优先级控制和元数据管理
"""

import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import IntEnum
from typing import Any


class EventPriority(IntEnum):
    """事件优先级 - 数值越小优先级越高"""

    CRITICAL = 0  # 紧急（系统级）
    HIGH = 1  # 高（用户核心操作）
    NORMAL = 2  # 普通（默认）
    LOW = 3  # 低（后台任务）
    BACKGROUND = 4  # 后台（日志、统计）


@dataclass
class EventMetadata:
    """事件元数据 - 用于链路追踪和监控"""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str | None = None
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    parent_span_id: str | None = None
    source: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    domain: str = "global"
    retry_count: int = 0
    max_retries: int = 3
    timeout_ms: int = 5000
    dedup_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "source": self.source,
            "timestamp": self.timestamp,
            "domain": self.domain,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout_ms": self.timeout_ms,
            "dedup_key": self.dedup_key,
        }


class NeuroEvent:
    """
    神经事件基类

    所有领域事件的基类，提供标准化的事件结构和行为
    """

    def __init__(
        self,
        event_type: str,
        payload: dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        metadata: EventMetadata | None = None,
        *,
        preserve_queue_identity: bool = False,
        **kwargs,
    ):
        self.event_type = event_type
        self.payload = payload
        self.priority = priority

        # 合并额外参数到 payload（须在生成 dedup_key 之前完成）
        self.payload.update(kwargs)

        if metadata is None:
            self.metadata = EventMetadata()
        elif preserve_queue_identity:
            self.metadata = metadata
        else:
            # 外部传入的 metadata 可能复用同一 event_id；入队会去重丢弃，导致 publish 失败或命令永远等不到回复
            self.metadata = replace(
                metadata,
                event_id=str(uuid.uuid4()),
                timestamp=time.time(),
                dedup_key=None,
            )

        if not self.metadata.dedup_key:
            self.metadata.dedup_key = self._generate_dedup_key()

    def remint_queue_identity(self) -> None:
        """为再次进入 NeuroBus 队列生成新的 event_id / 时间戳 / dedup_key。"""
        self.metadata = replace(
            self.metadata,
            event_id=str(uuid.uuid4()),
            timestamp=time.time(),
            dedup_key=None,
        )
        self.metadata.dedup_key = self._generate_dedup_key()

    def _generate_dedup_key(self) -> str:
        """生成去重键 - 基于事件类型和关键字段"""
        key_data = {
            "type": self.event_type,
            "payload_keys": sorted(self.payload.keys()),
            "timestamp": int(self.metadata.timestamp * 1000),  # 毫秒级
        }
        import hashlib

        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()[:32]

    def get_dedup_key(self) -> str:
        """获取去重键"""
        return self.metadata.dedup_key or self._generate_dedup_key()

    def with_trace(self, trace_id: str, span_id: str | None = None) -> "NeuroEvent":
        """添加链路追踪信息"""
        self.metadata.trace_id = trace_id
        if span_id:
            self.metadata.parent_span_id = self.metadata.span_id
            self.metadata.span_id = span_id
        return self

    def with_source(self, source: str) -> "NeuroEvent":
        """设置事件源"""
        self.metadata.source = source
        return self

    def with_domain(self, domain: str) -> "NeuroEvent":
        """设置领域"""
        self.metadata.domain = domain
        return self

    def with_timeout(self, timeout_ms: int) -> "NeuroEvent":
        """设置超时（毫秒）"""
        self.metadata.timeout_ms = timeout_ms
        return self

    def is_expired(self) -> bool:
        """检查事件是否已超时"""
        elapsed_ms = (time.time() - self.metadata.timestamp) * 1000
        return elapsed_ms > self.metadata.timeout_ms

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        return {
            "event_type": self.event_type,
            "priority": self.priority.value,
            "metadata": self.metadata.to_dict(),
            "payload": self.payload,
        }

    def to_json(self) -> str:
        """序列化为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], *, preserve_queue_identity: bool = False
    ) -> "NeuroEvent":
        """从字典反序列化。默认重新分配 event_id，便于再次 publish；审计/对账可设 preserve_queue_identity=True。"""
        metadata = EventMetadata(**data.get("metadata", {}))
        return cls(
            event_type=data["event_type"],
            payload=data.get("payload", {}),
            priority=EventPriority(data.get("priority", 2)),
            metadata=metadata,
            preserve_queue_identity=preserve_queue_identity,
        )

    def __repr__(self) -> str:
        return f"NeuroEvent({self.event_type}, priority={self.priority.name}, domain={self.metadata.domain})"

    def __lt__(self, other: "NeuroEvent") -> bool:
        """用于优先级队列排序"""
        if not isinstance(other, NeuroEvent):
            return NotImplemented
        # 优先级数值小的排在前面
        return self.priority.value < other.priority.value


class DomainEvent(NeuroEvent):
    """
    领域事件 - 特定于业务领域的事件

    用于跨聚合、跨领域的通信
    """

    def __init__(
        self,
        domain: str,
        event_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
        version: int = 1,
        **kwargs,
    ):
        super().__init__(event_type=f"{domain}.{event_type}", payload=payload, **kwargs)
        self.metadata.domain = domain
        self.aggregate_id = aggregate_id
        self.version = version
        self.payload["_aggregate_id"] = aggregate_id
        self.payload["_version"] = version


class IntentEvent(NeuroEvent):
    """
    意图事件 - 用户意图识别相关事件

    用于意图处理流程中的事件传递
    """

    INTENT_RECOGNIZED = "intent.recognized"
    INTENT_PROCESSING = "intent.processing"
    INTENT_COMPLETED = "intent.completed"
    INTENT_FAILED = "intent.failed"
    INTENT_REFLEX_TRIGGERED = "intent.reflex_triggered"

    def __init__(
        self,
        intent_type: str,
        user_id: str,
        confidence: float,
        raw_text: str,
        event_subtype: str = INTENT_RECOGNIZED,
        priority: EventPriority = EventPriority.HIGH,
        **kwargs,
    ):
        super().__init__(
            event_type=event_subtype,
            payload={
                "intent_type": intent_type,
                "user_id": user_id,
                "confidence": confidence,
                "raw_text": raw_text,
                **kwargs,
            },
            priority=priority,
        )
        self.metadata.domain = "intent"
        self.metadata.timeout_ms = self._get_timeout_for_intent(intent_type)

    def _get_timeout_for_intent(self, intent_type: str) -> int:
        """根据意图类型返回超时配置"""
        # Reflex 级意图 < 1ms
        reflex_intents = ["greeting", "emergency_stop", "confirm", "deny"]
        if intent_type in reflex_intents:
            return 1
        # 潜意识级 < 10ms
        subconscious_intents = ["help", "status_check"]
        if intent_type in subconscious_intents:
            return 10
        # 默认显意识级 < 200ms
        return 200


# 事件处理器类型定义
EventHandler = Callable[[NeuroEvent], Any]
AsyncEventHandler = Callable[[NeuroEvent], Any]  # Coroutine
