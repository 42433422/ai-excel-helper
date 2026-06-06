"""
潜意识处理器（SubconsciousProcessor）

<10ms 响应目标
- 后台异步处理
- 日志记录
- 统计更新
- 非关键通知
- 批量处理优化
"""

import asyncio
import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.neuro_bus.bus import NeuroBus, get_neuro_bus
from app.neuro_bus.events.base import NeuroEvent

logger = logging.getLogger(__name__)


@dataclass
class BatchBuffer:
    """批量缓冲"""

    events: list[NeuroEvent]
    max_size: int
    max_wait_ms: float
    created_at: float


class SubconsciousProcessor:
    """
    潜意识处理器

    用于：
    - 日志记录
    - 使用统计
    - 非关键通知
    - 缓存预热
    - 数据同步

    SLA: < 10ms
    """

    SLA_TARGET_MS = 10.0
    SLA_MAX_MS = 50.0

    def __init__(
        self,
        bus: NeuroBus | None = None,
        enable_batching: bool = True,
        batch_size: int = 10,
        batch_wait_ms: float = 5.0,
    ):
        self._bus = bus or get_neuro_bus()

        # 批处理配置
        self._enable_batching = enable_batching
        self._batch_size = batch_size
        self._batch_wait_ms = batch_wait_ms
        self._batches: dict[str, BatchBuffer] = {}

        # 处理器注册
        self._handlers: dict[str, Callable[[NeuroEvent], Any]] = {}
        self._batch_handlers: dict[str, Callable[[list[NeuroEvent]], Any]] = {}

        # 统计
        self._processed_count = 0
        self._batched_count = 0
        self._error_count = 0
        self._timeout_count = 0

        # 运行状态
        self._running = False
        self._flush_task: asyncio.Task | None = None

        # 性能监控
        self._latency_history: deque = deque(maxlen=1000)

    async def start(self):
        """启动处理器"""
        if self._running:
            return

        self._running = True

        # 启动批量刷新任务
        if self._enable_batching:
            self._flush_task = asyncio.create_task(self._flush_loop())

        logger.info("SubconsciousProcessor started (SLA: <10ms)")

    async def stop(self):
        """停止处理器"""
        self._running = False

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # 清空剩余批次
        await self._flush_all_batches()

        logger.info("SubconsciousProcessor stopped")

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[NeuroEvent], Any],
        supports_batching: bool = False,
        batch_handler: Callable[[list[NeuroEvent]], Any] | None = None,
    ):
        """
        注册处理器

        Args:
            event_type: 事件类型
            handler: 单事件处理器
            supports_batching: 是否支持批处理
            batch_handler: 批量处理器（可选）
        """
        self._handlers[event_type] = handler

        if supports_batching and batch_handler:
            self._batch_handlers[event_type] = batch_handler

            # 初始化批次缓冲
            self._batches[event_type] = BatchBuffer(
                events=[],
                max_size=self._batch_size,
                max_wait_ms=self._batch_wait_ms,
                created_at=time.time(),
            )

        logger.debug(f"Registered handler for {event_type}")

    async def process(self, event: NeuroEvent) -> bool:
        """
        处理事件

        Returns:
            是否成功
        """
        start_time = time.perf_counter()

        try:
            event_type = event.event_type

            # 检查批处理
            if self._enable_batching and event_type in self._batch_handlers:
                return await self._batch_process(event)

            # 单事件处理
            handler = self._handlers.get(event_type)
            if not handler:
                logger.debug(f"No handler for {event_type}")
                return False

            # 执行处理（带超时）
            timeout_sec = self.SLA_MAX_MS / 1000.0

            if asyncio.iscoroutinefunction(handler):
                await asyncio.wait_for(handler(event), timeout=timeout_sec)
            else:
                # 同步处理器在线程池执行
                loop = asyncio.get_running_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(None, handler, event), timeout=timeout_sec
                )

            # 记录性能
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._latency_history.append(elapsed_ms)
            self._processed_count += 1

            # SLA 检查
            if elapsed_ms > self.SLA_TARGET_MS:
                if elapsed_ms > self.SLA_MAX_MS:
                    self._timeout_count += 1
                    logger.warning(f"SubconsciousProcessor timeout: {elapsed_ms:.2f}ms")
                else:
                    logger.debug(f"SubconsciousProcessor SLA warning: {elapsed_ms:.2f}ms")

            return True

        except TimeoutError:
            self._timeout_count += 1
            logger.warning(f"SubconsciousProcessor timeout for {event.event_type}")
            return False

        except Exception as e:
            self._error_count += 1
            logger.exception(f"SubconsciousProcessor error: {e}")
            return False

    async def _batch_process(self, event: NeuroEvent) -> bool:
        """批处理事件"""
        event_type = event.event_type
        batch = self._batches[event_type]

        batch.events.append(event)
        self._batched_count += 1

        # 检查是否满足刷新条件
        if len(batch.events) >= batch.max_size:
            await self._flush_batch(event_type)

        return True

    async def _flush_loop(self):
        """定期刷新批次"""
        while self._running:
            try:
                await asyncio.sleep(self._batch_wait_ms / 1000.0)
                await self._flush_expired_batches()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Flush loop error: {e}")

    async def _flush_expired_batches(self):
        """刷新过期批次"""
        now = time.time()

        for event_type, batch in list(self._batches.items()):
            if batch.events:
                elapsed_ms = (now - batch.created_at) * 1000

                if elapsed_ms >= batch.max_wait_ms or len(batch.events) >= batch.max_size:
                    await self._flush_batch(event_type)

    async def _flush_batch(self, event_type: str):
        """刷新指定批次"""
        batch = self._batches.get(event_type)
        if not batch or not batch.events:
            return

        events = batch.events
        batch.events = []
        batch.created_at = time.time()

        handler = self._batch_handlers.get(event_type)
        if not handler:
            return

        try:
            start_time = time.perf_counter()

            if asyncio.iscoroutinefunction(handler):
                await asyncio.wait_for(handler(events), timeout=self.SLA_MAX_MS / 1000.0)
            else:
                loop = asyncio.get_running_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(None, handler, events), timeout=self.SLA_MAX_MS / 1000.0
                )

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._processed_count += len(events)

            # 平均延迟
            avg_latency = elapsed_ms / len(events)
            if avg_latency > self.SLA_TARGET_MS:
                logger.debug(f"Batch processing SLA warning: {avg_latency:.2f}ms avg")

        except Exception as e:
            self._error_count += len(events)
            logger.exception(f"Batch processing error: {e}")

    async def _flush_all_batches(self):
        """刷新所有批次"""
        for event_type in list(self._batches.keys()):
            await self._flush_batch(event_type)

    def get_stats(self) -> dict[str, Any]:
        """获取统计"""
        avg_latency = 0.0
        if self._latency_history:
            avg_latency = sum(self._latency_history) / len(self._latency_history)

        return {
            "processed": self._processed_count,
            "batched": self._batched_count,
            "errors": self._error_count,
            "timeouts": self._timeout_count,
            "avg_latency_ms": avg_latency,
            "handlers": len(self._handlers),
            "batch_handlers": len(self._batch_handlers),
            "running": self._running,
        }


# 常用处理器


class LoggingHandler:
    """日志处理器"""

    @staticmethod
    async def handle(event: NeuroEvent):
        logger.info(f"Event: {event.event_type} from {event.metadata.source}")


class MetricsHandler:
    """指标处理器"""

    def __init__(self):
        self._counters: dict[str, int] = {}

    async def handle_batch(self, events: list[NeuroEvent]):
        """批量处理指标"""
        for event in events:
            event_type = event.event_type
            self._counters[event_type] = self._counters.get(event_type, 0) + 1


# 便捷函数


async def subconscious_log(
    message: str,
    level: str = "info",
    context: dict[str, Any] = None,
):
    """
    潜意识日志

    非阻塞的日志记录
    """
    # 简化为直接 logging
    log_fn = getattr(logger, level, logger.info)
    log_fn(message, extra=context or {})


# 单例
_subconscious: SubconsciousProcessor | None = None


def get_subconscious_processor() -> SubconsciousProcessor:
    """获取单例"""
    global _subconscious
    if _subconscious is None:
        _subconscious = SubconsciousProcessor()
    return _subconscious
