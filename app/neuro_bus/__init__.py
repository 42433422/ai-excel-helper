"""
NeuroBus - 神经总线系统

提供事件驱动的神经架构支持，包含8大可靠性机制：
- 去重器（Deduplicator）
- 链路追踪器（Tracer）
- 动态限流器（Rate Limiter）
- 熔断保护器（Circuit Breaker）
- SLA 超时控制
- 错误反馈与重试
- 沙盒预演（Sandbox）
- 保命通道（Lifeline）

Level 4 新增可靠性机制：
- 死信队列（Dead Letter Queue）
- 事件存储与重播（Event Store & Replay）
- 健康监控与告警（Health Monitor）
"""

from app.neuro_bus.bus import NeuroBus, get_neuro_bus

# Level 4 可靠性机制
from app.neuro_bus.dead_letter_queue import (
    DeadLetterEntry,
    DeadLetterQueue,
    DeadLetterReason,
    enqueue_dead_letter,
    get_dead_letter_queue,
)
from app.neuro_bus.event_store import (
    EventStore,
    EventStoreMode,
    StoredEvent,
    get_event_store,
    replay_events,
    store_event,
)
from app.neuro_bus.events.base import EventPriority, NeuroEvent
from app.neuro_bus.health_monitor import (
    Alert,
    AlertLevel,
    HealthCheckResult,
    HealthMonitor,
    HealthStatus,
    get_health,
    get_health_monitor,
    get_system_status,
)
from app.neuro_bus.initializer import (
    NeuroBusInitializer,
    get_initializer,
    initialize_neuro_bus,
    shutdown_neuro_bus,
)

__all__ = [
    # 核心
    "NeuroBus",
    "get_neuro_bus",
    "NeuroEvent",
    "EventPriority",
    # Level 4: 死信队列
    "DeadLetterQueue",
    "DeadLetterEntry",
    "DeadLetterReason",
    "get_dead_letter_queue",
    "enqueue_dead_letter",
    # Level 4: 事件存储
    "EventStore",
    "StoredEvent",
    "EventStoreMode",
    "get_event_store",
    "store_event",
    "replay_events",
    # Level 4: 健康监控
    "HealthMonitor",
    "HealthCheckResult",
    "HealthStatus",
    "Alert",
    "AlertLevel",
    "get_health_monitor",
    "get_health",
    "get_system_status",
    # Level 4: 初始化器
    "NeuroBusInitializer",
    "get_initializer",
    "initialize_neuro_bus",
    "shutdown_neuro_bus",
]
