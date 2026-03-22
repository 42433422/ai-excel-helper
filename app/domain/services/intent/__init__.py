# -*- coding: utf-8 -*-
"""
意图识别策略模块

提供各种意图检测策略的实现
"""

from app.domain.services.intent.base_strategy import IntentDetectionStrategy
from app.domain.services.intent.coordinator import (
    IntentRecognitionCoordinator,
    get_intent_coordinator,
)
from app.domain.services.intent.goodbye_strategy import GoodbyeStrategy
from app.domain.services.intent.greeting_strategy import GreetingStrategy
from app.domain.services.intent.help_request_strategy import HelpRequestStrategy
from app.domain.services.intent.negation_strategy import NegationStrategy

__all__ = [
    "IntentDetectionStrategy",
    "GreetingStrategy",
    "GoodbyeStrategy",
    "HelpRequestStrategy",
    "NegationStrategy",
    "IntentRecognitionCoordinator",
    "get_intent_coordinator",
]
