# -*- coding: utf-8 -*-
"""
告别语检测策略
"""

from typing import Any, Dict, List, Optional

from app.domain.services.intent.base_strategy import IntentDetectionStrategy
from resources.config.intent_config import get_intent_config


class GoodbyeStrategy(IntentDetectionStrategy):
    """告别语检测策略"""

    def __init__(self):
        self._config = get_intent_config()
        goodbye_config = self._config.get("goodbye", {})
        self._patterns: List[str] = goodbye_config.get("patterns", [])
        self._max_length: int = 25

    def detect(self, message: str, context: Optional[Dict[str, Any]] = None) -> bool:
        if not message or len(message) > self._max_length:
            return False

        msg_lower = message.lower()

        for p in self._patterns:
            if p in msg_lower or p in message:
                return True

        return False

    def get_confidence(self, message: str) -> float:
        if not message:
            return 0.0

        msg_lower = message.lower()

        for i, p in enumerate(self._patterns):
            if p in msg_lower:
                return 1.0 - (i * 0.1)

        return 0.0
