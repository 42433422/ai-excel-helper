"""
统一编排器 - 统一入口
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from backend.runtime_context import runtime_context_after_workflow_interrupt

from .intent_engine import IntentEngine, IntentResult
from .slot_filler import SlotFiller, SlotFillResult
from ..registry.tool_registry import get_tools_for_intent, get_tool
from ..utils.metrics import get_metrics

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    success: bool = False
    intent: str = ""
    tool_key: str | None = None
    confidence: float = 0.0
    slots: dict[str, Any] = field(default_factory=dict)
    missing_slots: list[str] = field(default_factory=list)
    response: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    processing_mode: str = "unknown"
    processing_time_ms: float = 0.0
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class UnifiedOrchestrator:
    def __init__(self):
        from ..registry.tool_registry import ensure_tools_initialized
        ensure_tools_initialized()
        self._intent_engine = IntentEngine()
        self._slot_filler = SlotFiller()

    async def process(
        self,
        user_message: str,
        context: dict[str, Any] | None = None,
        preferred_mode: str | None = None
    ) -> ProcessingResult:
        start = time.perf_counter()
        context = context or {}

        if preferred_mode:
            context["preferred_mode"] = preferred_mode

        logger.info(f"[UnifiedOrchestrator] 处理输入: {user_message[:50]}...")

        intent_result = await self._intent_engine.process(user_message, context)

        if intent_result.response and not intent_result.fallback_available:
            total_time_ms = (time.perf_counter() - start) * 1000
            logger.info(f"[UnifiedOrchestrator] Reflex直接响应 ({total_time_ms:.2f}ms)")

            get_metrics().inc("orchestrator.total")
            get_metrics().histogram("orchestrator.duration_ms", total_time_ms)

            extra_data: dict[str, Any] = {}
            if intent_result.intent in ("stop", "confirm_no"):
                prior = context.get("runtime_context") if isinstance(context, dict) else None
                if not isinstance(prior, dict):
                    prior = None
                extra_data["runtime_context"] = runtime_context_after_workflow_interrupt(prior)

            return ProcessingResult(
                success=True,
                intent=intent_result.intent,
                confidence=intent_result.confidence,
                response=intent_result.response,
                processing_mode=intent_result.processing_mode,
                processing_time_ms=total_time_ms,
                data=extra_data,
            )

        merged_entities = dict(intent_result.entities or {})
        try:
            from backend.sales_contract_intent_bridge import merge_bridge_prefill_entities

            merged_entities = merge_bridge_prefill_entities(
                intent_result.intent, merged_entities, user_message
            )
        except Exception as e:
            logger.debug("[UnifiedOrchestrator] sales contract bridge prefill skipped: %s", e)

        slot_result = await self._slot_filler.fill(
            intent=intent_result.intent,
            entities=merged_entities,
            user_input=user_message,
            context=context
        )

        tools = get_tools_for_intent(slot_result.intent)
        tool_result = None

        if tools and slot_result.success:
            tool_result = await self._execute_tools(tools, slot_result.slots, user_message=user_message)

        if slot_result.missing_slots:
            response = f"请补充以下信息：{', '.join(slot_result.missing_slots)}"
        elif tool_result and tool_result.get("success"):
            response = tool_result.get("message", "操作完成")
        else:
            response = intent_result.response or f"已识别意图：{intent_result.intent}"

        total_time_ms = (time.perf_counter() - start) * 1000

        logger.info(
            f"[UnifiedOrchestrator] 完成: intent={intent_result.intent}, "
            f"mode={intent_result.processing_mode}, time={total_time_ms:.2f}ms"
        )

        # 清理 tool_result，只保留可序列化的字段
        serializable_data = {}
        if tool_result:
            for key, value in tool_result.items():
                if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                    # 递归检查嵌套的 dict
                    if isinstance(value, dict):
                        serializable_data[key] = {
                            k: v for k, v in value.items()
                            if isinstance(v, (str, int, float, bool, list, dict, type(None)))
                        }
                    else:
                        serializable_data[key] = value

        get_metrics().inc("orchestrator.total")
        get_metrics().histogram("orchestrator.duration_ms", total_time_ms)

        # 清理 metadata，只保留可序列化的字段（含 bridge 预填后的 entities）
        clean_entities = {}
        for key, value in merged_entities.items():
            if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                clean_entities[key] = value

        return ProcessingResult(
            success=tool_result.get("success", True) if tool_result else slot_result.success,
            intent=intent_result.intent,
            tool_key=tools[0] if tools else None,
            confidence=intent_result.confidence,
            slots=slot_result.slots,
            missing_slots=slot_result.missing_slots,
            response=response,
            data=serializable_data,
            processing_mode=intent_result.processing_mode,
            processing_time_ms=total_time_ms,
            metadata={
                "intent_result": {
                    "processing_mode": intent_result.processing_mode,
                    "entities": clean_entities
                },
                "slot_result": {
                    "missing_slots": slot_result.missing_slots,
                    "filled_count": len(slot_result.slots)
                }
            }
        )

    async def _execute_tools(
        self,
        tools: list,
        slots: dict[str, Any],
        *,
        user_message: str = "",
    ) -> dict[str, Any]:
        results = []
        merged_slots = dict(slots)
        um = (user_message or "").strip()
        if um:
            merged_slots["_user_message"] = um

        for tool_def in tools:
            try:
                tool = get_tool(tool_def.name)
                if not tool:
                    logger.warning(f"[UnifiedOrchestrator] 工具不存在: {tool_def.name}")
                    continue

                handler = tool_def.handler
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(**merged_slots)
                else:
                    result = handler(**merged_slots)

                if isinstance(result, dict):
                    results.append(result)
                else:
                    results.append(result.to_dict() if hasattr(result, 'to_dict') else {"success": True, "data": result})

            except Exception as e:
                logger.warning(f"[UnifiedOrchestrator] 工具执行失败: {tool_def.name}, error: {e}")
                results.append({"success": False, "error": str(e)})

        if not results:
            return {"success": False, "error": "没有可执行的工具"}

        first_success = next((r for r in results if r.get("success")), results[0])

        return first_success

    def get_intent_engine(self) -> IntentEngine:
        return self._intent_engine

    def get_slot_filler(self) -> SlotFiller:
        return self._slot_filler


_orchestrator: UnifiedOrchestrator | None = None


def get_orchestrator() -> UnifiedOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = UnifiedOrchestrator()
    return _orchestrator
