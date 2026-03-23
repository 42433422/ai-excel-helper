# -*- coding: utf-8 -*-
"""
ContextFacade - 统一上下文门面

组合 IntentContext 和 ChatContext，提供统一的上下文管理接口

核心流程：
1. 检查重复（ChatContext）
2. 检查 pending 续接（IntentContext）
3. 决策处理方式
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.domain.services.conversation.context.intent_context import (
    PendingIntent,
    IntentContext,
    get_intent_context,
    AdoptionReason,
    SPECIAL_INTENTS,
)
from app.domain.services.conversation.context.chat_context import (
    ChatTurn,
    ChatContext,
    get_chat_context,
)

logger = logging.getLogger(__name__)


class ProcessingAction(Enum):
    """处理动作枚举"""
    GREETING = "greeting"
    GOODBYE = "goodbye"
    HELP = "help"
    SLOT_FILL = "slot_fill"
    TOOL_CALL = "tool_call"
    AI_RESPONSE = "ai_response"
    NEGATED = "negated"
    DUPLICATE_RESPONSE = "duplicate_response"
    INTENT_SWITCH_QUERY = "intent_switch_query"


@dataclass
class IntentResult:
    """意图识别结果"""
    primary_intent: Optional[str]
    tool_key: Optional[str]
    slots: Dict[str, Any]
    is_greeting: bool = False
    is_goodbye: bool = False
    is_help: bool = False
    is_confirmation: bool = False
    is_negation_intent: bool = False
    is_negated: bool = False
    confidence: float = 0.0
    source: str = "unknown"


@dataclass
class ProcessingResult:
    """处理结果"""
    action: ProcessingAction
    text: str
    data: Dict[str, Any]
    pending_intent: Optional[PendingIntent] = None
    is_duplicate: bool = False
    cached_response: Optional[str] = None


@dataclass
class ContextDecision:
    """上下文决策"""
    should_continue: bool
    action: ProcessingAction
    reason: str
    merged_slots: Optional[Dict[str, Any]] = None
    pending_to_preserve: Optional[PendingIntent] = None


class ContextFacade:
    """
    统一上下文门面

    组合 IntentContext 和 ChatContext，协调处理流程

    流程：
    1. 检测重复（ChatContext）
    2. 获取 pending（IntentContext）
    3. 决策处理方式
    4. 返回处理结果

    使用依赖注入模式，支持通过容器管理生命周期。
    """

    def __init__(
        self,
        intent_context: Optional[IntentContext] = None,
        chat_context: Optional[ChatContext] = None
    ) -> None:
        self._intent_context = intent_context if intent_context is not None else get_intent_context()
        self._chat_context = chat_context if chat_context is not None else get_chat_context()

    @property
    def intent_context(self) -> IntentContext:
        return self._intent_context

    @property
    def chat_context(self) -> ChatContext:
        return self._chat_context

    def process(
        self,
        user_id: str,
        message: str,
        intent_result: IntentResult,
        response_text: Optional[str] = None
    ) -> ProcessingResult:
        """
        处理用户消息的上下文

        Args:
            user_id: 用户ID
            message: 用户消息
            intent_result: 意图识别结果
            response_text: 响应文本（用于缓存）

        Returns:
            ProcessingResult 处理结果
        """
        logger.info(
            f"[CONTEXT_FACADE] Processing: user={user_id}, "
            f"intent={intent_result.primary_intent}, "
            f"msg={message[:30]}..."
        )

        is_dup, cached_resp, is_exact = self._chat_context.is_duplicate(
            user_id=user_id,
            message=message,
            intent=intent_result.primary_intent,
            tool_key=intent_result.tool_key,
            slots=intent_result.slots
        )

        if is_dup and cached_resp:
            turn = ChatTurn(
                user_id=user_id,
                message=message,
                intent=intent_result.primary_intent,
                tool_key=intent_result.tool_key,
                slots=intent_result.slots,
                response_text=cached_resp,
                is_exact_duplicate=True,
                is_semantic_duplicate=not is_exact
            )
            self._chat_context.add_turn(user_id, turn)

            logger.info(f"[CONTEXT_FACADE] Duplicate response: user={user_id}")
            return ProcessingResult(
                action=ProcessingAction.DUPLICATE_RESPONSE,
                text=cached_resp,
                data={},
                is_duplicate=True,
                cached_response=cached_resp
            )

        decision = self._make_decision(user_id, message, intent_result)

        if decision.action == ProcessingAction.GREETING:
            result = self._handle_greeting(user_id, message, decision)
        elif decision.action == ProcessingAction.GOODBYE:
            result = self._handle_goodbye(user_id, message, decision)
        elif decision.action == ProcessingAction.HELP:
            result = self._handle_help(user_id, message, decision)
        elif decision.action == ProcessingAction.SLOT_FILL:
            result = self._handle_slot_fill(user_id, message, intent_result, decision)
        elif decision.action == ProcessingAction.TOOL_CALL:
            result = self._handle_tool_call(user_id, message, intent_result, decision)
        elif decision.action == ProcessingAction.NEGATED:
            result = self._handle_negated(user_id, message)
        elif decision.action == ProcessingAction.INTENT_SWITCH_QUERY:
            result = self._handle_intent_switch_query(user_id, message, intent_result, decision)
        else:
            result = ProcessingResult(
                action=ProcessingAction.AI_RESPONSE,
                text="抱歉，我没有理解您的意思。",
                data={}
            )

        if response_text:
            turn = ChatTurn(
                user_id=user_id,
                message=message,
                intent=intent_result.primary_intent,
                tool_key=intent_result.tool_key,
                slots=intent_result.slots,
                response_text=response_text,
                is_exact_duplicate=False,
                is_semantic_duplicate=False
            )
            self._chat_context.add_turn(user_id, turn)

        return result

    def _make_decision(
        self,
        user_id: str,
        message: str,
        intent_result: IntentResult
    ) -> ContextDecision:
        """
        做出上下文决策

        Returns:
            ContextDecision
        """
        pending = self._intent_context.get_pending(user_id)
        primary_intent = intent_result.primary_intent

        if intent_result.is_confirmation and pending:
            return ContextDecision(
                should_continue=True,
                action=ProcessingAction.TOOL_CALL,
                reason="user_confirmed_pending"
            )

        if intent_result.is_negation_intent and pending:
            return ContextDecision(
                should_continue=False,
                action=ProcessingAction.NEGATED,
                reason="user_negated",
                pending_to_preserve=None
            )

        if primary_intent in SPECIAL_INTENTS:
            return ContextDecision(
                should_continue=True,
                action=ProcessingAction(primary_intent),
                reason="special_intent",
                pending_to_preserve=pending
            )

        if not pending:
            return ContextDecision(
                should_continue=True,
                action=self._decide_action_for_new_intent(intent_result),
                reason="new_intent"
            )

        should_adopt, reason, merged = self._intent_context.should_adopt_new_intent(
            primary_intent, pending
        )

        if not should_adopt:
            return ContextDecision(
                should_continue=True,
                action=self._decide_action_for_preserved_intent(pending, intent_result),
                reason=f"preserved_{reason.value}",
                pending_to_preserve=pending
            )

        if reason == AdoptionReason.MERGE_SLOTS:
            merged_slots = merged.slots.copy() if merged else {}
            merged_slots.update(intent_result.slots)
            return ContextDecision(
                should_continue=True,
                action=self._decide_action_for_merged(merged_slots, primary_intent),
                reason="merged_slots",
                merged_slots=merged_slots,
                pending_to_preserve=pending
            )

        if reason == AdoptionReason.SWITCH_REQUESTED:
            return ContextDecision(
                should_continue=True,
                action=ProcessingAction.INTENT_SWITCH_QUERY,
                reason="switch_requested",
                merged_slots=merged.slots if merged else {},
                pending_to_preserve=pending
            )

        return ContextDecision(
            should_continue=True,
            action=self._decide_action_for_new_intent(intent_result),
            reason="switched_intent",
            merged_slots=intent_result.slots,
            pending_to_preserve=None
        )

    def _decide_action_for_new_intent(self, intent_result: IntentResult) -> ProcessingAction:
        """为新意图决定动作"""
        if not intent_result.primary_intent:
            return ProcessingAction.AI_RESPONSE

        if intent_result.is_greeting:
            return ProcessingAction.GREETING
        if intent_result.is_goodbye:
            return ProcessingAction.GOODBYE
        if intent_result.is_help:
            return ProcessingAction.HELP

        return ProcessingAction.TOOL_CALL

    def _decide_action_for_preserved_intent(
        self,
        pending: PendingIntent,
        intent_result: IntentResult
    ) -> ProcessingAction:
        """为保留的 pending 决定动作"""
        if intent_result.is_greeting:
            return ProcessingAction.GREETING
        if intent_result.is_goodbye:
            return ProcessingAction.GOODBYE
        if intent_result.is_help:
            return ProcessingAction.HELP

        return ProcessingAction.TOOL_CALL

    def _decide_action_for_merged(
        self,
        merged_slots: Dict[str, Any],
        intent: str
    ) -> ProcessingAction:
        """为合并后的槽位决定动作"""
        required_slots = self._get_required_slots(intent)
        missing = [s for s in required_slots if not merged_slots.get(s)]

        if missing:
            return ProcessingAction.SLOT_FILL
        return ProcessingAction.TOOL_CALL

    def _get_required_slots(self, intent: str) -> List[str]:
        """获取意图所需的必填槽位"""
        slot_map = {
            "shipment_generate": ["unit_name", "model_number", "tin_spec", "quantity_tins"],
            "product_query": ["keyword"],
            "customer_query": ["keyword"],
            "customer_supplement": ["field_name", "field_value"],
            "print_label": ["unit_name"],
            "wechat_send": ["unit_name"],
        }
        return slot_map.get(intent, [])

    def _handle_greeting(
        self,
        user_id: str,
        message: str,
        decision: ContextDecision
    ) -> ProcessingResult:
        """处理问候"""
        greeting_texts = [
            "您好！我是 XCAGI 智能助手，很高兴为您服务！",
            "你好呀！有什么可以帮您的吗？",
            "您好！欢迎使用 XCAGI 系统！",
        ]
        base_text = greeting_texts[hash(message) % len(greeting_texts)]

        if decision.pending_to_preserve:
            pending = decision.pending_to_preserve
            text = (
                f"{base_text}\n\n"
                f"（您有一个【{pending.intent}】任务尚未完成，"
                f"还缺少：{', '.join(pending.missing_slots) if pending.missing_slots else '无'}。\n"
                f"请继续补充信息，或说\"取消\"结束当前任务。）"
            )
            self._notify_pending_preserved(user_id, pending, "greeting")
        else:
            text = base_text

        return ProcessingResult(
            action=ProcessingAction.GREETING,
            text=text,
            data={},
            pending_intent=decision.pending_to_preserve
        )

    def _handle_goodbye(
        self,
        user_id: str,
        message: str,
        decision: ContextDecision
    ) -> ProcessingResult:
        """处理告别"""
        if decision.pending_to_preserve:
            self._notify_pending_preserved(user_id, decision.pending_to_preserve, "goodbye")
        return ProcessingResult(
            action=ProcessingAction.GOODBYE,
            text="再见！祝您工作顺利！如有需要，随时联系我。",
            data={},
            pending_intent=decision.pending_to_preserve
        )

    def _handle_help(
        self,
        user_id: str,
        message: str,
        decision: ContextDecision
    ) -> ProcessingResult:
        """处理帮助请求"""
        if decision.pending_to_preserve:
            self._notify_pending_preserved(user_id, decision.pending_to_preserve, "help")
        help_text = """🤖 XCAGI 智能助手功能介绍

📦 发货单管理 - 生成发货单、管理订单
📊 数据查询 - 产品、客户、发货记录
📤 文件处理 - 上传导入、模板分解
💡 智能提醒 - 根据您的操作习惯主动提示

直接说出您的需求，我会智能识别处理。"""

        return ProcessingResult(
            action=ProcessingAction.HELP,
            text=help_text,
            data={},
            pending_intent=decision.pending_to_preserve
        )

    def _handle_slot_fill(
        self,
        user_id: str,
        message: str,
        intent_result: IntentResult,
        decision: ContextDecision
    ) -> ProcessingResult:
        """处理槽位填充"""
        intent = intent_result.primary_intent
        slots = decision.merged_slots or intent_result.slots

        pending = PendingIntent(
            intent=intent,
            slots=slots,
            missing_slots=self._get_missing_slots(intent, slots),
            source="context_facade"
        )
        self._intent_context.set_pending(user_id, pending)

        question = self._build_followup_question(intent, pending.missing_slots, slots)

        return ProcessingResult(
            action=ProcessingAction.SLOT_FILL,
            text=question,
            data={
                "intent": intent,
                "slots": slots,
                "missing_slots": pending.missing_slots
            },
            pending_intent=pending
        )

    def _handle_tool_call(
        self,
        user_id: str,
        message: str,
        intent_result: IntentResult,
        decision: ContextDecision
    ) -> ProcessingResult:
        """处理工具调用"""
        intent = intent_result.primary_intent
        slots = decision.merged_slots or intent_result.slots

        self._intent_context.clear_pending(user_id)

        return ProcessingResult(
            action=ProcessingAction.TOOL_CALL,
            text=self._get_action_description(intent, slots),
            data={
                "intent": intent,
                "tool_key": intent_result.tool_key or intent,
                "slots": slots
            }
        )

    def _handle_negated(
        self,
        user_id: str,
        message: str
    ) -> ProcessingResult:
        """处理否定"""
        self._intent_context.clear_pending(user_id)

        return ProcessingResult(
            action=ProcessingAction.NEGATED,
            text="好的，已取消。有其他需要帮助的吗？",
            data={}
        )

    def _handle_intent_switch_query(
        self,
        user_id: str,
        message: str,
        intent_result: IntentResult,
        decision: ContextDecision
    ) -> ProcessingResult:
        """处理意图切换询问"""
        pending = decision.pending_to_preserve
        new_intent = intent_result.primary_intent

        text = (
            f"您之前有一个【{pending.intent}】任务还没完成。\n"
            f"现在您是想继续完成这个任务，还是切换到【{new_intent}】？\n"
            f"• 说\"继续\"保留原任务\n"
            f"• 说\"切换\"开始新任务\n"
            f"• 直接提供信息继续补充"
        )

        return ProcessingResult(
            action=ProcessingAction.INTENT_SWITCH_QUERY,
            text=text,
            data={
                "pending_intent": pending.intent,
                "pending_slots": pending.slots,
                "new_intent": new_intent,
                "new_slots": intent_result.slots
            },
            pending_intent=pending
        )

    def _get_missing_slots(self, intent: str, slots: Dict[str, Any]) -> List[str]:
        """获取缺失的槽位"""
        required = self._get_required_slots(intent)
        return [s for s in required if not slots.get(s)]

    def _build_followup_question(
        self,
        intent: str,
        missing_slots: List[str],
        current_slots: Dict[str, Any]
    ) -> str:
        """生成追问问题"""
        if not missing_slots:
            return "请提供更多信息"

        priority_order = ["unit_name", "model_number", "tin_spec", "quantity_tins"]

        for slot in priority_order:
            if slot in missing_slots:
                return self._get_slot_question(intent, slot)

        return f"请问{missing_slots[0]}是多少？"

    def _get_slot_question(self, intent: str, slot: str) -> str:
        """获取槽位追问"""
        questions = {
            "shipment_generate": {
                "unit_name": "请问要发货给哪个购买单位呢？",
                "model_number": "编号是多少呢？",
                "tin_spec": "规格是多少呢？",
                "quantity_tins": "这次需要多少桶呢？",
            },
            "product_query": {
                "keyword": "请问要搜索什么关键词？",
            },
            "customer_query": {
                "keyword": "请问要搜索什么关键词？",
            }
        }

        intent_questions = questions.get(intent, {})
        return intent_questions.get(slot, f"请问{slot}是多少呢？")

    def _get_action_description(self, intent: str, slots: Dict[str, Any]) -> str:
        """获取动作描述"""
        descriptions = {
            "shipment_generate": f"正在为 {slots.get('unit_name', '该客户')} 生成发货单",
            "products": f"正在查询 {slots.get('keyword', '该产品')} 的产品信息",
            "customers": f"正在查询客户信息",
            "shipments": f"正在查询发货记录",
            "print_label": f"正在处理标签打印",
            "wechat_send": f"正在发送微信消息",
        }
        return descriptions.get(intent, f"正在处理 {intent}")

    def update_pending_with_slots(
        self,
        user_id: str,
        new_slots: Dict[str, Any]
    ) -> Optional[PendingIntent]:
        """更新 pending 的槽位"""
        return self._intent_context.merge_slots(user_id, new_slots)

    def confirm_pending(self, user_id: str) -> Optional[PendingIntent]:
        """确认 pending，准备执行"""
        pending = self._intent_context.get_pending(user_id)
        if pending:
            self._intent_context.clear_pending(user_id)
        return pending

    def cancel_pending(self, user_id: str) -> None:
        """取消 pending"""
        self._intent_context.clear_pending(user_id)

    def get_context_summary(self, user_id: str) -> Dict[str, Any]:
        """获取上下文摘要"""
        return {
            "pending": self._intent_context.get_pending_summary(user_id),
            "history": self._chat_context.get_history_summary(user_id)
        }

    def _notify_pending_preserved(self, user_id: str, pending: PendingIntent, action: str) -> None:
        """通知 pending 保留（特殊意图时）"""
        try:
            notifier = self._get_notifier()
            if notifier and pending:
                pending_data = pending.to_dict()
                notifier.notify_pending_preserved(user_id, pending_data, action)
        except Exception as e:
            logger.warning(f"[CONTEXT_FACADE] Failed to notify preserved: {e}")

    def _get_notifier(self):
        """懒加载获取通知器"""
        if not hasattr(self, '_notifier'):
            try:
                from app.routes.context_api import get_context_notifier
                self._notifier = get_context_notifier()
            except ImportError:
                self._notifier = None
        return self._notifier


class ContextFacadeContainer:
    _instance: Optional[ContextFacade] = None

    @classmethod
    def get_instance(cls) -> ContextFacade:
        if cls._instance is None:
            cls._instance = ContextFacade()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None


def get_context_facade() -> ContextFacade:
    """获取 ContextFacade 单例（向后兼容）"""
    return ContextFacadeContainer.get_instance()
