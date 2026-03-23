# -*- coding: utf-8 -*-
"""
统一对话编排器

设计目标：
1. 单一入口 - 所有对话消息通过此编排器处理
2. 状态统一 - pending 状态在此组件内统一管理
3. 职责分明 - 意图识别、槽位验证、追问生成、执行编排各司其职
4. 零侵入 - 复用现有组件，不修改原有代码

核心流程：
Message → 意图识别 → 槽位验证 → (缺失? 追问 : 执行编排)

注意：此文件已重构，核心逻辑已移至 context 模块：
- IntentContext: 任务上下文（pending 状态管理）
- ChatContext: 聊天上下文（历史记录和重复检测）
- ContextFacade: 统一门面（组合两者）

此文件保留用于向后兼容，新代码应使用 ContextFacade。
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.domain.services.conversation.context import (
    ContextFacade,
    get_context_facade,
    ProcessingAction as ContextProcessingAction,
    IntentResult as ContextIntentResult,
    PendingIntent as ContextPendingIntent,
    SPECIAL_INTENTS as _SPECIAL_INTENTS,
    LOW_PRIORITY_INTENTS as _LOW_PRIORITY_INTENTS,
    HIGH_PRIORITY_INTENTS as _HIGH_PRIORITY_INTENTS,
)

logger = logging.getLogger(__name__)


class ProcessingAction(Enum):
    """处理动作枚举（向后兼容）"""
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
class PendingIntent:
    """
    待确认意图（向后兼容）

    为了保持向后兼容，保留原有的 PendingIntent dataclass。
    新代码应使用 context 模块中的 PendingIntent。
    """
    intent: str
    slots: Dict[str, Any]
    missing_slots: List[str]
    created_at: float = field(default_factory=time.time)
    source: str = "unknown"
    last_updated_at: float = field(default_factory=time.time)
    turn_count: int = 1

    def is_expired(self, max_age_seconds: float = 300) -> bool:
        """检查是否过期"""
        return time.time() - self.last_updated_at > max_age_seconds

    def merge_slots(self, new_slots: Dict[str, Any]) -> 'PendingIntent':
        """合并新槽位"""
        merged = self.slots.copy()
        merged.update(new_slots)

        still_missing = [s for s in self.missing_slots if not merged.get(s)]

        return PendingIntent(
            intent=self.intent,
            slots=merged,
            missing_slots=still_missing,
            created_at=self.created_at,
            source=self.source,
            last_updated_at=time.time(),
            turn_count=self.turn_count + 1
        )


@dataclass
class IntentResult:
    """意图识别结果（向后兼容）"""
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
    intent_hints: List[str] = field(default_factory=list)


@dataclass
class ProcessingResult:
    """处理结果（向后兼容）"""
    action: ProcessingAction
    text: str
    data: Dict[str, Any]
    pending_intent: Optional[PendingIntent] = None


class UnifiedConversationCoordinator:
    """
    统一对话编排器

    这是对话处理的唯一入口，负责：
    1. 协调意图识别流程
    2. 管理对话状态（pending）
    3. 验证槽位
    4. 生成追问
    5. 编排执行

    为了向后兼容，保留原有实现。
    新代码建议直接使用 ContextFacade。
    """

    def __init__(self):
        self.slot_validator = SlotValidator()

        self._task_agent = None
        self._context_facade = None

    @property
    def task_agent(self):
        """延迟加载 TaskAgent"""
        if self._task_agent is None:
            from app.services.task_agent import get_task_agent
            self._task_agent = get_task_agent()
        return self._task_agent

    @property
    def context_facade(self) -> ContextFacade:
        """获取 ContextFacade"""
        if self._context_facade is None:
            self._context_facade = get_context_facade()
        return self._context_facade

    def process(self, user_id: str, message: str, context_data: Dict[str, Any] = None) -> ProcessingResult:
        """
        处理用户消息的唯一入口

        流程：
        1. 检查 pending 状态
        2. 识别意图
        3. 验证槽位
        4. 缺失 → 追问，完整 → 执行
        """
        logger.info(f"[COORDINATOR] Processing: user={user_id}, msg={message[:50]}")

        pending = self._get_pending(user_id)

        intent_result = self._recognize_intent(message, context_data)

        if intent_result.is_confirmation and pending:
            return self._handle_confirmation(user_id, message, pending)

        if intent_result.is_negation_intent and not pending:
            if len(message) < 10:
                return ProcessingResult(
                    action=ProcessingAction.NEGATED,
                    text="好的，已取消。有其他需要帮助的吗？",
                    data={}
                )

        if intent_result.is_greeting:
            return self._handle_greeting(user_id, message, pending)
        if intent_result.is_goodbye:
            return self._handle_goodbye(user_id, message, pending)
        if intent_result.is_help:
            return self._handle_help(user_id, message, pending)

        if pending:
            return self._handle_pending_continuation(user_id, message, intent_result, pending)

        is_complete, missing = self.slot_validator.validate(
            intent_result.primary_intent,
            intent_result.slots
        )

        if not is_complete:
            return self._handle_slot_missing(
                user_id, message, intent_result, missing
            )

        return self._handle_execution(user_id, message, intent_result)

    def _get_pending(self, user_id: str) -> Optional[PendingIntent]:
        """获取 pending 状态"""
        ctx_pending = self.context_facade.intent_context.get_pending(user_id)
        if ctx_pending:
            return PendingIntent(
                intent=ctx_pending.intent,
                slots=ctx_pending.slots,
                missing_slots=ctx_pending.missing_slots,
                created_at=ctx_pending.created_at,
                source=ctx_pending.source,
                last_updated_at=ctx_pending.last_updated_at,
                turn_count=ctx_pending.turn_count
            )
        return None

    def _recognize_intent(self, message: str, context_data: Dict[str, Any]) -> IntentResult:
        """意图识别"""
        from app.services.intent_service import recognize_intents
        from app.domain.services.intent import get_intent_coordinator

        coordinator = get_intent_coordinator()
        basic = coordinator.detect_basic_intents(message)

        rule_result = recognize_intents(message)

        result = IntentResult(
            primary_intent=rule_result.get("primary_intent"),
            tool_key=rule_result.get("tool_key"),
            slots=rule_result.get("slots", {}),
            is_greeting=basic.get("is_greeting", False),
            is_goodbye=basic.get("is_goodbye", False),
            is_help=basic.get("is_help", False),
            is_confirmation=basic.get("is_confirmation", False),
            is_negation_intent=basic.get("is_negation_intent", False),
            is_negated=rule_result.get("is_negated", False),
            confidence=0.8,
            source="rule"
        )

        return result

    def _handle_confirmation(self, user_id: str, message: str, pending: PendingIntent) -> ProcessingResult:
        """处理确认意图"""
        logger.info(f"[COORDINATOR] User confirmed: user={user_id}, intent={pending.intent}")

        result = self._execute_plan(pending.intent, pending.slots)

        self.context_facade.intent_context.clear_pending(user_id)

        return ProcessingResult(
            action=ProcessingAction.TOOL_CALL,
            text=f"好的，正在执行【{pending.intent}】...",
            data=result,
            pending_intent=None
        )

    def _handle_greeting(self, user_id: str, message: str, pending: Optional[PendingIntent]) -> ProcessingResult:
        """处理问候（保留 pending）"""
        response = "您好！我是 XCAGI 智能助手，很高兴为您服务！"
        if pending:
            response += f"\n\n（您之前有一个{pending.intent}的任务尚未完成，是否需要继续？）"

        return ProcessingResult(
            action=ProcessingAction.GREETING,
            text=response,
            data={},
            pending_intent=pending
        )

    def _handle_goodbye(self, user_id: str, message: str, pending: Optional[PendingIntent]) -> ProcessingResult:
        """处理告别"""
        return ProcessingResult(
            action=ProcessingAction.GOODBYE,
            text="再见！祝您工作顺利！如有需要，随时联系我。",
            data={},
            pending_intent=pending
        )

    def _handle_help(self, user_id: str, message: str, pending: Optional[PendingIntent]) -> ProcessingResult:
        """处理帮助请求"""
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
            pending_intent=pending
        )

    def _handle_pending_continuation(
        self,
        user_id: str,
        message: str,
        intent_result: IntentResult,
        pending: PendingIntent
    ) -> ProcessingResult:
        """处理 pending 任务的续接"""
        logger.info(f"[COORDINATOR] Pending continuation: user={user_id}, pending={pending.intent}")

        merged = pending.merge_slots(intent_result.slots)

        is_complete, missing = self.slot_validator.validate(pending.intent, merged.slots)

        if is_complete:
            result = self._execute_plan(pending.intent, merged.slots)
            self.context_facade.intent_context.clear_pending(user_id)

            return ProcessingResult(
                action=ProcessingAction.TOOL_CALL,
                text=f"好的，{self._get_action_description(pending.intent, merged.slots)}...",
                data=result,
                pending_intent=None
            )
        else:
            updated = PendingIntent(
                intent=pending.intent,
                slots=merged.slots,
                missing_slots=missing,
                source=pending.source
            )

            ctx_pending = ContextPendingIntent(
                intent=updated.intent,
                slots=updated.slots,
                missing_slots=updated.missing_slots,
                source=updated.source
            )
            self.context_facade.intent_context.set_pending(user_id, ctx_pending)

            question = self.slot_validator.build_followup(pending.intent, missing, merged.slots)

            return ProcessingResult(
                action=ProcessingAction.SLOT_FILL,
                text=question,
                data={
                    "intent": pending.intent,
                    "slots": merged.slots,
                    "missing_slots": missing
                },
                pending_intent=updated
            )

    def _handle_slot_missing(
        self,
        user_id: str,
        message: str,
        intent_result: IntentResult,
        missing: List[str]
    ) -> ProcessingResult:
        """处理槽位缺失"""
        pending = PendingIntent(
            intent=intent_result.primary_intent,
            slots=intent_result.slots,
            missing_slots=missing,
            source=intent_result.source
        )

        ctx_pending = ContextPendingIntent(
            intent=pending.intent,
            slots=pending.slots,
            missing_slots=pending.missing_slots,
            source=pending.source
        )
        self.context_facade.intent_context.set_pending(user_id, ctx_pending)

        question = self.slot_validator.build_followup(
            intent_result.primary_intent,
            missing,
            intent_result.slots
        )

        return ProcessingResult(
            action=ProcessingAction.SLOT_FILL,
            text=question,
            data={
                "intent": intent_result.primary_intent,
                "slots": intent_result.slots,
                "missing_slots": missing
            },
            pending_intent=pending
        )

    def _handle_execution(
        self,
        user_id: str,
        message: str,
        intent_result: IntentResult
    ) -> ProcessingResult:
        """处理执行"""
        result = self._execute_plan(intent_result.tool_key, intent_result.slots)

        return ProcessingResult(
            action=ProcessingAction.TOOL_CALL,
            text=self._get_action_description(intent_result.tool_key, intent_result.slots),
            data=result,
            pending_intent=None
        )

    def _execute_plan(self, intent: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        """执行计划（委托给 TaskAgent）"""
        return self.task_agent.execute_plan(
            {"task_type": intent, "slots": slots},
            original_message=""
        )

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


class SlotValidator:
    """槽位验证器（配置化）"""

    REQUIRED_SLOTS = {
        "shipment_generate": {
            "required": ["unit_name", "model_number", "tin_spec", "quantity_tins"],
            "optional": ["contact_phone"],
        },
        "product_query": {
            "required": [],
            "optional": ["keyword", "model_number", "tin_spec"],
        },
        "customer_query": {
            "required": [],
            "optional": ["keyword", "customer_name"],
        },
        "customer_supplement": {
            "required": ["field_name", "field_value"],
            "optional": [],
        },
        "print_label": {
            "required": ["unit_name"],
            "optional": ["quantity_tins"],
        },
        "wechat_send": {
            "required": ["unit_name"],
            "optional": ["contact_person"],
        },
    }

    SLOT_LABELS = {
        "unit_name": "购买单位",
        "model_number": "编号",
        "tin_spec": "规格",
        "quantity_tins": "桶数",
        "contact_phone": "联系电话",
        "keyword": "关键词",
        "customer_name": "客户名称",
        "field_name": "字段名",
        "field_value": "字段值",
    }

    def validate(self, intent: str, slots: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证槽位"""
        if intent not in self.REQUIRED_SLOTS:
            return True, []

        required = self.REQUIRED_SLOTS[intent].get("required", [])
        missing = [s for s in required if not slots.get(s)]

        return len(missing) == 0, missing

    def build_followup(self, intent: str, missing_slots: List[str], current_slots: Dict[str, Any] = None) -> str:
        """生成追问文本"""
        if not missing_slots:
            return ""

        priority_order = ["unit_name", "model_number", "tin_spec", "quantity_tins"]

        for slot in priority_order:
            if slot in missing_slots:
                return self._build_single_question(intent, slot)

        return f"请问{missing_slots[0]}是多少？"

    def _build_single_question(self, intent: str, slot: str) -> str:
        """生成单个追问"""
        if intent == "shipment_generate":
            questions = {
                "unit_name": "请问要发货给哪个购买单位呢？",
                "model_number": "编号是多少呢？",
                "tin_spec": "规格是多少呢？",
                "quantity_tins": "这次需要多少桶呢？",
            }
            return questions.get(slot, f"请问{slot}是多少呢？")

        return f"请问{self.SLOT_LABELS.get(slot, slot)}是多少呢？"


_coordinator: Optional[UnifiedConversationCoordinator] = None


def get_conversation_coordinator() -> UnifiedConversationCoordinator:
    """获取编排器单例"""
    global _coordinator
    if _coordinator is None:
        _coordinator = UnifiedConversationCoordinator()
    return _coordinator
