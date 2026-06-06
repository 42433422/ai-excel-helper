"""
对话上下文模块

提供双上下文机制：
- IntentContext: 任务上下文，管理 pending 状态的粘接和续接
- ChatContext: 聊天上下文，管理对话历史和重复检测
"""

from app.domain.services.conversation.context.chat_context import (
    ChatContext,
    ChatTurn,
    get_chat_context,
)
from app.domain.services.conversation.context.context_facade import (
    ContextDecision,
    ContextFacade,
    IntentResult,
    ProcessingAction,
    ProcessingResult,
    get_context_facade,
)
from app.domain.services.conversation.context.intent_context import (
    HIGH_PRIORITY_INTENTS,
    LOW_PRIORITY_INTENTS,
    SPECIAL_INTENTS,
    AdoptionReason,
    IntentContext,
    PendingIntent,
    get_intent_context,
)

__all__ = [
    # IntentContext
    "PendingIntent",
    "IntentContext",
    "get_intent_context",
    "AdoptionReason",
    "SPECIAL_INTENTS",
    "LOW_PRIORITY_INTENTS",
    "HIGH_PRIORITY_INTENTS",
    # ChatContext
    "ChatTurn",
    "ChatContext",
    "get_chat_context",
    # ContextFacade
    "ContextFacade",
    "get_context_facade",
    "ProcessingAction",
    "IntentResult",
    "ProcessingResult",
    "ContextDecision",
]
