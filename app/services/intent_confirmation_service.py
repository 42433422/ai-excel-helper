# -*- coding: utf-8 -*-
"""
意图反向询问服务

当识别到意图但缺失必要槽位时，自动追问用户补充
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

INTENT_REQUIRED_SLOTS = {
    "shipment_generate": {
        "required": ["unit_name"],
        "optional": ["quantity_tins", "tin_spec", "contact_phone"],
        "prompts": {
            "unit_name": "请问要发货给哪个购买单位？",
            "quantity_tins": "请问需要多少桶？",
            "tin_spec": "请问规格是多少？",
            "contact_phone": "请问联系电话是多少？",
        }
    },
    "customer_supplement": {
        "required": [],
        "optional": ["contact_person", "contact_phone", "contact_address"],
        "prompts": {
            "contact_person": "请问联系人是谁？",
            "contact_phone": "请问联系电话是多少？",
            "contact_address": "请问联系地址是多少？",
        }
    },
    "customer_edit": {
        "required": ["unit_name"],
        "optional": ["contact_person", "contact_phone"],
        "prompts": {
            "unit_name": "请问要修改哪个客户的信息？",
            "contact_person": "请问新的联系人是谁？",
            "contact_phone": "请问新的联系电话是多少？",
        }
    },
    "wechat_send": {
        "required": ["unit_name"],
        "optional": ["contact_person"],
        "prompts": {
            "unit_name": "请问要发微信给哪个客户？",
            "contact_person": "请问联系人的姓名是？",
        }
    },
    "products": {
        "required": [],
        "optional": ["unit_name", "keyword"],
        "prompts": {
            "unit_name": "请问要查看哪个购买单位的产品？",
            "keyword": "请问要搜索什么关键词？",
        }
    },
    "shipments": {
        "required": [],
        "optional": ["unit_name", "order_no"],
        "prompts": {
            "unit_name": "请问要查看哪个客户的发货记录？",
            "order_no": "请问订单编号是多少？",
        }
    },
    "print_label": {
        "required": ["unit_name"],
        "optional": ["quantity_tins"],
        "prompts": {
            "unit_name": "请问要打印哪个客户的标签？",
            "quantity_tins": "请问要打印多少个标签？",
        }
    },
    "materials": {
        "required": [],
        "optional": ["keyword"],
        "prompts": {
            "keyword": "请问要查询什么材料？",
        }
    },
}

FALLBACK_QUESTIONS = {
    "shipment_generate": "请告诉我发货给哪个单位，需要多少桶，什么规格？",
    "customer_supplement": "请告诉我要补充的客户信息（联系人、电话、地址）？",
    "customer_edit": "请告诉我要修改哪个客户，以及要修改什么信息？",
    "wechat_send": "请告诉我要发微信给哪个客户？",
    "products": "请告诉我要查看哪个客户的产品，或者搜索什么关键词？",
    "shipments": "请告诉我要查看哪个客户的发货记录？",
    "print_label": "请告诉我要打印哪个客户的标签？",
    "materials": "请告诉我要查询什么材料？",
}


def check_missing_slots(intent: str, slots: Dict[str, Any]) -> List[str]:
    """
    检查缺失的必填槽位

    Args:
        intent: 意图名称
        slots: 已提取的槽位

    Returns:
        缺失的必填槽位列表
    """
    if intent not in INTENT_REQUIRED_SLOTS:
        return []

    required_slots = INTENT_REQUIRED_SLOTS[intent].get("required", [])
    missing = []

    for slot in required_slots:
        value = slots.get(slot)
        if not value or (isinstance(value, str) and not value.strip()):
            missing.append(slot)

    return missing


def generate_followup_question(intent: str, missing_slots: List[str]) -> str:
    """
    生成追问问题

    Args:
        intent: 意图名称
        missing_slots: 缺失的槽位列表

    Returns:
        追问问题文本
    """
    if intent in INTENT_REQUIRED_SLOTS:
        prompts = INTENT_REQUIRED_SLOTS[intent].get("prompts", {})
        questions = [prompts.get(slot, f"请问{slot}是多少？") for slot in missing_slots if slot in prompts]

        if questions:
            return " ".join(questions)

    if intent in FALLBACK_QUESTIONS:
        return FALLBACK_QUESTIONS[intent]

    return "请提供更多信息？"


def build_slot_fill_prompt(intent: str, slots: Dict[str, Any], missing_slots: List[str]) -> Dict[str, Any]:
    """
    构建槽位填充提示

    Args:
        intent: 意图名称
        slots: 已提取的槽位
        missing_slots: 缺失的槽位

    Returns:
        槽位填充信息字典
    """
    prompts = {}
    if intent in INTENT_REQUIRED_SLOTS:
        slot_prompts = INTENT_REQUIRED_SLOTS[intent].get("prompts", {})
        for slot in missing_slots:
            prompts[slot] = slot_prompts.get(slot, f"{slot}")

    return {
        "intent": intent,
        "missing_slots": missing_slots,
        "current_slots": slots,
        "questions": prompts,
        "question_text": generate_followup_question(intent, missing_slots),
    }


class IntentConfirmationService:
    """
    意图确认和追问服务

    用于：
    1. 检查意图所需槽位是否完整
    2. 缺失时生成追问
    3. 已完整时确认执行
    """

    def __init__(self):
        self.pending_intents: Dict[str, Dict[str, Any]] = {}

    def check_and_build_prompt(self, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查槽位并构建提示

        Args:
            intent_result: 意图识别结果

        Returns:
            处理结果，包含：
            - status: "complete" | "missing_slots" | "unclear"
            - intent: 意图名称
            - slots: 槽位信息
            - question: 追问问题（如果缺失）
            - pending_data: 待确认数据（用于上下文）
        """
        intent = (
            intent_result.get("final_intent")
            or intent_result.get("primary_intent")
            or intent_result.get("tool_key")
            or intent_result.get("deepseek_intent")
        )
        slots = intent_result.get("slots", {})

        if not intent or intent == "unk":
            return {
                "status": "unclear",
                "intent": None,
                "slots": {},
                "question": "抱歉，我没有理解您的意思。请告诉我您想做什么？",
                "pending_data": None,
            }

        missing = check_missing_slots(intent, slots)

        if missing:
            prompt_data = build_slot_fill_prompt(intent, slots, missing)
            return {
                "status": "missing_slots",
                "intent": intent,
                "slots": slots,
                "missing_slots": missing,
                "question": prompt_data["question_text"],
                "pending_data": {
                    "intent": intent,
                    "slots": slots,
                    "missing_slots": missing,
                },
            }

        return {
            "status": "complete",
            "intent": intent,
            "slots": slots,
            "question": None,
            "pending_data": {
                "intent": intent,
                "slots": slots,
                "missing_slots": [],
            },
        }

    def set_pending_intent(self, user_id: str, intent_data: Dict[str, Any]) -> None:
        """设置待填充的意图"""
        self.pending_intents[user_id] = intent_data

    def get_pending_intent(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取待填充的意图"""
        return self.pending_intents.get(user_id)

    def clear_pending_intent(self, user_id: str) -> None:
        """清除待填充的意图"""
        if user_id in self.pending_intents:
            del self.pending_intents[user_id]

    def merge_slots(self, user_id: str, new_slots: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并新槽位到待填充意图

        Args:
            user_id: 用户ID
            new_slots: 新提取的槽位

        Returns:
            合并后的槽位
        """
        pending = self.get_pending_intent(user_id)
        if not pending:
            return new_slots

        merged = pending.get("slots", {}).copy()
        merged.update(new_slots)

        if "unit_name" in merged:
            from app.infrastructure.lookups.purchase_unit_resolver import resolve_purchase_unit
            resolved = resolve_purchase_unit(merged["unit_name"])
            if resolved:
                merged["unit_name"] = resolved.unit_name

        return merged


_confirmation_service: Optional[IntentConfirmationService] = None


def get_confirmation_service() -> IntentConfirmationService:
    """获取确认服务单例"""
    global _confirmation_service
    if _confirmation_service is None:
        _confirmation_service = IntentConfirmationService()
    return _confirmation_service
