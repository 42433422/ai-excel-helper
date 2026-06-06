"""
处理器协调器（ProcessorCoordinator）

双模式意图处理协调
- Reflex: <1ms (反射弧)
- Subconscious: <10ms (潜意识)
- Conscious: <200ms (显意识)

负责：
- 意图分级路由
- 处理器选择
- 降级与升级
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.domain.neuro.processors.conscious import ConsciousProcessor, get_conscious_processor
from app.domain.neuro.processors.subconscious import (
    SubconsciousProcessor,
    get_subconscious_processor,
)
from app.domain.neuro.reflex_arc import IntentReflexArc, get_reflex_arc
from app.neuro_bus.domains.intent_domain import get_intent_domain
from app.neuro_bus.events.base import EventPriority, NeuroEvent

logger = logging.getLogger(__name__)


class ProcessorType(Enum):
    """处理器类型"""

    REFLEX = "reflex"  # < 1ms
    SUBCONSCIOUS = "subconscious"  # < 10ms
    CONSCIOUS = "conscious"  # < 200ms


@dataclass
class RoutingDecision:
    """路由决策"""

    processor_type: ProcessorType
    confidence: float
    reason: str


@dataclass
class ProcessingReport:
    """处理报告"""

    success: bool
    processor_used: ProcessorType
    latency_ms: float
    result: Any
    fallback_used: bool = False
    error: str | None = None


class ProcessorCoordinator:
    """
    处理器协调器

    实现双模式意图处理的智能路由

    路由策略：
    1. Reflex (反射弧)
       - 输入匹配预定义模式
       - 置信度 >= 0.8
       - 立即响应

    2. Subconscious (潜意识)
       - 后台任务
       - 日志、统计
       - 非关键路径

    3. Conscious (显意识)
       - 核心业务逻辑
       - AI 处理
       - 完整可靠性机制

    降级策略：
    - Conscious 超时 -> 返回简化响应
    - 系统过载 -> 优先使用 Reflex
    """

    def __init__(
        self,
        reflex_arc: IntentReflexArc | None = None,
        subconscious: SubconsciousProcessor | None = None,
        conscious: ConsciousProcessor | None = None,
    ):
        self._reflex = reflex_arc or get_reflex_arc()
        self._subconscious = subconscious or get_subconscious_processor()
        self._conscious = conscious or get_conscious_processor()

        # 统计
        self._reflex_count = 0
        self._subconscious_count = 0
        self._conscious_count = 0
        self._fallback_count = 0
        self._error_count = 0

    def route(self, text: str, event: NeuroEvent | None = None) -> RoutingDecision:
        """
        路由决策

        根据输入特征选择处理器
        """
        from app.neuro_bus.routing.policy_router import decide_processor_with_policy

        policy_decision = decide_processor_with_policy(text, event)
        if policy_decision is not None:
            return policy_decision

        # 1. 尝试 Reflex
        reflex_result = self._reflex.process(text)

        if reflex_result.triggered and reflex_result.confidence >= 0.8:
            self._reflex_count += 1
            return RoutingDecision(
                processor_type=ProcessorType.REFLEX,
                confidence=reflex_result.confidence,
                reason=f"Reflex match ({reflex_result.reflex_type.value})",
            )

        # 2. 检查是否为后台任务
        if event and event.priority in [EventPriority.LOW, EventPriority.BACKGROUND]:
            self._subconscious_count += 1
            return RoutingDecision(
                processor_type=ProcessorType.SUBCONSCIOUS,
                confidence=0.9,
                reason="Background task priority",
            )

        # 3. 默认使用 Conscious
        self._conscious_count += 1
        return RoutingDecision(
            processor_type=ProcessorType.CONSCIOUS,
            confidence=0.7,
            reason="Default to conscious processing",
        )

    async def process(
        self,
        text: str,
        user_id: str = "",
        context: dict[str, Any] = None,
    ) -> ProcessingReport:
        """
        处理用户输入

        完整处理流程：
        1. 路由决策
        2. 执行处理
        3. 降级处理（如需要）
        """
        start_time = time.perf_counter()
        context = context or {}

        # 路由决策
        decision = self.route(text)

        try:
            # 根据决策执行处理
            if decision.processor_type == ProcessorType.REFLEX:
                result = await self._process_reflex(text, user_id)

            elif decision.processor_type == ProcessorType.SUBCONSCIOUS:
                result = await self._process_subconscious(text, user_id, context)

            else:  # CONSCIOUS
                result = await self._process_conscious(text, user_id, context)

                # 如果 Conscious 失败，尝试降级到 Reflex
                if not result.success:
                    fallback_result = await self._process_reflex(text, user_id)
                    if fallback_result.success:
                        self._fallback_count += 1
                        result = fallback_result
                        result.fallback_used = True

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            result.latency_ms = elapsed_ms

            # 发送意图事件
            await self._emit_intent_event(text, user_id, result, decision)

            return result

        except Exception as e:
            self._error_count += 1
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            logger.exception(f"Processing error: {e}")

            # 紧急降级到 Reflex
            try:
                fallback = await self._process_reflex(text, user_id)
                if fallback.success:
                    self._fallback_count += 1
                    fallback.fallback_used = True
                    fallback.latency_ms = elapsed_ms
                    return fallback
            except Exception:
                pass

            fail_report = ProcessingReport(
                success=False,
                processor_used=decision.processor_type,
                latency_ms=elapsed_ms,
                result=None,
                error=str(e),
            )
            await self._emit_intent_event(text, user_id, fail_report, decision)
            return fail_report

    async def _process_reflex(self, text: str, user_id: str) -> ProcessingReport:
        """反射处理"""
        start_time = time.perf_counter()

        result = self._reflex.process(text)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return ProcessingReport(
            success=result.triggered,
            processor_used=ProcessorType.REFLEX,
            latency_ms=elapsed_ms,
            result={
                "reflex_type": result.reflex_type.value if result.triggered else None,
                "response": result.response,
                "confidence": result.confidence,
            },
        )

    async def _process_subconscious(
        self,
        text: str,
        user_id: str,
        context: dict[str, Any],
    ) -> ProcessingReport:
        """潜意识处理"""
        start_time = time.perf_counter()

        # 创建事件
        event = NeuroEvent(
            event_type="subconscious.task",
            payload={
                "text": text,
                "user_id": user_id,
                "context": context,
            },
            priority=EventPriority.LOW,
        )

        # 执行处理
        success = await self._subconscious.process(event)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return ProcessingReport(
            success=success,
            processor_used=ProcessorType.SUBCONSCIOUS,
            latency_ms=elapsed_ms,
            result={"processed": success},
        )

    async def _process_conscious(
        self,
        text: str,
        user_id: str,
        context: dict[str, Any],
    ) -> ProcessingReport:
        """显意识处理"""
        start_time = time.perf_counter()

        # 创建事件
        event = NeuroEvent(
            event_type="intent.process",
            payload={
                "text": text,
                "user_id": user_id,
                "context": context,
            },
            priority=EventPriority.HIGH,
        )

        # 执行处理
        result = await self._conscious.process(event)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return ProcessingReport(
            success=result.success,
            processor_used=ProcessorType.CONSCIOUS,
            latency_ms=elapsed_ms,
            result=result.data,
            error=result.error,
        )

    async def _emit_intent_event(
        self,
        text: str,
        user_id: str,
        report: ProcessingReport,
        decision: RoutingDecision,
    ):
        """发送意图处理事件"""
        try:
            intent_domain = get_intent_domain()

            if report.success:
                if report.processor_used == ProcessorType.REFLEX:
                    rdata = report.result or {}
                    rt = rdata.get("reflex_type") or "unknown"
                    intent_domain.emit_reflex_triggered(
                        reflex_type=str(rt),
                        latency_ms=report.latency_ms,
                        user_id=user_id or "",
                    )
                intent_domain.emit_intent_recognized(
                    intent_type="general",
                    confidence=decision.confidence,
                    entities={},
                    raw_text=text,
                    processor_used=report.processor_used.value,
                    latency_ms=report.latency_ms,
                )
            else:
                intent_domain.emit_intent_failed(
                    intent_type="general",
                    user_id=user_id,
                    error=report.error or "Processing failed",
                    raw_text=text,
                )

        except Exception as e:
            logger.exception(f"Failed to emit intent event: {e}")

    def get_stats(self) -> dict[str, Any]:
        """获取统计"""
        total = self._reflex_count + self._subconscious_count + self._conscious_count

        return {
            "reflex": self._reflex_count,
            "subconscious": self._subconscious_count,
            "conscious": self._conscious_count,
            "total": total,
            "fallbacks": self._fallback_count,
            "errors": self._error_count,
            "reflex_rate": self._reflex_count / max(total, 1),
            "fallback_rate": self._fallback_count / max(total, 1),
        }

    def get_all_processor_stats(self) -> dict[str, Any]:
        """获取所有处理器统计"""
        return {
            "coordinator": self.get_stats(),
            "reflex": self._reflex.get_stats(),
            "subconscious": self._subconscious.get_stats(),
            "conscious": self._conscious.get_stats(),
        }


# 便捷函数


async def process_intent(
    text: str,
    user_id: str = "",
    context: dict[str, Any] = None,
) -> ProcessingReport:
    """
    便捷函数：处理意图

    用法:
        report = await process_intent("你好")
        if report.success:
            print(report.result)
    """
    coordinator = get_processor_coordinator()
    return await coordinator.process(text, user_id, context)


def route_intent(text: str) -> ProcessorType:
    """
    便捷函数：获取路由决策

    用法:
        processor_type = route_intent("你好")
        if processor_type == ProcessorType.REFLEX:
            # 快速路径
            pass
    """
    coordinator = get_processor_coordinator()
    decision = coordinator.route(text)
    return decision.processor_type


# 单例
_coordinator: ProcessorCoordinator | None = None


def get_processor_coordinator() -> ProcessorCoordinator:
    """获取单例"""
    global _coordinator
    if _coordinator is None:
        _coordinator = ProcessorCoordinator()
    return _coordinator
