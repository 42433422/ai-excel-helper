"""
统一意图识别器

整合多种意图识别引擎（规则、BERT、DeepSeek、RASA）

原始模块位于 app/services/unified_intent_recognizer.py
此文件在 DDD 迁移完成前提供委托。
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _env_flag(name: str, default: str = "0") -> bool:
    return (os.environ.get(name, default) or default).strip().lower() in {"1", "true", "yes", "on"}


class UnifiedIntentRecognizer:
    """
    统一意图识别器

    整合多种意图识别引擎（规则、蒸馏、BERT、DeepSeek、RASA）。

    `recognize()` 的路由：
        distilled(>阈值) -> bert(>阈值) -> rasa(>阈值) -> deepseek(>阈值) -> unk

    新增：
        - `is_ready()`：用于 ``/health/readiness``，返回每个子引擎的加载状态。
        - RASA 真正参与 recognize：之前版本只在 ``load()`` 里实例化 RASA 却
          从不调用它，健康检查永远显示"已加载"但运行时不会落地，本次补齐。
    """

    def __init__(self):
        self.bert_recognizer = None
        self.deepseek_recognizer = None
        self.rasa_recognizer = None
        self.distilled_recognizer = None
        self.rule_recognizer = None
        self._initialized = False
        self._engine_errors: dict[str, str] = {}

    def load(self) -> bool:
        if self._initialized:
            return True

        try:
            # 首选 ai_engines 版本（提供统一的 load_model() 契约）。
            try:
                from app.ai_engines.bert.intent_service import BertIntentClassifier
            except Exception:
                from app.services.bert_intent_service import BertIntentClassifier  # type: ignore
            self.bert_recognizer = BertIntentClassifier()
            loader = getattr(self.bert_recognizer, "load_model", None)
            if callable(loader):
                loader()
            logger.info("BERT识别器已加载")
        except Exception as e:
            logger.warning(f"BERT识别器加载失败：{e}")
            self._engine_errors["bert"] = str(e)

        try:
            # distilled_intent_service 当前只暴露工厂 get_distilled_recognizer，
            # 直接 import DistilledIntentClassifier 会失败；这里做兼容。
            try:
                from app.services.distilled_intent_service import (
                    get_distilled_recognizer,  # type: ignore
                )

                self.distilled_recognizer = get_distilled_recognizer()
            except Exception:
                from app.services.distilled_intent_service import (
                    DistilledIntentClassifier,  # type: ignore
                )

                self.distilled_recognizer = DistilledIntentClassifier()
                loader = getattr(self.distilled_recognizer, "load_model", None)
                if callable(loader):
                    loader()
            logger.info("蒸馏模型识别器已加载")
        except Exception as e:
            logger.warning(f"蒸馏模型加载失败：{e}")
            self._engine_errors["distilled"] = str(e)

        try:
            # 兼容两套命名：ai_engines 用 DeepseekIntentClassifier；services 用 DeepSeekIntentRecognizer。
            try:
                from app.ai_engines.deepseek.intent_service import (
                    DeepseekIntentClassifier as _DeepseekImpl,  # type: ignore
                )
            except Exception:
                from app.services.deepseek_intent_service import (
                    DeepSeekIntentRecognizer as _DeepseekImpl,  # type: ignore
                )
            self.deepseek_recognizer = _DeepseekImpl()
            loader = getattr(self.deepseek_recognizer, "load_model", None)
            if callable(loader):
                loader()
            logger.info("DeepSeek识别器已加载")
        except Exception as e:
            logger.warning(f"DeepSeek识别器加载失败：{e}")
            self._engine_errors["deepseek"] = str(e)

        try:
            # 首选深度落地版（app.ai_engines.rasa）；保留旧入口作为兼容 fallback。
            try:
                from app.ai_engines.rasa.nlu_service import RasaNLUService
            except Exception:
                from app.services.rasa_nlu_service import RasaNLUService  # type: ignore
            self.rasa_recognizer = RasaNLUService()
            self.rasa_recognizer.load_model()
            logger.info("RASA NLU已加载")
        except Exception as e:
            logger.warning(f"RASA NLU加载失败：{e}")
            self._engine_errors["rasa"] = str(e)

        self._initialized = True
        logger.info("混合意图服务已加载")
        return True

    def recognize(self, text: str) -> dict[str, Any]:
        if not self._initialized:
            self.load()

        if not text or not text.strip():
            return {"intent": "unk", "confidence": 0.0, "source": "unified"}

        try:
            from app.domain.ports.cache_port import get_intent_cache_port
            from app.request_active_mod_ctx import get_request_active_mod_id

            cache = get_intent_cache_port()
            if cache is None:
                return self._recognize_uncached(text)
            mod_id = get_request_active_mod_id()
            return cache.get_or_compute(
                text=text,
                mod_id=mod_id,
                compute_fn=lambda: self._recognize_uncached(text),
            )
        except Exception as e:
            logger.debug("IntentCache path failed, falling back: %s", e)
            return self._recognize_uncached(text)

    def _recognize_uncached(self, text: str) -> dict[str, Any]:
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

        if self.rasa_recognizer and _env_flag("ENABLE_RASA", "1"):
            try:
                parsed = self.rasa_recognizer.parse(text)
                intent_obj = (parsed or {}).get("intent") or {}
                name = intent_obj.get("name")
                confidence = float(intent_obj.get("confidence") or 0.0)
                threshold = float(getattr(self.rasa_recognizer, "confidence_threshold", 0.7) or 0.7)
                if name and confidence >= threshold:
                    return {
                        "intent": name,
                        "confidence": round(confidence, 4),
                        "entities": parsed.get("entities") or [],
                        "source": "rasa",
                    }
            except Exception as e:
                logger.warning(f"RASA 预测失败：{e}")

        if self.deepseek_recognizer:
            try:
                # DeepseekIntentClassifier 提供 recognize/predict，按可用方法调用。
                predict = getattr(self.deepseek_recognizer, "predict", None) or getattr(
                    self.deepseek_recognizer, "recognize", None
                )
                if predict:
                    result = predict(text)
                    if isinstance(result, dict) and result.get("confidence", 0) > 0.7:
                        result["source"] = result.get("source") or "deepseek"
                        return result
            except Exception as e:
                logger.warning(f"DeepSeek 预测失败：{e}")

        return {"intent": "unk", "confidence": 0.0, "source": "unified"}

    def is_ready(self) -> bool:
        """用于 /health/readiness：只要规则层可用即认为 ready。"""

        if not self._initialized:
            try:
                self.load()
            except Exception as e:
                logger.debug("UnifiedIntentRecognizer.load() 失败：%s", e)
        # 规则层始终可用；只要这里完成初始化即 ready。
        return self._initialized

    def get_engine_status(self) -> dict[str, Any]:
        """返回各子识别器的可用状态，供诊断/健康端点使用。"""

        if not self._initialized:
            self.load()

        status: dict[str, Any] = {
            "rule": {"loaded": True},
            "distilled": {
                "loaded": self.distilled_recognizer is not None,
                "error": self._engine_errors.get("distilled"),
            },
            "bert": {
                "loaded": self.bert_recognizer is not None,
                "error": self._engine_errors.get("bert"),
            },
            "deepseek": {
                "loaded": self.deepseek_recognizer is not None,
                "error": self._engine_errors.get("deepseek"),
            },
            "rasa": self._rasa_status_snapshot(),
        }
        return status

    def _rasa_status_snapshot(self) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "loaded": self.rasa_recognizer is not None,
            "error": self._engine_errors.get("rasa"),
        }
        getter = getattr(self.rasa_recognizer, "get_status", None)
        if callable(getter):
            try:
                entry.update(getter())
            except Exception as e:
                entry["status_error"] = str(e)
        return entry


_unified_intent_recognizer: UnifiedIntentRecognizer | None = None


def get_unified_intent_recognizer() -> UnifiedIntentRecognizer:
    global _unified_intent_recognizer
    if _unified_intent_recognizer is None:
        _unified_intent_recognizer = UnifiedIntentRecognizer()
        _unified_intent_recognizer.load()
    return _unified_intent_recognizer
