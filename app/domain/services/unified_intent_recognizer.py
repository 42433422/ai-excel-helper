# -*- coding: utf-8 -*-
"""
统一意图识别器

整合多种意图识别引擎（规则、BERT、DeepSeek、RASA）

原始模块位于 app/services/unified_intent_recognizer.py
此文件在 DDD 迁移完成前提供委托。
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class UnifiedIntentRecognizer:
    """
    统一意图识别器

    整合多种意图识别引擎（规则、BERT、DeepSeek、RASA）
    """

    def __init__(self):
        self.bert_recognizer = None
        self.deepseek_recognizer = None
        self.rasa_recognizer = None
        self.distilled_recognizer = None
        self.rule_recognizer = None
        self._initialized = False

    def load(self) -> bool:
        if self._initialized:
            return True

        try:
            from app.services.bert_intent_service import BertIntentClassifier
            self.bert_recognizer = BertIntentClassifier()
            self.bert_recognizer.load_model()
            logger.info("BERT识别器已加载")
        except Exception as e:
            logger.warning(f"BERT识别器加载失败：{e}")

        try:
            from app.services.distilled_intent_service import DistilledIntentClassifier
            self.distilled_recognizer = DistilledIntentClassifier()
            self.distilled_recognizer.load_model()
            logger.info("蒸馏模型识别器已加载")
        except Exception as e:
            logger.warning(f"蒸馏模型加载失败：{e}")

        try:
            from app.services.deepseek_intent_service import DeepseekIntentClassifier
            self.deepseek_recognizer = DeepseekIntentClassifier()
            self.deepseek_recognizer.load_model()
            logger.info("DeepSeek识别器已加载")
        except Exception as e:
            logger.warning(f"DeepSeek识别器加载失败：{e}")

        try:
            from app.services.rasa_nlu_service import RasaNLUService
            self.rasa_recognizer = RasaNLUService()
            self.rasa_recognizer.load_model()
            logger.info("RASA NLU已加载")
        except Exception as e:
            logger.warning(f"RASA NLU加载失败：{e}")

        self._initialized = True
        logger.info("混合意图服务已加载")
        return True

    def recognize(self, text: str) -> Dict[str, Any]:
        if not self._initialized:
            self.load()

        if not text or not text.strip():
            return {"intent": "unk", "confidence": 0.0, "source": "unified"}

        if self.distilled_recognizer:
            try:
                result = self.distilled_recognizer.predict(text)
                if result.get("confidence", 0) > 0.7:
                    result["source"] = "distilled"
                    return result
            except Exception as e:
                logger.warning(f"蒸馏模型预测失败：{e}")

        if self.bert_recognizer:
            try:
                result = self.bert_recognizer.predict(text)
                if result.get("confidence", 0) > 0.7:
                    result["source"] = "bert"
                    return result
            except Exception as e:
                logger.warning(f"BERT预测失败：{e}")

        return {"intent": "unk", "confidence": 0.0, "source": "unified"}


_unified_intent_recognizer: Optional[UnifiedIntentRecognizer] = None


def get_unified_intent_recognizer() -> UnifiedIntentRecognizer:
    global _unified_intent_recognizer
    if _unified_intent_recognizer is None:
        _unified_intent_recognizer = UnifiedIntentRecognizer()
        _unified_intent_recognizer.load()
    return _unified_intent_recognizer
