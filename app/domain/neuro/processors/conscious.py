"""
显意识处理器（ConsciousProcessor）

<200ms 响应目标
- 主同步处理管道
- 核心业务逻辑
- 用户响应
- 完整可靠性机制栈
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.neuro_bus.bus import NeuroBus, get_neuro_bus
from app.neuro_bus.circuit_breaker import NeuroCircuitBreakerManager
from app.neuro_bus.deduplicator import NeuroBusDeduplicator
from app.neuro_bus.events.base import EventPriority, NeuroEvent
from app.neuro_bus.retry_handler import NeuroRetryHandler
from app.neuro_bus.sandbox import NeuroSandbox
from app.neuro_bus.sla_controller import SLAController

logger = logging.getLogger(__name__)


class ProcessingStage(Enum):
    """处理阶段"""

    VALIDATE = "validate"
    PRESERVE = "preserve"
    PREPROCESS = "preprocess"
    PROCESS = "process"
    POSTPROCESS = "postprocess"
    COMMIT = "commit"


@dataclass
class ProcessingResult:
    """处理结果"""

    success: bool
    data: Any = None
    error: str | None = None
    latency_ms: float = 0.0
    stage_reached: ProcessingStage = ProcessingStage.VALIDATE


class ConsciousProcessor:
    """
    显意识处理器

    用于：
    - 核心业务逻辑
    - 数据库操作
    - 外部服务调用
    - 用户响应生成

    SLA: < 200ms

    支持完整可靠性机制：
    - 去重
    - 熔断
    - SLA 监控
    - 重试
    - 沙盒预演
    """

    SLA_TARGET_MS = 200.0
    SLA_MAX_MS = 5000.0

    def __init__(
        self,
        bus: NeuroBus | None = None,
        enable_reliability: bool = True,
    ):
        self._bus = bus or get_neuro_bus()
        self._enable_reliability = enable_reliability

        # 可靠性机制
        self._deduplicator = NeuroBusDeduplicator() if enable_reliability else None
        self._circuit_breaker = NeuroCircuitBreakerManager() if enable_reliability else None
        self._sla_controller = SLAController() if enable_reliability else None
        self._retry_handler = NeuroRetryHandler() if enable_reliability else None
        self._sandbox = NeuroSandbox() if enable_reliability else None

        # 处理器注册
        self._handlers: dict[str, Callable[[NeuroEvent], Any]] = {}

        # 统计
        self._processed_count = 0
        self._success_count = 0
        self._error_count = 0
        self._dedup_count = 0
        self._circuit_open_count = 0
        self._sandbox_reject_count = 0
        self._sla_violation_count = 0

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[NeuroEvent], Any],
    ):
        """注册处理器"""
        self._handlers[event_type] = handler
        logger.debug(f"Registered conscious handler for {event_type}")

    async def process(self, event: NeuroEvent) -> ProcessingResult:
        """
        处理事件

        执行完整可靠性机制栈
        """
        start_time = time.perf_counter()
        stage = ProcessingStage.VALIDATE

        try:
            # 1. 去重检查
            if self._enable_reliability and self._deduplicator:
                if not self._deduplicator.check_and_acquire(event):
                    self._dedup_count += 1
                    cached_result = self._deduplicator.get_cached_result(event)
                    return ProcessingResult(
                        success=True,
                        data=cached_result,
                        latency_ms=(time.perf_counter() - start_time) * 1000,
                        stage_reached=stage,
                    )

            stage = ProcessingStage.PRESERVE

            # 2. 熔断检查
            if self._enable_reliability and self._circuit_breaker:
                if not self._circuit_breaker.check(event.metadata.domain, event.event_type):
                    self._circuit_open_count += 1
                    return ProcessingResult(
                        success=False,
                        error="Circuit breaker open",
                        latency_ms=(time.perf_counter() - start_time) * 1000,
                        stage_reached=stage,
                    )

            stage = ProcessingStage.PREPROCESS

            # 3. 沙盒预检（高风险操作）
            if self._enable_reliability and self._sandbox:
                if not self._sandbox.validate(event):
                    self._sandbox_reject_count += 1
                    return ProcessingResult(
                        success=False,
                        error="Sandbox validation failed",
                        latency_ms=(time.perf_counter() - start_time) * 1000,
                        stage_reached=stage,
                    )

            stage = ProcessingStage.PREPROCESS

            # 4. SLA 监控开始
            if self._enable_reliability and self._sla_controller:
                sla_monitor = self._sla_controller.start_monitoring(event)

            stage = ProcessingStage.PROCESS

            # 5. 执行处理
            handler = self._handlers.get(event.event_type)
            if not handler:
                return ProcessingResult(
                    success=False,
                    error=f"No handler for {event.event_type}",
                    latency_ms=(time.perf_counter() - start_time) * 1000,
                    stage_reached=stage,
                )

            # 带重试的执行
            if self._enable_reliability and self._retry_handler:
                result = await self._retry_handler.execute_for_event(
                    event.metadata.domain,
                    handler,
                    event,
                )
            else:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(event)
                else:
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(None, handler, event)

            stage = ProcessingStage.COMMIT

            # 6. 标记成功
            if self._enable_reliability:
                if self._deduplicator:
                    self._deduplicator.release(event, result)
                if self._circuit_breaker:
                    self._circuit_breaker.record_success(event.metadata.domain, event.event_type)

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # 7. SLA 检查
            if self._enable_reliability and self._sla_controller:
                sla_report = self._sla_controller.finish_monitoring(event.metadata.event_id)
                if sla_report and sla_report["status"] == "violated":
                    self._sla_violation_count += 1

            self._success_count += 1
            self._processed_count += 1

            return ProcessingResult(
                success=True,
                data=result,
                latency_ms=elapsed_ms,
                stage_reached=stage,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # 记录失败
            if self._enable_reliability:
                if self._circuit_breaker:
                    self._circuit_breaker.record_failure(event.metadata.domain, event.event_type)
                if self._deduplicator:
                    self._deduplicator.remove(event)

            self._error_count += 1
            self._processed_count += 1

            logger.exception(f"Conscious processing error: {e}")

            return ProcessingResult(
                success=False,
                error=str(e),
                latency_ms=elapsed_ms,
                stage_reached=stage,
            )

    def get_stats(self) -> dict[str, Any]:
        """获取统计"""
        return {
            "processed": self._processed_count,
            "success": self._success_count,
            "errors": self._error_count,
            "deduplicated": self._dedup_count,
            "circuit_open": self._circuit_open_count,
            "sandbox_rejected": self._sandbox_reject_count,
            "sla_violations": self._sla_violation_count,
            "success_rate": self._success_count / max(self._processed_count, 1),
            "handlers": len(self._handlers),
            "reliability_enabled": self._enable_reliability,
        }


# 常见处理器模式


class IntentProcessingHandler:
    """意图处理处理器模板"""

    async def handle(self, event: NeuroEvent) -> dict[str, Any]:
        """处理意图事件"""
        intent_type = event.payload.get("intent_type")
        raw_text = event.payload.get("raw_text")

        # 具体实现由子类覆盖
        return {
            "intent_type": intent_type,
            "processed": True,
            "response": "",
        }


class BusinessLogicHandler:
    """业务逻辑处理器模板"""

    async def validate(self, event: NeuroEvent) -> bool:
        """验证事件数据"""
        return True

    async def execute(self, event: NeuroEvent) -> Any:
        """执行业务逻辑"""
        raise NotImplementedError()

    async def handle(self, event: NeuroEvent) -> Any:
        """完整处理流程"""
        if not await self.validate(event):
            raise ValueError("Validation failed")

        return await self.execute(event)


# 便捷函数


async def conscious_process(
    event_type: str,
    payload: dict[str, Any],
    priority: EventPriority = EventPriority.HIGH,
) -> ProcessingResult:
    """便捷函数：处理事件"""
    processor = get_conscious_processor()

    event = NeuroEvent(
        event_type=event_type,
        payload=payload,
        priority=priority,
    )

    return await processor.process(event)


# 单例
_conscious: ConsciousProcessor | None = None


def get_conscious_processor() -> ConsciousProcessor:
    """获取单例"""
    global _conscious
    if _conscious is None:
        _conscious = ConsciousProcessor()
    return _conscious
