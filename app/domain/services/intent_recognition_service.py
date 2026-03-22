"""
意图识别领域服务

负责识别用户意图的核心业务逻辑
这是领域层的核心服务，不依赖任何基础设施层
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class IntentType(Enum):
    """意图类型枚举"""
    SHIPMENT = "shipment"
    PRODUCT = "product"
    CUSTOMER = "customer"
    SEARCH = "search"
    IMPORT = "import"
    EXPORT = "export"
    PRINT = "print"
    UNKNOWN = "unknown"


class IntentRecognitionService:
    """
    意图识别领域服务

    核心职责：
    - 解析用户消息识别意图
    - 提取实体和参数
    - 判断意图置信度
    """

    def __init__(self):
        self._intent_keywords = {
            IntentType.SHIPMENT: [
                "发货", "发货单", "出货", "订单", "开单", "打单"
            ],
            IntentType.PRODUCT: [
                "产品", "商品", "货物", "型号", "规格"
            ],
            IntentType.CUSTOMER: [
                "客户", "单位", "公司", "联系人"
            ],
            IntentType.SEARCH: [
                "查询", "搜索", "查找", "看看"
            ],
            IntentType.IMPORT: [
                "导入", "批量", "Excel", "表格"
            ],
            IntentType.EXPORT: [
                "导出", "下载", "生成文件"
            ],
            IntentType.PRINT: [
                "打印", "标签", "小票"
            ]
        }

    def recognize(self, message: str) -> Tuple[IntentType, float, Dict[str, Any]]:
        """
        识别用户意图

        Args:
            message: 用户消息

        Returns:
            (意图类型, 置信度, 提取的参数)
        """
        message_lower = message.lower()

        best_intent = IntentType.UNKNOWN
        best_score = 0.0
        params = {}

        for intent_type, keywords in self._intent_keywords.items():
            score = self._calculate_keyword_score(message_lower, keywords)
            if score > best_score:
                best_score = score
                best_intent = intent_type
                params = self._extract_parameters(message, intent_type)

        if best_score < 0.3:
            return IntentType.UNKNOWN, 0.0, {}

        return best_intent, best_score, params

    def _calculate_keyword_score(self, message: str, keywords: List[str]) -> float:
        """计算关键词匹配分数"""
        matches = sum(1 for kw in keywords if kw in message)
        return matches / len(keywords) if keywords else 0.0

    def _extract_parameters(self, message: str, intent: IntentType) -> Dict[str, Any]:
        """提取意图相关的参数"""
        params = {}

        if intent == IntentType.SHIPMENT:
            params = self._extract_shipment_params(message)
        elif intent == IntentType.PRODUCT:
            params = self._extract_product_params(message)
        elif intent == IntentType.CUSTOMER:
            params = self._extract_customer_params(message)

        return params

    def _extract_shipment_params(self, message: str) -> Dict[str, Any]:
        """提取发货单相关参数"""
        params = {}
        import re

        quantity_pattern = r'(\d+)\s*(桶|箱|个|件|台|套)'
        quantities = re.findall(quantity_pattern, message)
        if quantities:
            params['quantities'] = [(int(q), unit) for q, unit in quantities]

        return params

    def _extract_product_params(self, message: str) -> Dict[str, Any]:
        """提取产品相关参数"""
        params = {}
        return params

    def _extract_customer_params(self, message: str) -> Dict[str, Any]:
        """提取客户相关参数"""
        params = {}
        return params

    def batch_recognize(self, messages: List[str]) -> List[Tuple[IntentType, float, Dict[str, Any]]]:
        """
        批量识别意图

        Args:
            messages: 用户消息列表

        Returns:
            识别结果列表
        """
        return [self.recognize(msg) for msg in messages]


def get_intent_recognition_service() -> IntentRecognitionService:
    """获取意图识别服务实例"""
    return IntentRecognitionService()
