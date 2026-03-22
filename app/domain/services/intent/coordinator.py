# -*- coding: utf-8 -*-
"""
意图识别协调器

组合多种意图检测策略，提供统一的识别接口
"""

from typing import Any, Dict, List, Optional, Tuple

from app.domain.services.intent.base_strategy import IntentDetectionStrategy
from app.domain.services.intent.goodbye_strategy import GoodbyeStrategy
from app.domain.services.intent.greeting_strategy import GreetingStrategy
from app.domain.services.intent.help_request_strategy import HelpRequestStrategy
from app.domain.services.intent.negation_strategy import NegationStrategy


class IntentRecognitionCoordinator:
    """意图识别协调器 - 组合多种策略"""

    def __init__(self):
        self._strategies: Dict[str, IntentDetectionStrategy] = {}
        self._initialize_strategies()

    def _initialize_strategies(self):
        self._strategies["greeting"] = GreetingStrategy()
        self._strategies["goodbye"] = GoodbyeStrategy()
        self._strategies["help"] = HelpRequestStrategy()
        self._strategies["negation"] = NegationStrategy()

    def detect_greeting(self, message: str) -> bool:
        return self._strategies["greeting"].detect(message)

    def detect_goodbye(self, message: str) -> bool:
        return self._strategies["goodbye"].detect(message)

    def detect_help(self, message: str) -> bool:
        return self._strategies["help"].detect(message)

    def detect_negation(self, message: str, action_keywords: Optional[List[str]] = None) -> bool:
        context = {"action_keywords": action_keywords} if action_keywords else None
        return self._strategies["negation"].detect(message, context)

    def detect_confirmation(self, message: str) -> bool:
        from resources.config.intent_config import get_intent_config
        config = get_intent_config()
        confirmation_keywords = config.get("confirmation_keywords", [])
        msg = (message or "").strip()
        return any(kw == msg or msg.startswith(kw) for kw in confirmation_keywords)

    def detect_negation_intent(self, message: str) -> bool:
        from resources.config.intent_config import get_intent_config
        config = get_intent_config()
        negation_keywords = config.get("negation_keywords", [])
        msg = (message or "").strip()
        return any(kw == msg or msg.startswith(kw) for kw in negation_keywords)

    def detect_basic_intents(self, message: str) -> Dict[str, bool]:
        return {
            "is_greeting": self.detect_greeting(message),
            "is_goodbye": self.detect_goodbye(message),
            "is_help": self.detect_help(message),
            "is_confirmation": self.detect_confirmation(message),
            "is_negation_intent": self.detect_negation_intent(message),
        }


_intent_coordinator: Optional[IntentRecognitionCoordinator] = None


def get_intent_coordinator() -> IntentRecognitionCoordinator:
    """获取意图识别协调器单例"""
    global _intent_coordinator
    if _intent_coordinator is None:
        _intent_coordinator = IntentRecognitionCoordinator()
    return _intent_coordinator
