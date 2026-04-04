"""
意图处理模块
功能：调用统一意图识别器
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class IntentHandler:
    """意图处理器"""

    def __init__(self):
        self._recognizer = None
        self._init_recognizer()

    def _init_recognizer(self):
        """初始化统一意图识别器"""
        try:
            from app.services.unified_intent_recognizer import get_unified_intent_recognizer
            self._recognizer = get_unified_intent_recognizer()
            logger.info("Unified intent recognizer initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize intent recognizer: {e}")
            self._recognizer = None

    def recognize(self, text: str, context: Optional[List[Dict]] = None) -> Optional[Dict[str, Any]]:
        """识别意图"""
        if not self._recognizer:
            logger.warning("Intent recognizer not available")
            return None

        try:
            result = self._recognizer.recognize(text, context)
            logger.info(f"Intent recognized: {result.primary_intent}")

            return {
                "primary_intent": result.primary_intent,
                "tool_key": result.tool_key,
                "intent_hints": result.intent_hints,
                "is_negated": result.is_negated,
                "is_greeting": result.is_greeting,
                "is_goodbye": result.is_goodbye,
                "is_help": result.is_help,
                "is_confirmation": result.is_confirmation,
                "slots": result.slots,
                "confidence": result.confidence,
                "sources_used": result.sources_used,
            }
        except Exception as e:
            logger.error(f"Intent recognition failed: {e}")
            return None

    def is_available(self) -> bool:
        """检查是否可用"""
        return self._recognizer is not None

# 4243342
