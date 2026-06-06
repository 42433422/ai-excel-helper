"""
意图域（IntentNeuroDomain）

意图识别事件通道，优先级最高
"""

import logging
from dataclasses import dataclass
from typing import Any

from app.neuro_bus.domains.base import DomainChannel, NeuroDomain, get_domain_registry
from app.neuro_bus.events.base import EventPriority, NeuroEvent

logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    """意图识别结果"""

    intent_type: str
    confidence: float
    entities: dict[str, Any]
    raw_text: str
    processor_used: str  # "reflex", "subconscious", "conscious"
    latency_ms: float


class IntentNeuroDomain(NeuroDomain):
    """
    意图神经域

    处理：
    - 意图识别请求
    - 意图识别完成
    - 意图处理状态更新
    - Reflex 级快速响应
    """

    domain_name = "intent"
    default_channel = DomainChannel.FAST

    def __init__(self, bus=None):
        super().__init__(bus)

        # 统计
        self._recognized_count = 0
        self._reflex_count = 0
        self._failed_count = 0

        # 注册默认处理器（子类可覆盖）
        self._setup_handlers()

    def _setup_handlers(self):
        """设置默认事件处理器"""

        @self.on("intent.recognized", priority=0, channel=DomainChannel.FAST)
        async def on_intent_recognized(event: NeuroEvent):
            """意图识别完成"""
            self._recognized_count += 1
            intent_type = event.payload.get("intent_type")
            confidence = event.payload.get("confidence", 0.0)
            processor = event.payload.get("processor_used", "unknown")

            if processor == "reflex":
                self._reflex_count += 1

            logger.debug(
                f"Intent recognized: {intent_type} (confidence={confidence:.2f}, processor={processor})"
            )
            try:
                from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

                bump_domain_handler_metric("intent.recognized")
            except Exception:
                pass

        @self.on("intent.processing", priority=1, channel=DomainChannel.FAST)
        async def on_intent_processing(event: NeuroEvent):
            """意图处理中"""
            intent_type = event.payload.get("intent_type")
            logger.debug(f"Intent processing: {intent_type}")
            try:
                from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

                bump_domain_handler_metric("intent.processing")
            except Exception:
                pass

        @self.on("intent.failed", priority=0, channel=DomainChannel.STANDARD)
        async def on_intent_failed(event: NeuroEvent):
            """意图处理失败"""
            self._failed_count += 1
            intent_type = event.payload.get("intent_type")
            error = event.payload.get("error", "Unknown")
            logger.error(f"Intent failed: {intent_type}, error: {error}")
            try:
                from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

                bump_domain_handler_metric("intent.failed")
            except Exception:
                pass

        @self.on("intent.reflex_triggered", priority=0, channel=DomainChannel.FAST)
        async def on_reflex_triggered(event: NeuroEvent):
            """反射弧触发"""
            self._reflex_count += 1
            reflex_type = event.payload.get("reflex_type")
            latency_ms = event.payload.get("latency_ms", 0)
            logger.debug(f"Reflex triggered: {reflex_type} ({latency_ms:.2f}ms)")
            try:
                from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

                bump_domain_handler_metric("intent.reflex_triggered")
            except Exception:
                pass

    async def initialize(self):
        """初始化意图域"""
        logger.info("IntentNeuroDomain initialized")

    async def shutdown(self):
        """关闭意图域"""
        logger.info("IntentNeuroDomain shutdown")

    def emit_intent_recognized(
        self,
        intent_type: str,
        confidence: float,
        entities: dict[str, Any],
        raw_text: str,
        processor_used: str = "conscious",
        latency_ms: float = 0.0,
    ) -> bool:
        """
        发送意图识别完成事件
        """
        return self.emit(
            event_type="intent.recognized",
            priority=EventPriority.HIGH,
            payload={
                "intent_type": intent_type,
                "confidence": confidence,
                "entities": entities,
                "raw_text": raw_text,
                "processor_used": processor_used,
                "latency_ms": latency_ms,
            },
        )

    def emit_intent_processing(
        self,
        intent_type: str,
        user_id: str,
        stage: str = "started",
    ) -> bool:
        """
        发送意图处理中事件
        """
        return self.emit(
            event_type="intent.processing",
            priority=EventPriority.HIGH,
            payload={
                "intent_type": intent_type,
                "user_id": user_id,
                "stage": stage,
            },
        )

    def emit_intent_failed(
        self,
        intent_type: str,
        user_id: str,
        error: str,
        raw_text: str = "",
    ) -> bool:
        """
        发送意图处理失败事件
        """
        return self.emit(
            event_type="intent.failed",
            priority=EventPriority.NORMAL,
            payload={
                "intent_type": intent_type,
                "user_id": user_id,
                "error": error,
                "raw_text": raw_text,
            },
        )

    def emit_reflex_triggered(
        self,
        reflex_type: str,
        latency_ms: float,
        user_id: str,
    ) -> bool:
        """
        发送反射弧触发事件
        """
        return self.emit(
            event_type="intent.reflex_triggered",
            priority=EventPriority.CRITICAL,
            payload={
                "reflex_type": reflex_type,
                "latency_ms": latency_ms,
                "user_id": user_id,
            },
        )

    def get_stats(self) -> dict[str, Any]:
        """获取统计"""
        base_stats = super().get_stats()
        out = {
            **base_stats,
            "recognized": self._recognized_count,
            "reflex_triggers": self._reflex_count,
            "failed": self._failed_count,
            "reflex_rate": self._reflex_count / max(self._recognized_count, 1),
        }
        try:
            from app.neuro_bus.neuro_trace_config import (
                get_domain_handler_metrics,
                is_neuro_domain_metrics_enabled,
            )

            if is_neuro_domain_metrics_enabled():
                allm = get_domain_handler_metrics()
                intent_only = {k: v for k, v in allm.items() if k.startswith("intent.")}
                if intent_only:
                    out["handler_metrics"] = intent_only
        except Exception:
            pass
        return out


# 单例
_intent_domain: IntentNeuroDomain | None = None


def get_intent_domain() -> IntentNeuroDomain:
    """获取意图域单例"""
    global _intent_domain
    if _intent_domain is None:
        _intent_domain = IntentNeuroDomain()
        get_domain_registry().register(_intent_domain)
    return _intent_domain
