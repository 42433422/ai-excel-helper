"""
对话协调器集成

将 Neuro-DDD 架构与现有对话协调器集成
- 注入 NeuroBus 事件发布
- 添加处理器协调
"""

import logging
from dataclasses import dataclass
from typing import Any

from app.domain.neuro.processors.coordinator import (
    ProcessorCoordinator,
    get_processor_coordinator,
)
from app.domain.services.conversation.coordinator import (
    UnifiedConversationCoordinator,
)
from app.domain.services.conversation.coordinator import (
    get_conversation_coordinator as get_base_coordinator,
)
from app.neuro_bus.domains.intent_domain import get_intent_domain

logger = logging.getLogger(__name__)


@dataclass
class NeuroProcessingResult:
    """神经处理结果"""

    action: str
    text: str
    data: dict[str, Any]
    processor_type: str
    latency_ms: float
    neuro_enhanced: bool = True


class NeuroConversationCoordinator:
    """
    神经对话协调器

    集成 Neuro-DDD 的对话协调：
    1. 使用 ProcessorCoordinator 进行路由
    2. 原 Coordinator 作为后备
    3. NeuroBus 事件发布
    """

    def __init__(
        self,
        base_coordinator: UnifiedConversationCoordinator | None = None,
        processor_coordinator: ProcessorCoordinator | None = None,
    ):
        self._base = base_coordinator or get_base_coordinator()
        self._processor = processor_coordinator or get_processor_coordinator()
        self._intent_domain = get_intent_domain()

    async def process(
        self,
        user_id: str,
        message: str,
        context_data: dict[str, Any] = None,
    ) -> NeuroProcessingResult:
        """
        处理用户消息

        流程：
        1. 尝试 Neuro 处理器
        2. 如需要深度处理，使用原协调器
        3. 发布事件
        """
        # 1. 尝试 Neuro 处理器路由
        neuro_report = await self._processor.process(
            text=message,
            user_id=user_id,
            context=context_data,
        )

        # 2. 如 Neuro 处理器成功处理
        if neuro_report.success:
            result = neuro_report.result or {}

            # 转换结果
            return NeuroProcessingResult(
                action=self._map_processor_action(neuro_report.processor_used),
                text=result.get("response", ""),
                data=result,
                processor_type=neuro_report.processor_used.value,
                latency_ms=neuro_report.latency_ms,
                neuro_enhanced=True,
            )

        # 3. Neuro 未处理，使用原协调器
        base_result = self._base.process(user_id, message, context_data)
        try:
            self._intent_domain.emit_intent_recognized(
                intent_type="general",
                confidence=0.5,
                entities={},
                raw_text=message,
                processor_used="legacy_coordinator",
                latency_ms=0.0,
            )
        except Exception:
            logger.debug("intent emit skipped for legacy coordinator path", exc_info=True)

        return NeuroProcessingResult(
            action=base_result.action.value,
            text=base_result.text,
            data=base_result.data,
            processor_type="legacy",
            latency_ms=0.0,  # 未知
            neuro_enhanced=False,
        )

    def _map_processor_action(self, processor_type) -> str:
        """映射处理器类型到动作"""
        from app.domain.neuro.processors import ProcessorType

        mapping = {
            ProcessorType.REFLEX: "greeting",
            ProcessorType.SUBCONSCIOUS: "background_task",
            ProcessorType.CONSCIOUS: "ai_response",
        }

        return mapping.get(processor_type, "ai_response")


def integrate_with_conversation_coordinator():
    """
    集成对话协调器

    注册 NeuroConversationCoordinator
    """
    logger.info("Integrating Neuro-DDD with conversation coordinator...")

    # 创建集成协调器
    neuro_coordinator = NeuroConversationCoordinator()

    logger.info("Conversation coordinator integration complete")

    return neuro_coordinator


# 全局单例
_neuro_coordinator: NeuroConversationCoordinator | None = None


def get_neuro_conversation_coordinator() -> NeuroConversationCoordinator:
    """获取神经对话协调器单例"""
    global _neuro_coordinator
    if _neuro_coordinator is None:
        _neuro_coordinator = integrate_with_conversation_coordinator()
    return _neuro_coordinator
