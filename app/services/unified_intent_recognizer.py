# -*- coding: utf-8 -*-
"""
统一意图识别服务

整合6套意图识别实现：
1. 规则引擎 (rule_engine.py) - 快速、确定性高
2. DeepSeek API (deepseek_intent_service.py) - 深度语义理解
3. BERT 模型 (bert_intent_service.py) - 预训练模型
4. RASA NLU (rasa_nlu_service.py) - 口语化处理
5. 蒸馏模型 (distilled_intent_service.py) - 轻量级本地模型
6. 混合引擎 (hybrid_intent_service.py) - 多引擎组合

使用策略：
- 优先级：规则 > 蒸馏 > BERT > DeepSeek > RASA
- 规则优先保证速度和可靠性
- DeepSeek/BERT 提供语义理解能力
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from resources.config.intent_config import get_intent_config, reload_intent_config

logger = logging.getLogger(__name__)


class RecognizerType(Enum):
    """识别器类型"""
    RULE = "rule"
    DISTILLED = "distilled"
    BERT = "bert"
    DEEPSEEK = "deepseek"
    RASA = "rasa"
    HYBRID = "hybrid"


@dataclass
class RecognizerResult:
    """统一识别结果"""
    primary_intent: str
    tool_key: str
    intent_hints: List[str]
    is_negated: bool
    is_greeting: bool
    is_goodbye: bool
    is_help: bool
    is_confirmation: bool
    is_negation_intent: bool
    is_likely_unclear: bool
    all_matched_tools: List[tuple]
    slots: Dict[str, Any]
    confidence: float
    sources_used: List[str]
    raw_results: Dict[str, Any]


class UnifiedIntentRecognizer:
    """
    统一意图识别器

    组合多个识别器，按优先级返回最佳结果
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._initialized = True
        self._rule_recognizer = None
        self._distilled_recognizer = None
        self._bert_recognizer = None
        self._deepseek_recognizer = None
        self._rasa_service = None
        self._hybrid_service = None

        self._init_recognizers()

    def _init_recognizers(self):
        """初始化所有识别器"""
        from app.services.rule_engine import get_rule_engine, reload_rule_engine
        self._rule_engine = get_rule_engine()

        try:
            from app.services.distilled_intent_service import get_distilled_recognizer
            self._distilled_recognizer = get_distilled_recognizer()
            if self._distilled_recognizer.is_available():
                logger.info("蒸馏模型识别器已加载")
            else:
                logger.info("蒸馏模型不可用")
                self._distilled_recognizer = None
        except Exception as e:
            logger.warning(f"蒸馏模型加载失败: {e}")
            self._distilled_recognizer = None

        try:
            from app.services.bert_intent_service import BertIntentClassifier
            # unified_intent_recognizer 位于：XCAGI/app/services/
            # 模型目录在：XCAGI/distillation/
            # 因此 base_dir 需要回到 XCAGI 根目录（向上 3 级）。
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            distillation_model_path = os.path.join(base_dir, "distillation", "checkpoints", "best.pt")
            chinese_bert_path = os.path.join(base_dir, "distillation", "checkpoints", "hfl", "chinese-bert-wwm-ext")

            if os.path.exists(distillation_model_path):
                logger.info(f"发现本地蒸馏模型：{distillation_model_path}")
                self._bert_recognizer = BertIntentClassifier(
                    model_path=distillation_model_path,
                    local_files_only=True
                )
            elif os.path.exists(chinese_bert_path):
                logger.info(f"发现 chinese-bert-wwm-ext 模型：{chinese_bert_path}")
                self._bert_recognizer = BertIntentClassifier(
                    model_path=chinese_bert_path,
                    local_files_only=True
                )
            else:
                logger.warning("本地模型不存在，使用虚拟模型（规则引擎将作为主要识别器）")
                self._bert_recognizer = BertIntentClassifier(
                    model_name="chinese-bert-wwm",
                    local_files_only=True
                )
            if self._bert_recognizer.is_available():
                logger.info("BERT识别器已加载")
            else:
                logger.warning("BERT识别器不可用")
                self._bert_recognizer = None
        except Exception as e:
            logger.warning(f"BERT识别器加载失败: {e}")
            self._bert_recognizer = None

        try:
            from app.services.deepseek_intent_service import DeepSeekIntentRecognizer
            self._deepseek_recognizer = DeepSeekIntentRecognizer()
            logger.info("DeepSeek识别器已加载")
        except Exception as e:
            logger.warning(f"DeepSeek识别器加载失败: {e}")
            self._deepseek_recognizer = None

        try:
            from app.services.rasa_nlu_service import RasaNLUService
            self._rasa_service = RasaNLUService()
            logger.info("RASA NLU已加载")
        except Exception as e:
            logger.warning(f"RASA NLU加载失败: {e}")
            self._rasa_service = None

        try:
            from app.services.hybrid_intent_service import HybridIntentService
            self._hybrid_service = HybridIntentService()
            logger.info("混合意图服务已加载")
        except Exception as e:
            logger.warning(f"混合意图服务加载失败: {e}")
            self._hybrid_service = None

    def recognize(
        self,
        message: str,
        context: Optional[List[Dict[str, str]]] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> RecognizerResult:
        """
        统一意图识别入口

        Args:
            message: 用户消息
            context: 对话上下文 (对话历史列表)
            context_data: 扩展上下文数据 (用户偏好、最近意图等)

        Returns:
            RecognizerResult: 统一的识别结果
        """
        results = {}
        sources_used = []
        context_used = False

        try:
            from app.services.intent_service import quick_recognize, recognize_intents

            if context_data:
                quick_result = quick_recognize(message, context_data)
                if quick_result.get("primary_intent") and quick_result.get("elapsed_ms", 100) < 50:
                    sources_used.append("quick")
                    context_used = quick_result.get("context_inherited", False)
                    logger.info(f"[CONTEXT] quick_recognize hit: intent={quick_result.get('primary_intent')}, context_used={context_used}")
                    return RecognizerResult(
                        primary_intent=quick_result.get("primary_intent"),
                        tool_key=quick_result.get("tool_key"),
                        intent_hints=[quick_result.get("primary_intent")] if quick_result.get("primary_intent") else [],
                        is_negated=False,
                        is_greeting=False,
                        is_goodbye=False,
                        is_help=False,
                        is_confirmation=False,
                        is_negation_intent=False,
                        is_likely_unclear=False,
                        all_matched_tools=[],
                        slots=quick_result.get("slots", {}),
                        confidence=0.95 if quick_result.get("source") == "quick_command" else 0.85,
                        sources_used=sources_used,
                        raw_results={"quick_result": quick_result}
                    )
        except Exception as e:
            logger.warning(f"快速识别失败: {e}")

        rule_result = self._recognize_rule(message)
        if rule_result:
            results["rule"] = rule_result
            sources_used.append("rule")

        if context_data:
            context_intent = self._recognize_from_context(message, context_data)
            if context_intent:
                results["context"] = context_intent
                sources_used.append("context")
                context_used = True

        if self._distilled_recognizer and self._distilled_recognizer.is_available():
            distilled_result = self._recognize_distilled(message)
            if distilled_result:
                results["distilled"] = distilled_result
                sources_used.append("distilled")

        if self._bert_recognizer:
            bert_result = self._recognize_bert(message)
            if bert_result:
                results["bert"] = bert_result
                sources_used.append("bert")

        # 普通界面 + 专业意图（混合）：不再跑 unified 内的同步 DeepSeek 意图（避免多一次 RTT + 嵌套事件循环风险），
        # 主对话仍会调用一次 DeepSeek 生成回复。
        skip_unified_deepseek = False
        if context_data and isinstance(context_data, dict):
            if (
                str(context_data.get("tool_execution_profile") or "").strip().lower() == "normal"
                and str(context_data.get("ui_surface") or "").strip().lower() == "normal"
            ):
                skip_unified_deepseek = True
                logger.info("[INTENT] 混合界面画像：跳过 unified 内 DeepSeek 意图")

        if self._deepseek_recognizer and not skip_unified_deepseek:
            deepseek_result = self._recognize_deepseek(message, context)
            if deepseek_result:
                results["deepseek"] = deepseek_result
                sources_used.append("deepseek")

        final_result = self._merge_results(results, message, context_data)

        return RecognizerResult(
            primary_intent=final_result.get("primary_intent"),
            tool_key=final_result.get("tool_key"),
            intent_hints=final_result.get("intent_hints", []),
            is_negated=final_result.get("is_negated", False),
            is_greeting=final_result.get("is_greeting", False),
            is_goodbye=final_result.get("is_goodbye", False),
            is_help=final_result.get("is_help", False),
            is_confirmation=final_result.get("is_confirmation", False),
            is_negation_intent=final_result.get("is_negation_intent", False),
            is_likely_unclear=final_result.get("is_likely_unclear", False),
            all_matched_tools=final_result.get("all_matched_tools", []),
            slots=final_result.get("slots", {}),
            confidence=final_result.get("confidence", 0.0),
            sources_used=sources_used,
            raw_results=results
        )

    def _recognize_from_context(
        self,
        message: str,
        context_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """基于上下文的意图识别"""
        try:
            pending = context_data.get("pending_confirmation")
            if pending:
                pending_intent = pending.get("intent") or pending.get("tool_key")
                if pending_intent:
                    return {
                        "primary_intent": pending_intent,
                        "tool_key": pending_intent,
                        "confidence": 0.9,
                        "slots": pending.get("slots", {}),
                        "source": "context_pending"
                    }

            last_intent = context_data.get("last_intent") or context_data.get("current_intent")
            last_slots = context_data.get("last_slots", {})

            if last_intent and last_slots:
                return {
                    "primary_intent": last_intent,
                    "tool_key": last_intent,
                    "confidence": 0.7,
                    "slots": last_slots,
                    "source": "context_inherit"
                }

            recent_intents = context_data.get("recent_intents", [])
            if recent_intents:
                return {
                    "primary_intent": recent_intents[0],
                    "tool_key": recent_intents[0],
                    "confidence": 0.6,
                    "slots": {},
                    "source": "context_recent"
                }

        except Exception as e:
            logger.warning(f"上下文识别失败: {e}")

        return None

    def _recognize_rule(self, message: str) -> Optional[Dict[str, Any]]:
        """规则识别"""
        try:
            from app.services.intent_service import recognize_intents
            return recognize_intents(message)
        except Exception as e:
            logger.error(f"规则识别失败: {e}")
            return None

    def _recognize_distilled(self, message: str) -> Optional[Dict[str, Any]]:
        """蒸馏模型识别"""
        try:
            if not self._distilled_recognizer:
                return None
            result = self._distilled_recognizer.recognize(message)
            if result and result.get("intent"):
                return {
                    "primary_intent": result["intent"],
                    "tool_key": result["intent"],
                    "confidence": result.get("confidence", 0.0),
                    "slots": {}
                }
            return None
        except Exception as e:
            logger.error(f"蒸馏模型识别失败: {e}")
            return None

    def _recognize_bert(self, message: str) -> Optional[Dict[str, Any]]:
        """BERT模型识别"""
        try:
            if not self._bert_recognizer:
                return None
            result = self._bert_recognizer.predict(message)
            if result and result.get("intent"):
                return {
                    "primary_intent": result["intent"],
                    "tool_key": result["intent"],
                    "confidence": result.get("confidence", 0.0),
                    "slots": {}
                }
            return None
        except Exception as e:
            logger.error(f"BERT识别失败: {e}")
            return None

    def _recognize_deepseek(self, message: str, context: Optional[List[Dict[str, str]]] = None) -> Optional[Dict[str, Any]]:
        """DeepSeek模型识别"""
        try:
            import asyncio
            if not self._deepseek_recognizer:
                return None
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._deepseek_recognizer.recognize(message, context))
            finally:
                loop.close()
            if result and result.get("intent"):
                return {
                    "primary_intent": result["intent"],
                    "tool_key": result["intent"],
                    "confidence": result.get("confidence", 0.0),
                    "slots": result.get("slots", {})
                }
            return None
        except Exception as e:
            logger.error(f"DeepSeek识别失败: {e}")
            return None

    def _merge_results(
        self,
        results: Dict[str, Dict],
        message: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """合并多个识别结果，规则优先，考虑上下文匹配度"""
        if not results:
            return {
                "primary_intent": None,
                "tool_key": None,
                "confidence": 0.0,
                "slots": {},
                "is_likely_unclear": len(message) <= 4
            }

        if "rule" in results:
            rule_result = results["rule"]
            if rule_result.get("tool_key") and not rule_result.get("is_negated"):
                return rule_result

        if "context" in results and context_data:
            context_result = results["context"]
            context_confidence = context_result.get("confidence", 0.0)

            pending = context_data.get("pending_confirmation")
            if pending and context_confidence >= 0.85:
                return context_result

            user_prefs = context_data.get("user_preferences", {})
            if user_prefs and context_confidence >= 0.75:
                slots = context_result.get("slots", {})
                if not slots.get("unit_name") and user_prefs.get("favorite_customer"):
                    slots["unit_name"] = user_prefs["favorite_customer"]
                    context_result["slots"] = slots
                return context_result

        for source in ["distilled", "bert", "deepseek", "hybrid"]:
            if source in results:
                result = results[source]
                if result.get("primary_intent") and result.get("confidence", 0) > 0.6:
                    return result

        if "context" in results:
            return results["context"]

        return results.get("rule", {})

    def reload(self):
        """重新加载所有识别器"""
        reload_intent_config()
        from app.services.rule_engine import reload_rule_engine
        reload_rule_engine()
        self._init_recognizers()


_unified_recognizer: Optional[UnifiedIntentRecognizer] = None


def get_unified_intent_recognizer() -> UnifiedIntentRecognizer:
    """获取统一识别器单例"""
    global _unified_recognizer
    if _unified_recognizer is None:
        _unified_recognizer = UnifiedIntentRecognizer()
    return _unified_recognizer


def reload_unified_recognizer() -> UnifiedIntentRecognizer:
    """重新加载统一识别器"""
    global _unified_recognizer
    if _unified_recognizer:
        _unified_recognizer.reload()
    return get_unified_intent_recognizer()
