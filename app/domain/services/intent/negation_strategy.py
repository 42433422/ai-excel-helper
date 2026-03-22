# -*- coding: utf-8 -*-
"""
否定检测策略
"""

from typing import Any, Dict, List, Optional

from app.domain.services.intent.base_strategy import IntentDetectionStrategy
from resources.config.intent_config import get_intent_config


class NegationStrategy(IntentDetectionStrategy):
    """否定式指令检测策略"""

    def __init__(self):
        self._config = get_intent_config()
        negation_config = self._config.get("negation", {})
        self._prefixes: List[str] = negation_config.get("prefixes", [])
        self._phrases: List[str] = negation_config.get("phrases", [])

    def detect(self, message: str, context: Optional[Dict[str, Any]] = None) -> bool:
        if not message:
            return False

        msg_lower = message.lower()

        for phrase in self._phrases:
            if phrase in msg_lower or phrase in message:
                return True

        for prefix in self._prefixes:
            if msg_lower.startswith(prefix) or message.startswith(prefix):
                return True
            if (" " + prefix in msg_lower) or ("，" + prefix in msg_lower):
                return True

        if context and context.get("action_keywords"):
            action_keywords = context["action_keywords"]
            for kw in action_keywords:
                idx = msg_lower.find(kw.lower())
                if idx == -1:
                    continue
                before = msg_lower[:idx]
                for prefix in self._prefixes:
                    if prefix in before or before.endswith(prefix):
                        return True

        return False

    def get_confidence(self, message: str) -> float:
        if not message:
            return 0.0

        msg_lower = message.lower()

        for phrase in self._phrases:
            if phrase in msg_lower:
                return 0.9

        for prefix in self._prefixes:
            if msg_lower.startswith(prefix):
                return 0.8

        return 0.0
