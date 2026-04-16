"""
意图引擎 - 分层处理 (<100ms)
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Any

from ..processors.reflex_processor import ReflexProcessor, ReflexResult
from ..processors.cache_processor import CacheProcessor, CacheResult
from ..processors.rule_processor import RuleProcessor, RuleResult
from ..processors.llm_processor import LLMProcessor, LLMResult
from ..registry.intent_registry import INTENT_REGISTRY, get_intent
from ..utils.metrics import get_metrics
from backend.sales_contract_intent_bridge import sales_contract_utterance_requires_structured_llm

logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    intent: str
    confidence: float
    entities: dict[str, Any] = field(default_factory=dict)
    response: str = ""
    processing_mode: str = "unknown"
    processing_time_ms: float = 0.0
    fallback_available: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class IntentEngine:
    def __init__(self):
        self._reflex = ReflexProcessor()
        self._cache = CacheProcessor()
        self._rule = RuleProcessor()
        self._llm = LLMProcessor()

    async def process(self, user_input: str, context: dict[str, Any] | None = None) -> IntentResult:
        start = time.perf_counter()
        total_start = start

        context = context or {}
        preferred_mode = context.get("preferred_mode", "auto")

        if preferred_mode == "fast":
            return await self._fast_path(user_input, total_start)

        if preferred_mode == "accurate":
            return await self._accurate_path(user_input, total_start)

        return await self._auto_path(user_input, total_start)

    async def _fast_path(self, user_input: str, start: float) -> IntentResult:
        reflex_result = self._reflex.process(user_input)
        if reflex_result.matched:
            get_metrics().inc("intent_engine.reflex.hit")
            return IntentResult(
                intent=reflex_result.intent,
                confidence=0.98,
                response=reflex_result.response,
                processing_mode="reflex",
                processing_time_ms=(time.perf_counter() - start) * 1000,
                fallback_available=False
            )

        cache_result = self._cache.get(user_input)
        if cache_result.hit:
            get_metrics().inc("intent_engine.cache.hit")
            return IntentResult(
                intent=cache_result.data.get("intent", "unknown"),
                confidence=cache_result.data.get("confidence", 0.5),
                entities=cache_result.data.get("entities", {}),
                processing_mode="cache",
                processing_time_ms=(time.perf_counter() - start) * 1000,
                fallback_available=True
            )

        rule_result = self._rule.process(user_input)
        if rule_result.matched:
            get_metrics().inc("intent_engine.rule.hit")
            self._cache.set(user_input, {
                "intent": rule_result.intent,
                "confidence": rule_result.confidence,
                "entities": rule_result.entities
            })
            return IntentResult(
                intent=rule_result.intent,
                confidence=rule_result.confidence,
                entities=rule_result.entities,
                processing_mode="rule",
                processing_time_ms=(time.perf_counter() - start) * 1000
            )

        return IntentResult(
            intent="unknown",
            confidence=0.0,
            processing_mode="fast_fallback",
            processing_time_ms=(time.perf_counter() - start) * 1000
        )

    async def _accurate_path(self, user_input: str, start: float) -> IntentResult:
        llm_result = await self._llm.process(user_input)
        if llm_result.success:
            get_metrics().inc("intent_engine.llm.success")
            self._cache.set(user_input, {
                "intent": llm_result.intent,
                "confidence": llm_result.confidence,
                "entities": llm_result.entities
            })
            return IntentResult(
                intent=llm_result.intent,
                confidence=llm_result.confidence,
                entities=llm_result.entities,
                response=llm_result.response,
                processing_mode="llm",
                processing_time_ms=(time.perf_counter() - start) * 1000
            )

        rule_result = self._rule.process(user_input)
        if rule_result.matched:
            return IntentResult(
                intent=rule_result.intent,
                confidence=rule_result.confidence,
                entities=rule_result.entities,
                processing_mode="rule_fallback",
                processing_time_ms=(time.perf_counter() - start) * 1000
            )

        return IntentResult(
            intent="general_chat",
            confidence=0.3,
            processing_mode="llm_fallback",
            processing_time_ms=(time.perf_counter() - start) * 1000
        )

    async def _auto_path(self, user_input: str, start: float) -> IntentResult:
        reflex_result = self._reflex.process(user_input)
        if reflex_result.matched:
            get_metrics().inc("intent_engine.reflex.hit")
            return IntentResult(
                intent=reflex_result.intent,
                confidence=0.98,
                response=reflex_result.response,
                processing_mode="reflex",
                processing_time_ms=(time.perf_counter() - start) * 1000,
                fallback_available=False
            )

        cache_result = self._cache.get(user_input)
        if cache_result.hit:
            get_metrics().inc("intent_engine.cache.hit")
            return IntentResult(
                intent=cache_result.data.get("intent", "unknown"),
                confidence=cache_result.data.get("confidence", 0.5),
                entities=cache_result.data.get("entities", {}),
                processing_mode="cache",
                processing_time_ms=(time.perf_counter() - start) * 1000,
                fallback_available=True
            )

        rule_result = self._rule.process(user_input)
        if rule_result.matched:
            if (
                rule_result.intent == "sales_contract"
                and sales_contract_utterance_requires_structured_llm(user_input)
            ):
                logger.info(
                    "[IntentEngine] sales_contract 口语长单，规则仅作提示，降级到 LLM/bridge 抽取"
                )
                llm_result = await self._llm.process(user_input)
                if llm_result.success:
                    get_metrics().inc("intent_engine.llm.success")
                    self._cache.set(user_input, {
                        "intent": llm_result.intent,
                        "confidence": llm_result.confidence,
                        "entities": llm_result.entities
                    })
                    return IntentResult(
                        intent=llm_result.intent,
                        confidence=llm_result.confidence,
                        entities=llm_result.entities,
                        response=llm_result.response,
                        processing_mode="llm",
                        processing_time_ms=(time.perf_counter() - start) * 1000
                    )

            get_metrics().inc("intent_engine.rule.hit")
            self._cache.set(user_input, {
                "intent": rule_result.intent,
                "confidence": rule_result.confidence,
                "entities": rule_result.entities
            })
            return IntentResult(
                intent=rule_result.intent,
                confidence=rule_result.confidence,
                entities=rule_result.entities,
                processing_mode="rule",
                processing_time_ms=(time.perf_counter() - start) * 1000
            )

        llm_result = await self._llm.process(user_input)
        if llm_result.success:
            get_metrics().inc("intent_engine.llm.success")
            self._cache.set(user_input, {
                "intent": llm_result.intent,
                "confidence": llm_result.confidence,
                "entities": llm_result.entities
            })
            return IntentResult(
                intent=llm_result.intent,
                confidence=llm_result.confidence,
                entities=llm_result.entities,
                response=llm_result.response,
                processing_mode="llm",
                processing_time_ms=(time.perf_counter() - start) * 1000
            )

        return IntentResult(
            intent="general_chat",
            confidence=0.1,
            processing_mode="fallback",
            processing_time_ms=(time.perf_counter() - start) * 1000
        )

    def get_reflex_processor(self) -> ReflexProcessor:
        return self._reflex

    def get_cache_processor(self) -> CacheProcessor:
        return self._cache

    def get_rule_processor(self) -> RuleProcessor:
        return self._rule

    def get_llm_processor(self) -> LLMProcessor:
        return self._llm


_intent_engine: IntentEngine | None = None


def get_intent_engine() -> IntentEngine:
    global _intent_engine
    if _intent_engine is None:
        _intent_engine = IntentEngine()
    return _intent_engine
