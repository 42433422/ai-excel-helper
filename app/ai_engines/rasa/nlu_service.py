# -*- coding: utf-8 -*-
"""
RASA NLU 意图识别服务

此文件迁移自 app/services/rasa_nlu_service.py
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class RasaNLUService:
    """
    RASA NLU 意图识别服务
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.model = None

    def load_model(self) -> bool:
        if not self.model_path:
            logger.info("RASA NLU 模型路径未配置")
            return False
        return True

    def parse(self, text: str) -> Dict[str, Any]:
        if not text:
            return {"intent": {"name": "unk", "confidence": 0.0}}
        return {"intent": {"name": "unk", "confidence": 0.0}}


_rasa_nlu_service: Optional[RasaNLUService] = None


def get_rasa_nlu_service() -> RasaNLUService:
    global _rasa_nlu_service
    if _rasa_nlu_service is None:
        _rasa_nlu_service = RasaNLUService()
    return _rasa_nlu_service
