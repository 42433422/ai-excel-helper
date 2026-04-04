"""
回答生成模块
功能：基于意图生成自然语言回答
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """回答生成器"""

    def __init__(self):
        self._default_responses = self._init_default_responses()

    def _init_default_responses(self) -> Dict[str, str]:
        """初始化默认回答"""
        return {
            "greeting": "您好，我是深圳奇士美的AI助手，很高兴为您服务！",
            "goodbye": "感谢您的来电，祝您工作顺利！",
            "help": "我可以帮您查询产品信息、处理出货单、管理库存等，请告诉我您需要什么帮助？",
            "unknown": "抱歉，我不太理解您的意思，请您再详细描述一下？",
            "product_query": "好的，我来帮您查询产品信息...",
            "shipment": "收到，我来帮您处理出货单...",
            "inventory": "好的，我来帮您查询库存情况...",
        }

    def generate(self, intent_result: Optional[Dict[str, Any]], text: str = "") -> str:
        """生成回答"""
        if not intent_result:
            return self._default_responses["unknown"]

        primary_intent = intent_result.get("primary_intent", "")
        is_greeting = intent_result.get("is_greeting", False)
        is_goodbye = intent_result.get("is_goodbye", False)
        is_help = intent_result.get("is_help", False)
        is_negated = intent_result.get("is_negated", False)

        if is_negated:
            return "好的，明白了。"

        if is_greeting:
            return self._default_responses["greeting"]

        if is_goodbye:
            return self._default_responses["goodbye"]

        if is_help:
            return self._default_responses["help"]

        if primary_intent:
            intent_lower = primary_intent.lower()
            if "product" in intent_lower:
                return self._default_responses["product_query"]
            if "shipment" in intent_lower or "order" in intent_lower:
                return self._default_responses["shipment"]
            if "inventory" in intent_lower or "stock" in intent_lower:
                return self._default_responses["inventory"]

        return self._default_responses["unknown"]

# 4243342
