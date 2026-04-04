# -*- coding: utf-8 -*-
"""
否定意图检测策略（区分“否定式动作”与“否定意图”）

否定意图：例如“不要生成发货单 / 算了 / 取消”等，属于对话层面明确表达“不做”。
本策略仅判断是否包含否定意图关键词，不负责阻断工具（阻断由 intent_service 的 is_negation 完成）。
"""

from typing import Any, Dict, List, Optional

from app.domain.services.intent.base_strategy import IntentDetectionStrategy
from resources.config.intent_config import get_intent_config


class NegationIntentStrategy(IntentDetectionStrategy):
    """否定意图检测策略"""

    def __init__(self):
        self._config = get_intent_config()
        self._keywords: List[str] = self._config.get("negation_keywords", [])

    def detect(self, message: str, context: Optional[Dict[str, Any]] = None) -> bool:
        if message is None:
            return False
        msg = (message or "").strip()
        if not msg:
            return False
        return any(kw == msg or msg.startswith(kw) for kw in self._keywords)

    def get_confidence(self, message: str) -> float:
        if not message:
            return 0.0
        msg = (message or "").strip()
        return 0.9 if any(kw == msg or msg.startswith(kw) for kw in self._keywords) else 0.0

