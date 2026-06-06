"""
链路追踪器（Tracer）

提供跨领域的链路追踪，类似 OpenTelemetry 的 span 模型
支持分布式追踪和性能分析
"""

import logging
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.neuro_bus.events.base import NeuroEvent

logger = logging.getLogger(__name__)


class SpanStatus(Enum):
    """Span 状态"""

    OK = "ok"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class Span:
    """
    追踪 Span

    表示一个操作单元，包含时间、标签和事件
    """

    span_id: str
    trace_id: str
    parent_id: str | None
    name: str
    start_time: float
    end_time: float | None = None
    status: SpanStatus = SpanStatus.OK
    tags: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.span_id:
            self.span_id = str(uuid.uuid4())[:16]

    def finish(self, status: SpanStatus = SpanStatus.OK):
        """完成 Span"""
        self.end_time = time.time()
        self.status = status

    def add_event(self, name: str, attributes: dict[str, Any] | None = None):
        """添加事件"""
        self.events.append(
            {
                "name": name,
                "timestamp": time.time(),
                "attributes": attributes or {},
            }
        )

    def set_tag(self, key: str, value: Any):
        """设置标签"""
        self.tags[key] = value

    @property
    def duration_ms(self) -> float | None:
        """获取持续时间（毫秒）"""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "tags": self.tags,
            "events": self.events,
        }


# 当前追踪上下文
current_trace: ContextVar[str | None] = ContextVar("current_trace", default=None)
current_span: ContextVar[str | None] = ContextVar("current_span", default=None)


class TraceContext:
    """
    追踪上下文管理器

    用于手动管理追踪上下文
    """

    def __init__(self, trace_id: str | None = None, span_id: str | None = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.span_id = span_id or str(uuid.uuid4())[:16]
        self._token_trace = None
        self._token_span = None

    def __enter__(self):
        self._token_trace = current_trace.set(self.trace_id)
        self._token_span = current_span.set(self.span_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token_trace:
            current_trace.reset(self._token_trace)
        if self._token_span:
            current_span.reset(self._token_span)


class NeuroTracer:
    """
    神经链路追踪器

    提供：
    - 自动 span 创建
    - 跨领域追踪传播
    - 性能分析数据
    """

    def __init__(self, max_spans: int = 10000):
        self._spans: dict[str, Span] = {}
        self._trace_roots: dict[str, str] = {}  # trace_id -> root_span_id
        self._max_spans = max_spans

    def start_span(
        self,
        name: str,
        trace_id: str | None = None,
        parent_id: str | None = None,
        tags: dict[str, Any] | None = None,
    ) -> Span:
        """
        开始一个新的 Span
        """
        # 从上下文获取 trace_id
        if not trace_id:
            trace_id = current_trace.get() or str(uuid.uuid4())

        # 从上下文获取 parent_id
        if not parent_id:
            parent_id = current_span.get()

        span = Span(
            span_id=str(uuid.uuid4())[:16],
            trace_id=trace_id,
            parent_id=parent_id,
            name=name,
            start_time=time.time(),
            tags=tags or {},
        )

        # 记录根 span
        if not parent_id:
            self._trace_roots[trace_id] = span.span_id

        # 存储
        self._spans[span.span_id] = span

        # 设置当前上下文
        current_trace.set(trace_id)
        current_span.set(span.span_id)

        # 容量控制
        if len(self._spans) > self._max_spans:
            self._cleanup_old_spans()

        return span

    def end_span(self, span_id: str, status: SpanStatus = SpanStatus.OK):
        """结束 Span"""
        if span_id in self._spans:
            self._spans[span_id].finish(status)

    def get_span(self, span_id: str) -> Span | None:
        """获取 Span"""
        return self._spans.get(span_id)

    def get_trace(self, trace_id: str) -> list[Span]:
        """获取完整追踪链"""
        return [span for span in self._spans.values() if span.trace_id == trace_id]

    def trace_event(self, event: NeuroEvent, operation: str) -> Span:
        """
        追踪事件处理

        自动从事件元数据提取 trace 信息
        """
        span = self.start_span(
            name=f"{event.event_type}.{operation}",
            trace_id=event.metadata.trace_id,
            parent_id=event.metadata.span_id,
            tags={
                "event_type": event.event_type,
                "domain": event.metadata.domain,
                "priority": event.priority.name,
            },
        )

        # 更新事件的 trace 信息
        event.metadata.trace_id = span.trace_id
        event.metadata.parent_span_id = span.parent_id
        event.metadata.span_id = span.span_id

        return span

    def inject_trace_context(self, event: NeuroEvent) -> NeuroEvent:
        """
        注入追踪上下文到事件

        用于跨服务/领域传播
        """
        trace_id = current_trace.get()
        span_id = current_span.get()

        if trace_id:
            event.metadata.trace_id = trace_id
        if span_id:
            event.metadata.parent_span_id = span_id
            # 生成新的 span_id
            event.metadata.span_id = str(uuid.uuid4())[:8]

        return event

    def get_current_trace_id(self) -> str | None:
        """获取当前 trace_id"""
        return current_trace.get()

    def get_current_span_id(self) -> str | None:
        """获取当前 span_id"""
        return current_span.get()

    def _cleanup_old_spans(self):
        """清理旧的 span"""
        # 按开始时间排序，删除最老的 20%
        sorted_spans = sorted(self._spans.items(), key=lambda x: x[1].start_time)
        to_remove = int(len(sorted_spans) * 0.2)

        for span_id, _ in sorted_spans[:to_remove]:
            del self._spans[span_id]

    def get_stats(self) -> dict[str, Any]:
        """获取统计"""
        active_spans = sum(1 for s in self._spans.values() if not s.end_time)
        return {
            "total_spans": len(self._spans),
            "active_spans": active_spans,
            "completed_spans": len(self._spans) - active_spans,
            "traces": len(self._trace_roots),
        }


# 装饰器


def traced(name: str | None = None, tags: dict[str, Any] | None = None):
    """
    追踪装饰器

    用法:
        @traced("process_order")
        async def process_order(order_id: str):
            pass
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            tracer = NeuroTracer()
            span_name = name or func.__name__
            span = tracer.start_span(span_name, tags=tags)

            try:
                result = await func(*args, **kwargs)
                span.finish(SpanStatus.OK)
                return result
            except Exception as e:
                span.finish(SpanStatus.ERROR)
                span.set_tag("error", str(e))
                raise

        return wrapper

    return decorator
