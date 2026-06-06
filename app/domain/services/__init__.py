"""
领域服务层

此模块提供领域服务（Domain Services），包含无状态的业务逻辑。
意图识别已迁移到 NeuroDDD 的 IntentReflexArc + ProcessorCoordinator 管道。
"""

from app.domain.services.unified_intent_recognizer import (
    UnifiedIntentRecognizer,
    get_unified_intent_recognizer,
)

__all__ = [
    "UnifiedIntentRecognizer",
    "get_unified_intent_recognizer",
]
