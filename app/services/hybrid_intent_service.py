# -*- coding: utf-8 -*-
"""
混合意图识别服务：规则 + RASA NLU + BERT 预训练模型

结合多种系统的优势:
- 规则系统: 快速、确定性高、处理否定和特殊格式
- RASA NLU: 处理变体表达、口语化、拼写容错
- BERT 模型: 深度语义理解、高精度意图分类
"""

from __future__ import annotations

import logging

from typing import Any, Dict, Optional

from .intent_service import recognize_intents as rule_recognize_intents
from .rasa_nlu_service import RasaNLUService, get_rasa_nlu_service

logger = logging.getLogger(__name__)

INTENT_MAPPING = {
    "shipment_generate": "shipment_generate",
    "customers": "customers",
    "products": "products",
    "shipments": "shipments",
    "wechat_send": "wechat_send",
    "print_label": "print_label",
    "upload_file": "upload_file",
    "materials": "materials",
    "shipment_template": "shipment_template",
    "template_extract": "template_extract",
    "excel_decompose": "excel_decompose",
    "business_docking": "business_docking",
    "template_preview": "template_preview",
    "shipment_records": "shipment_records",
    "wechat": "wechat",
    "printer_list": "printer_list",
    "settings": "settings",
    "tools_table": "tools_table",
    "other_tools": "other_tools",
    "ai_ecosystem": "ai_ecosystem",
    "show_images": "show_images",
    "show_videos": "show_videos",
    "greet": "greet",
    "goodbye": "goodbye",
    "help": "help",
    "negation_test": "negation",
    "customer_export": "customer_export",
    "customer_edit": "customer_edit",
    "customer_supplement": "customer_supplement",
}

BERT_INTENT_MAPPING = {
    "shipment_generate": "shipment_generate",
    "customers": "customers",
    "products": "products",
    "shipments": "shipments",
    "wechat_send": "wechat_send",
    "print_label": "print_label",
    "upload_file": "upload_file",
    "materials": "materials",
    "shipment_template": "shipment_template",
    "template_extract": "template_extract",
    "excel_decompose": "excel_decompose",
    "business_docking": "business_docking",
    "template_preview": "template_preview",
    "shipment_records": "shipment_records",
    "wechat": "wechat",
    "printer_list": "printer_list",
    "settings": "settings",
    "tools_table": "tools_table",
    "other_tools": "other_tools",
    "ai_ecosystem": "ai_ecosystem",
    "show_images": "show_images",
    "show_videos": "show_videos",
    "greet": "greet",
    "goodbye": "goodbye",
    "help": "help",
    "negation": "negation",
    "customer_export": "customer_export",
    "customer_edit": "customer_edit",
    "customer_supplement": "customer_supplement",
}


class HybridIntentService:
    """
    混合意图识别服务

    融合规则系统、RASA NLU 和 BERT 模型的优势:
    - 规则系统: 快速、确定性高、处理否定和特殊格式
    - RASA NLU: 处理变体表达、口语化、拼写容错
    - BERT 模型: 深度语义理解、高精度意图分类
    """

    def __init__(
        self,
        use_rasa: bool = False,
        rasa_service: Optional[RasaNLUService] = None,
        rasa_confidence_threshold: float = 0.7,
        rasa_fallback_to_rule: bool = True,
        use_bert: bool = True,
        bert_model_path: Optional[str] = None,
        bert_confidence_threshold: float = 0.7,
        bert_fallback_to_rule: bool = True,
    ):
        """
        初始化混合意图服务

        Args:
            use_rasa: 是否启用 RASA
            rasa_service: RASA 服务实例（可选）
            rasa_confidence_threshold: RASA 置信度阈值
            rasa_fallback_to_rule: RASA 不可用时是否回退到规则
            use_bert: 是否启用 BERT 模型
            bert_model_path: BERT 模型路径
            bert_confidence_threshold: BERT 置信度阈值
            bert_fallback_to_rule: BERT 不可用时是否回退到规则
        """
        self.use_rasa = use_rasa
        self.rasa_service = rasa_service
        self.rasa_confidence_threshold = rasa_confidence_threshold
        self.rasa_fallback_to_rule = rasa_fallback_to_rule

        self.use_bert = use_bert
        self.bert_model_path = bert_model_path
        self.bert_confidence_threshold = bert_confidence_threshold
        self.bert_fallback_to_rule = bert_fallback_to_rule
        self.bert_classifier = None
        self.bert_service = None

        if self.use_bert:
            self._init_bert_service()

    def _init_bert_service(self):
        """初始化 BERT 服务"""
        try:
            from .bert_intent_service import (
                BertIntentService,
                get_bert_intent_service,
            )
            self.bert_service = get_bert_intent_service(
                model_path=self.bert_model_path,
                model_name="bert-base-chinese",
                confidence_threshold=self.bert_confidence_threshold,
                use_fallback=self.bert_fallback_to_rule,
            )
            logger.info(f"BERT 意图服务已初始化，模型路径: {self.bert_model_path}")
        except Exception as e:
            logger.warning(f"无法初始化 BERT 服务: {e}")
            self.use_bert = False

    async def recognize(self, message: str) -> Dict[str, Any]:
        """
        混合意图识别

        Args:
            message: 用户消息

        Returns:
            意图识别结果（兼容原有格式）
        """
        rule_result = rule_recognize_intents(message)
        rule_result["sources_used"] = ["rule"]

        if self.use_bert and self.bert_service:
            bert_result = self.bert_service.recognize(message)
            rule_result["bert_intent"] = bert_result.get("intent")
            rule_result["bert_confidence"] = bert_result.get("confidence", 0.0)
            rule_result["bert_available"] = True
            rule_result["sources_used"].append("bert")

            if bert_result.get("fallback_recommended"):
                rule_result["bert_low_confidence"] = True

            if (
                bert_result.get("confidence", 0.0) >= self.bert_confidence_threshold
                and not rule_result.get("is_negated")
            ):
                mapped_intent = BERT_INTENT_MAPPING.get(bert_result.get("intent", ""))
                if mapped_intent:
                    rule_result["primary_intent"] = mapped_intent
                    rule_result["intent_confidence"] = bert_result.get("confidence", 0.0)
                    if rule_result["intent_hints"] is None:
                        rule_result["intent_hints"] = []
                    if mapped_intent not in rule_result["intent_hints"]:
                        rule_result["intent_hints"].append(mapped_intent)

        if not self.use_rasa or self.rasa_service is None:
            return rule_result

        rasa_result = await self.rasa_service.parse(message)
        rasa_intent = rasa_result.get("intent", {})
        rasa_intent_name = rasa_intent.get("name") if rasa_intent else None
        rasa_confidence = rasa_intent.get("confidence", 0.0) if rasa_intent else 0.0

        rule_result["rasa_intent"] = rasa_intent_name
        rule_result["rasa_confidence"] = rasa_confidence
        rule_result["rasa_available"] = True
        rule_result["sources_used"].append("rasa")

        if rasa_intent_name and rasa_confidence >= self.rasa_confidence_threshold:
            mapped_intent = INTENT_MAPPING.get(rasa_intent_name)
            if mapped_intent and mapped_intent != "negation":
                rule_result["primary_intent"] = mapped_intent
                if rule_result["intent_hints"] is None:
                    rule_result["intent_hints"] = []
                if mapped_intent not in rule_result["intent_hints"]:
                    rule_result["intent_hints"].append(mapped_intent)

        if rule_result.get("is_negated"):
            rule_result["rasa_intent"] = None
            rule_result["rasa_confidence"] = 0.0
            rule_result["tool_key"] = None

        return rule_result

    def recognize_sync(self, message: str) -> Dict[str, Any]:
        """
        同步版本的意图识别（兼容原有接口）

        Args:
            message: 用户消息

        Returns:
            意图识别结果
        """
        import asyncio
        import concurrent.futures
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.recognize(message))
                    return future.result(timeout=30)
            else:
                return asyncio.run(self.recognize(message))
        except concurrent.futures.TimeoutError:
            logger.error("混合意图识别超时")
            return rule_recognize_intents(message)
        except RuntimeError:
            return asyncio.run(self.recognize(message))
        except Exception as e:
            logger.error(f"混合意图识别失败: {e}")
            return rule_recognize_intents(message)


_hybrid_service_instance: Optional[HybridIntentService] = None

def get_hybrid_intent_service(
    use_rasa: bool = False,
    use_bert: bool = True,
    bert_model_path: Optional[str] = None,
    bert_confidence_threshold: float = 0.7,
    **kwargs
) -> HybridIntentService:
    """
    获取混合意图服务单例

    Args:
        use_rasa: 是否启用 RASA
        use_bert: 是否启用 BERT 模型
        bert_model_path: BERT 模型路径
        bert_confidence_threshold: BERT 置信度阈值
        **kwargs: 其他参数

    Returns:
        HybridIntentService 实例
    """
    global _hybrid_service_instance

    if _hybrid_service_instance is None:
        rasa_service = None
        if use_rasa:
            rasa_service = get_rasa_nlu_service(**kwargs)

        _hybrid_service_instance = HybridIntentService(
            use_rasa=use_rasa,
            rasa_service=rasa_service,
            use_bert=use_bert,
            bert_model_path=bert_model_path,
            bert_confidence_threshold=bert_confidence_threshold,
        )

    return _hybrid_service_instance

def reset_hybrid_intent_service():
    """重置混合意图服务单例"""
    global _hybrid_service_instance
    _hybrid_service_instance = None


async def hybrid_recognize_intents(message: str) -> Dict[str, Any]:
    """
    混合意图识别入口函数

    Args:
        message: 用户消息

    Returns:
        意图识别结果
    """
    service = get_hybrid_intent_service()
    return await service.recognize(message)


def hybrid_recognize_intents_sync(message: str) -> Dict[str, Any]:
    """
    混合意图识别同步入口函数

    Args:
        message: 用户消息

    Returns:
        意图识别结果
    """
    service = get_hybrid_intent_service()
    return service.recognize_sync(message)
