# -*- coding: utf-8 -*-
"""
确认意图检测策略

把确认关键词判断从 coordinator 里抽离出来，避免 coordinator 在方法调用时直接依赖配置模块。
"""

from typing import Any, Dict, List, Optional

from app.domain.services.intent.base_strategy import IntentDetectionStrategy
from resources.config.intent_config import get_intent_config


class ConfirmationStrategy(IntentDetectionStrategy):
    """确认意图检测策略"""

    def __init__(self):
        self._config = get_intent_config()
        self._keywords: List[str] = self._config.get("confirmation_keywords", [])

    def detect(self, message: str, context: Optional[Dict[str, Any]] = None) -> bool:
        if message is None:
            return False
        msg = (message or "").strip()
        if not msg:
            return False
        return any(kw == msg or msg.startswith(kw) for kw in self._keywords)

    def get_confidence(self, message: str) -> float:
        # 只做粗粒度置信度，不影响规则引擎的主决策流程
        if not message:
            return 0.0
        msg = (message or "").strip()
        return 0.9 if any(kw == msg or msg.startswith(kw) for kw in self._keywords) else 0.0

