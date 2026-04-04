# -*- coding: utf-8 -*-
"""
领域服务层

此模块提供领域服务（Domain Services），包含无状态的业务逻辑。
"""

from app.domain.services.intent_confirmation_service import (
    IntentConfirmationService,
    get_confirmation_service,
)
from app.domain.services.intent_recognition_service import (
    IntentRecognitionService,
    RecognizerResult,
    get_intent_recognition_service,
    IntentType,
)

# Keep legacy for backward compatibility (will be deprecated)
from app.domain.services.unified_intent_recognizer import (
    UnifiedIntentRecognizer,
    get_unified_intent_recognizer,
)

__all__ = [
    "IntentConfirmationService",
    "get_confirmation_service",
    "IntentRecognitionService",
    "RecognizerResult",
    "get_intent_recognition_service",
    "IntentType",
    # legacy
    "UnifiedIntentRecognizer",
    "get_unified_intent_recognizer",
]
