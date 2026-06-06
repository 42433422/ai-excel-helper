"""
NeuroBus - 神经总线核心实现

提供高性能的异步事件总线，支持：
- 发布/订阅模式
- 优先级队列（5级优先级）
- 同步/异步处理器
- 事件持久化与回放
- 领域隔离
"""

import asyncio
import logging
import os
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from heapq import heappop, heappush
from typing import Any

from app.neuro_bus.events.base import AsyncEventHandler, EventHandler, NeuroEvent

logger = logging.getLogger(__name__)


def _neuro_env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _deployment_is_staging() -> bool:
    """k8s/CI：设置 FHD_ENV=staging；与本仓库 staging 部署约定一致。"""
    return os.environ.get("FHD_ENV", "").strip().lower() == "staging"


def _neuro_trace_sample_rate() -> float:
    """生产 trace 采样率，避免洪泛。XCAGI_NEURO_BUS_TRACE_SAMPLE_RATE 默认 0.1。"""
    raw = os.environ.get("XCAGI_NEURO_BUS_TRACE_SAMPLE_RATE", "0.1").strip()
    try:
        rate = float(raw)
    except ValueError:
        rate = 0.1
    return max(0.0, min(1.0, rate))


def _should_trace_event() -> bool:
    """未启用 tracer 时忽略；启用后按采样率决定是否记录 span。"""
    rate = _neuro_trace_sample_rate()
    if rate >= 1.0:
        return True
    if rate <= 0.0:
        return False
    import random

    return random.random() < rate


def _neuro_reliability_wanted(env_name: str, *, staging_default: bool) -> bool:
    """
    可靠性层开关：显式设置环境变量时以变量为准；未设置时在 staging 采用默认值（默认可关）。
    """
    raw = os.environ.get(env_name)
    if raw is not None and str(raw).strip() != "":
        return _neuro_env_flag(env_name)
    if _deployment_is_staging():
        return staging_default
    return False


class HandlerSubscription:
    """处理器订阅信息"""

    def __init__(
        self,
        event_type: str,
        handler: EventHandler | AsyncEventHandler,
        priority: int = 0,
        is_async: bool = True,
        filter_fn: Callable[[NeuroEvent], bool] | None = None,
    ):
        self.event_type = event_type
        self.handler = handler
        self.priority = priority
        self.is_async = is_async
        self.filter_fn = filter_fn
        self.created_at = time.time()
        self.call_count = 0
        self.error_count = 0

    def should_handle(self, event: NeuroEvent) -> bool:
        """检查是否应该处理该事件"""
        if self.filter_fn:
            return self.filter_fn(event)
        return True

    def record_call(self, success: bool = True):
        """记录调用统计"""
        self.call_count += 1
        if not success:
            self.error_count += 1

    @property
    def error_rate(self) -> float:
        """计算错误率"""
        if self.call_count == 0:
            return 0.0
        return self.error_count / self.call_count


class PriorityEventQueue:
    """
    优先级事件队列

    使用堆实现的高效优先级队列
    """

    def __init__(self, max_size: int = 10000):
        self._queue: list[tuple] = []  # (priority, timestamp, event_id, event)
        self._event_ids: set[str] = set()
        self._max_size = max_size
        self._lock = threading.RLock()
        self._dropped_count = 0

    def put(self, event: NeuroEvent) -> bool:
        """
        放入事件

        Returns:
            是否成功放入（队列满时丢弃低优先级事件）
        """
        with self._lock:
            # 同一 event_id 已在队列中则无法入队；自动 remint 避免静默丢件导致上游阻塞
            for attempt in range(4):
                if event.metadata.event_id not in self._event_ids:
                    break
                if attempt == 3:
                    logger.error(
                        "NeuroBus: event_id %s still conflicts after remint; dropping",
                        event.metadata.event_id,
                    )
                    self._dropped_count += 1
                    return False
                logger.warning(
                    "NeuroBus: duplicate event_id %s in queue; reminting (attempt %s)",
                    event.metadata.event_id,
                    attempt + 1,
                )
                event.remint_queue_identity()

            # 队列满时处理
            if len(self._queue) >= self._max_size:
                # 如果新事件优先级比队列中最低的高，则替换
                if self._queue and event.priority.value < self._queue[0][0]:
                    _, _, _, old_event = heappop(self._queue)
                    self._event_ids.discard(old_event.metadata.event_id)
                    self._dropped_count += 1
                    logger.warning(f"Dropped low priority event due to queue full: {old_event}")
                else:
                    self._dropped_count += 1
                    logger.warning(f"Queue full, dropping event: {event}")
                    return False

            # 放入队列 (优先级数值小的在前)
            heappush(
                self._queue,
                (event.priority.value, event.metadata.timestamp, event.metadata.event_id, event),
            )
            self._event_ids.add(event.metadata.event_id)
            return True

    def get(self) -> NeuroEvent | None:
        """取出最高优先级事件"""
        with self._lock:
            if not self._queue:
                return None
            _, _, event_id, event = heappop(self._queue)
            self._event_ids.discard(event_id)
            return event

    def peek(self) -> NeuroEvent | None:
        """查看最高优先级事件（不取出）"""
        with self._lock:
            if not self._queue:
                return None
            return self._queue[0][3]

    def size(self) -> int:
        """队列大小"""
        with self._lock:
            return len(self._queue)

    def clear(self):
        """清空队列"""
        with self._lock:
            self._queue.clear()
            self._event_ids.clear()


class NeuroBus:
    """
    神经总线 - 高性能事件总线实现

    特性：
    - 多优先级事件队列
    - 同步/异步处理器支持
    - 领域隔离
    - 事件过滤
    - 处理器统计
    """

    def __init__(
        self,
        max_queue_size: int = 10000,
        worker_threads: int = 4,
        enable_metrics: bool = True,
    ):
        self._event_queue = PriorityEventQueue(max_size=max_queue_size)
        self._handlers: dict[str, list[HandlerSubscription]] = defaultdict(list)
        self._domain_handlers: dict[str, dict[str, list[HandlerSubscription]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._global_handlers: list[HandlerSubscription] = []

        # 执行器
        self._executor = ThreadPoolExecutor(
            max_workers=worker_threads, thread_name_prefix="neurobus_"
        )
        self._loop: asyncio.AbstractEventLoop | None = None

        # 运行状态
        self._running = False
        self._shutdown = False
        self._processing_task: asyncio.Task | None = None

        # 统计
        self._enable_metrics = enable_metrics
        self._published_count = 0
        self._processed_count = 0
        self._error_count = 0
        self._dropped_count = 0
        # Event to signal new items in the queue; created when start() runs on the event loop.
        self._event_available: asyncio.Event | None = None

        # 事件持久化（可选）
        self._event_buffer: list[dict[str, Any]] = []
        self._enable_persistence = False

        # 可选可靠性层：未设环境变量时，FHD_ENV=staging 默认开启 DEDUP+CIRCUIT；其余见 .env.example
        self._rel_dedup = None
        self._rel_rate = None
        self._rel_circuit = None
        self._rel_lifeline = None
        self._rel_tracer = None
        self._rel_sla_log = _neuro_env_flag("XCAGI_NEURO_BUS_SLA_LOG")
        self._trace_by_event_id: dict[str, str] = {}
        if _neuro_reliability_wanted("XCAGI_NEURO_BUS_DEDUP", staging_default=True):
            from app.neuro_bus.deduplicator import EventDeduplicator

            self._rel_dedup = EventDeduplicator()
        if _neuro_reliability_wanted("XCAGI_NEURO_BUS_RATE_LIMIT", staging_default=False):
            from app.neuro_bus.rate_limiter import NeuroRateLimiter

            self._rel_rate = NeuroRateLimiter()
        if _neuro_reliability_wanted("XCAGI_NEURO_BUS_CIRCUIT", staging_default=True):
            from app.neuro_bus.circuit_breaker import CircuitBreaker

            self._rel_circuit = CircuitBreaker("neuro_dispatch")
        if _neuro_reliability_wanted("XCAGI_NEURO_BUS_LIFELINE", staging_default=False):
            from app.neuro_bus.lifeline import Lifeline

            self._rel_lifeline = Lifeline()
        if _neuro_reliability_wanted("XCAGI_NEURO_BUS_TRACE", staging_default=False):
            from app.neuro_bus.tracer import NeuroTracer

            self._rel_tracer = NeuroTracer()

        # handler 异常时自动写入全局 DLQ（与 initializer 中 DLQ 实例一致）
        self._dlq_integration = None
        if _neuro_reliability_wanted("XCAGI_NEURO_BUS_DLQ_AUTO", staging_default=False):
            from app.neuro_bus.dead_letter_queue import (
                NeuroBusDLQIntegration,
                get_dead_letter_queue,
            )

            self._dlq_integration = NeuroBusDLQIntegration(get_dead_letter_queue())

        logger.info("NeuroBus initialized")

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self):
        """启动总线"""
        if self._running:
            return

        self._running = True
        self._shutdown = False
        self._loop = asyncio.get_running_loop()
        # create an Event bound to the running loop to avoid loop-less creation errors
        self._event_available = asyncio.Event()

        # 启动事件处理循环
        self._processing_task = asyncio.create_task(self._processing_loop())

        logger.info("NeuroBus started")

    async def stop(self):
        """停止总线"""
        if not self._running:
            return

        self._shutdown = True
        self._running = False

        # 取消处理任务
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        # 关闭线程池
        self._executor.shutdown(wait=True)
        # Wake processing loop if waiting on the event
        if getattr(self, "_event_available", None):
            try:
                self._event_available.set()
            except Exception:
                pass

        logger.info("NeuroBus stopped")

    async def _processing_loop(self):
        """事件处理主循环"""
        while not self._shutdown:
            try:
                # 获取事件
                event = self._event_queue.get()

                if event is None:
                    # 队列为空：优先等待由 publish() 设置的 Event，避免忙轮询
                    ev = getattr(self, "_event_available", None)
                    if ev is not None:
                        # clear then wait with a timeout to periodically check _shutdown
                        ev.clear()
                        try:
                            await asyncio.wait_for(ev.wait(), timeout=1.0)
                        except asyncio.TimeoutError:
                            pass
                    else:
                        # fallback: tiny sleep if no event available
                        await asyncio.sleep(0.001)
                    continue

                # 检查超时
                if event.is_expired():
                    logger.warning(f"Event expired: {event}")
                    self._dropped_count += 1
                    continue

                # 分发事件
                await self._dispatch_event(event)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in processing loop: {e}")
                self._error_count += 1

    async def _dispatch_event(self, event: NeuroEvent):
        """分发事件到处理器"""
        handlers_called = 0
        any_failed = False

        # 1. 特定类型处理器
        event_type = event.event_type
        if event_type in self._handlers:
            for subscription in self._handlers[event_type]:
                if subscription.should_handle(event):
                    ok = await self._call_handler(subscription, event)
                    handlers_called += 1
                    if not ok:
                        any_failed = True

        # 2. 领域特定处理器
        domain = event.metadata.domain
        if domain and domain in self._domain_handlers:
            domain_handlers = self._domain_handlers[domain]
            if event_type in domain_handlers:
                for subscription in domain_handlers[event_type]:
                    if subscription.should_handle(event):
                        ok = await self._call_handler(subscription, event)
                        handlers_called += 1
                        if not ok:
                            any_failed = True

        # 3. 全局处理器（监听所有事件）
        for subscription in self._global_handlers:
            if subscription.should_handle(event):
                ok = await self._call_handler(subscription, event)
                handlers_called += 1
                if not ok:
                    any_failed = True

        if handlers_called == 0:
            logger.debug(f"No handlers for event: {event}")

        self._processed_count += 1

        if self._rel_dedup is not None:
            if any_failed:
                self._rel_dedup.remove(event)
            else:
                self._rel_dedup.mark_processed(event)

        eid = event.metadata.event_id
        sid = self._trace_by_event_id.pop(eid, None)
        if sid and self._rel_tracer is not None:
            from app.neuro_bus.tracer import SpanStatus

            self._rel_tracer.end_span(sid, SpanStatus.ERROR if any_failed else SpanStatus.OK)

    async def _call_handler(self, subscription: HandlerSubscription, event: NeuroEvent) -> bool:
        """调用处理器；返回是否成功（无异常）。"""
        if self._rel_circuit is not None and not self._rel_circuit.can_execute():
            logger.warning("NeuroBus circuit open; skipping handler for %s", event.event_type)
            return False
        t0 = time.perf_counter()
        try:
            if subscription.is_async:
                await subscription.handler(event)
            else:
                await asyncio.get_running_loop().run_in_executor(
                    self._executor, subscription.handler, event
                )
            subscription.record_call(success=True)
            if self._rel_circuit is not None:
                self._rel_circuit.record_success()

        except Exception as e:
            logger.exception(f"Handler error for event {event}: {e}")
            subscription.record_call(success=False)
            self._error_count += 1
            if self._rel_circuit is not None:
                self._rel_circuit.record_failure()
            if self._dlq_integration is not None:
                try:
                    self._dlq_integration.handle_failure(
                        event,
                        e,
                        retry_count=0,
                        handler_name=getattr(subscription.handler, "__name__", None),
                    )
                except Exception as dlq_exc:
                    logger.exception("NeuroBus DLQ enqueue failed: %s", dlq_exc)
            return False
        finally:
            if self._rel_sla_log:
                from app.neuro_bus.sla_controller import SLAConfig

                elapsed_ms = (time.perf_counter() - t0) * 1000
                if elapsed_ms > SLAConfig.CONSCIOUS.warning_threshold_ms:
                    logger.warning(
                        "NeuroBus handler SLA slow: event=%s handler=%s %.1fms",
                        event.event_type,
                        getattr(subscription.handler, "__name__", "handler"),
                        elapsed_ms,
                    )
        return True

    def _preflight_publish(self, event: NeuroEvent) -> bool:
        if self._rel_dedup is not None:
            if not self._rel_dedup.mark_processing(event):
                return False
        if self._rel_rate is not None:
            if not self._rel_rate.check_rate(event):
                if self._rel_dedup is not None:
                    self._rel_dedup.remove(event)
                return False
        if self._rel_lifeline is not None:
            qd = self._event_queue.size()
            if not self._rel_lifeline.should_process(event, qd):
                if self._rel_dedup is not None:
                    self._rel_dedup.remove(event)
                return False
        return True

    def publish(self, event: NeuroEvent) -> bool:
        """
        发布事件

        Returns:
            是否成功加入队列
        """
        if not self._running or self._shutdown:
            logger.warning("Cannot publish: NeuroBus not running")
            return False

        if not self._preflight_publish(event):
            return False

        # 持久化（如果启用）
        if self._enable_persistence:
            self._event_buffer.append(event.to_dict())

        span_id = None
        if self._rel_tracer is not None and _should_trace_event():
            sp = self._rel_tracer.start_span(
                f"neuro.publish:{event.event_type}",
                tags={
                    "event_type": event.event_type,
                    "event_id": event.metadata.event_id,
                },
            )
            span_id = sp.span_id
            self._trace_by_event_id[event.metadata.event_id] = span_id

        success = self._event_queue.put(event)
        if success:
            self._published_count += 1
            # wake processing loop if it's waiting
            ev = getattr(self, "_event_available", None)
            if ev is not None:
                try:
                    ev.set()
                except Exception:
                    # ignore any loop-related errors
                    pass
        else:
            if self._rel_dedup is not None:
                self._rel_dedup.remove(event)
            if span_id is not None and self._rel_tracer is not None:
                from app.neuro_bus.tracer import SpanStatus

                self._rel_tracer.end_span(span_id, SpanStatus.ERROR)
                self._trace_by_event_id.pop(event.metadata.event_id, None)

        return success

    def subscribe(
        self,
        event_type: str,
        handler: EventHandler | AsyncEventHandler,
        priority: int = 0,
        is_async: bool = True,
        filter_fn: Callable[[NeuroEvent], bool] | None = None,
    ) -> HandlerSubscription:
        """
        订阅特定类型事件

        Args:
            event_type: 事件类型
            handler: 处理器函数
            priority: 处理器优先级（数值小的先执行）
            is_async: 是否为异步处理器
            filter_fn: 可选的过滤函数

        Returns:
            订阅对象
        """
        subscription = HandlerSubscription(
            event_type=event_type,
            handler=handler,
            priority=priority,
            is_async=is_async,
            filter_fn=filter_fn,
        )

        self._handlers[event_type].append(subscription)

        # 按优先级排序
        self._handlers[event_type].sort(key=lambda s: s.priority)

        logger.debug(f"Subscribed to {event_type}: {handler.__name__}")
        return subscription

    def subscribe_to_domain(
        self,
        domain: str,
        event_type: str,
        handler: EventHandler | AsyncEventHandler,
        priority: int = 0,
        is_async: bool = True,
    ) -> HandlerSubscription:
        """订阅特定领域的事件"""
        subscription = HandlerSubscription(
            event_type=event_type,
            handler=handler,
            priority=priority,
            is_async=is_async,
        )

        self._domain_handlers[domain][event_type].append(subscription)
        self._domain_handlers[domain][event_type].sort(key=lambda s: s.priority)

        logger.debug(f"Subscribed to {domain}.{event_type}: {handler.__name__}")
        return subscription

    def subscribe_all(
        self,
        handler: EventHandler | AsyncEventHandler,
        filter_fn: Callable[[NeuroEvent], bool] | None = None,
    ) -> HandlerSubscription:
        """订阅所有事件（全局处理器）"""
        subscription = HandlerSubscription(
            event_type="*",
            handler=handler,
            filter_fn=filter_fn,
        )

        self._global_handlers.append(subscription)
        logger.debug(f"Global subscription: {handler.__name__}")
        return subscription

    def unsubscribe(self, subscription: HandlerSubscription) -> bool:
        """取消订阅"""
        if subscription.event_type in self._handlers:
            if subscription in self._handlers[subscription.event_type]:
                self._handlers[subscription.event_type].remove(subscription)
                return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """获取总线统计信息"""
        return {
            "published": self._published_count,
            "processed": self._processed_count,
            "errors": self._error_count,
            "dropped": self._dropped_count,
            "queue_size": self._event_queue.size(),
            "handlers": sum(len(h) for h in self._handlers.values()),
            "global_handlers": len(self._global_handlers),
            "running": self._running,
            "reliability": self.get_reliability_status(),
        }

    def get_reliability_status(self) -> dict[str, Any]:
        """总线级可靠性层是否启用（与 /api/neurobus 诊断一致）。"""
        out: dict[str, Any] = {
            "fhd_env": os.environ.get("FHD_ENV", ""),
            "dedup": self._rel_dedup is not None,
            "rate_limit": self._rel_rate is not None,
            "circuit_breaker": self._rel_circuit is not None,
            "lifeline": self._rel_lifeline is not None,
            "tracer": self._rel_tracer is not None,
            "sla_log": self._rel_sla_log,
            "dlq_auto": self._dlq_integration is not None,
            "trace_sample_rate": (
                _neuro_trace_sample_rate() if self._rel_tracer is not None else None
            ),
        }
        if self._rel_circuit is not None:
            try:
                out["circuit_open"] = not self._rel_circuit.can_execute()
            except Exception:
                out["circuit_open"] = None
        return out

    def summarize_subscriptions(self) -> dict[str, Any]:
        """Startup diagnostics: handler counts per event type (flat + per-domain)."""
        flat = {k: len(v) for k, v in sorted(self._handlers.items())}
        domain_nested: dict[str, dict[str, int]] = {}
        for d, evs in self._domain_handlers.items():
            domain_nested[d] = {e: len(subs) for e, subs in sorted(evs.items())}
        return {
            "flat_event_handlers": flat,
            "domain_handlers": domain_nested,
            "global_handlers": len(self._global_handlers),
        }

    @property
    def registered_domains(self) -> list[str]:
        """已注册神经域名称（来自 DomainRegistry，供启动日志与健康检查）。"""
        try:
            from app.neuro_bus.domains.base import get_domain_registry

            return get_domain_registry().list_domains()
        except Exception:
            return []


# 全局 NeuroBus 实例
_neuro_bus: NeuroBus | None = None
_neuro_bus_lock = threading.Lock()


def get_neuro_bus() -> NeuroBus:
    global _neuro_bus
    if _neuro_bus is None:
        with _neuro_bus_lock:
            if _neuro_bus is None:
                _neuro_bus = NeuroBus()
    return _neuro_bus


def set_neuro_bus(bus: NeuroBus):
    """设置全局 NeuroBus 实例"""
    global _neuro_bus
    _neuro_bus = bus
