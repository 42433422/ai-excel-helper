# -*- coding: utf-8 -*-
"""
意图确认服务

管理待确认意图和槽位合并逻辑

原始模块位于 app/services/intent_confirmation_service.py
此文件在 DDD 迁移完成前提供委托。
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IntentConfirmationService:
    """
    意图确认服务

    管理待确认意图和槽位合并逻辑
    """

    def __init__(self):
        self._pending_intents: Dict[str, Dict[str, Any]] = {}

    def get_pending_intent(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._pending_intents.get(user_id)

    def set_pending_intent(self, user_id: str, intent_data: Dict[str, Any]) -> None:
        self._pending_intents[user_id] = intent_data

    def clear_pending_intent(self, user_id: str) -> None:
        self._pending_intents.pop(user_id, None)

    def merge_slots(self, user_id: str, new_slots: Dict[str, Any]) -> Dict[str, Any]:
        pending = self._pending_intents.get(user_id)
        if not pending:
            return new_slots

        merged = dict(pending.get("slots", {}))
        for key, value in new_slots.items():
            if value and (key not in merged or not merged[key]):
                merged[key] = value

        return merged

    def check_and_build_prompt(self, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        intent = intent_result.get("final_intent", "")
        slots = intent_result.get("slots", {})

        required_slots = self._get_required_slots(intent)
        missing_slots = [s for s in required_slots if not slots.get(s)]

        if not missing_slots:
            return {"status": "complete", "missing_slots": []}

        questions = {
            "unit_name": "请问是哪个客户/购货单位？",
            "product_name": "请问是哪个产品？",
            "quantity": "请问需要多少数量？",
            "spec": "请问是什么规格？",
        }

        question = questions.get(missing_slots[0], f"请问 {missing_slots[0]} 是多少？")

        return {
            "status": "missing_slots",
            "missing_slots": missing_slots,
            "question": question,
            "pending_data": {
                "intent": intent,
                "slots": slots,
                "missing_slots": missing_slots,
            },
        }

    def _get_required_slots(self, intent: str) -> List[str]:
        required_map = {
            "shipment_generate": ["unit_name"],
            "products": ["keyword"],
            "customers": [],
            "shipments": [],
            "print_label": ["unit_name"],
        }
        return required_map.get(intent, [])


_confirmation_service: Optional[IntentConfirmationService] = None


def get_confirmation_service() -> IntentConfirmationService:
    global _confirmation_service
    if _confirmation_service is None:
        _confirmation_service = IntentConfirmationService()
    return _confirmation_service
