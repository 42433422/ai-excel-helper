"""
意图识别领域服务 (Unified)

这是 DDD 领域层核心服务，提供统一的意图识别接口。
整合规则引擎、AI 模型 (BERT/DeepSeek/RASA) 和策略模式。

职责:
- 协调多种识别策略
- 提供标准化 RecognizerResult
- 保持纯领域逻辑 (无基础设施依赖)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple

from .intent.coordinator import IntentRecognitionCoordinator, get_intent_coordinator
from resources.config.intent_config import get_intent_config


class IntentType(Enum):
    """意图类型枚举 (与 config 映射)"""
    SHIPMENT = "shipment_generate"
    PRODUCT = "products"
    CUSTOMER = "customers"
    SEARCH = "search"
    IMPORT = "upload_file"
    EXPORT = "customer_export"
    PRINT = "print_label"
    WECHAT = "wechat_send"
    UNKNOWN = "unknown"
    GREETING = "greet"
    GOODBYE = "goodbye"
    HELP = "help"


@dataclass
class RecognizerResult:
    """统一意图识别结果 (与 unified_intent_recognizer.py 兼容)"""
    primary_intent: str
    tool_key: str
    intent_hints: List[str]
    is_negated: bool = False
    is_greeting: bool = False
    is_goodbye: bool = False
    is_help: bool = False
    is_confirmation: bool = False
    is_negation_intent: bool = False
    is_likely_unclear: bool = False
    all_matched_tools: List[tuple] = None  # type: ignore
    slots: Dict[str, Any] = None  # type: ignore
    confidence: float = 0.0
    sources_used: List[str] = None  # type: ignore
    raw_results: Dict[str, Any] = None  # type: ignore

    def __post_init__(self):
        if self.all_matched_tools is None:
            self.all_matched_tools = []
        if self.slots is None:
            self.slots = {}
        if self.sources_used is None:
            self.sources_used = []
        if self.raw_results is None:
            self.raw_results = {}


class IntentRecognizer(Protocol):
    """意图识别器协议 (for dependency injection)"""
    def recognize(self, message: str, context: Optional[Dict[str, Any]] = None) -> RecognizerResult: ...


class IntentRecognitionService:
    """
    统一的意图识别领域服务

    整合:
    - IntentRecognitionCoordinator (策略模式: greeting/negation 等)
    - RuleEngine (关键词/正则)
    - AI 模型 (via infrastructure adapters)
    """

    def __init__(self, coordinator: Optional[IntentRecognitionCoordinator] = None):
        self.coordinator = coordinator or get_intent_coordinator()
        self._config = get_intent_config()
        self._rule_engine = None  # lazy loaded from services if needed (to avoid circular imports)

    def recognize(self, message: str, context: Optional[Dict[str, Any]] = None) -> RecognizerResult:
        """
        统一意图识别入口 - 核心方法

        流程:
        1. 基础检测 (greeting, negation, etc.) via coordinator
        2. 规则引擎匹配 (优先)
        3. 返回标准化 RecognizerResult

        This replaces logic from intent_service.py, rule_engine.py, hybrid_*, unified_*
        """
        if not message or not isinstance(message, str):
            return RecognizerResult(
                primary_intent="unknown",
                tool_key="unknown",
                intent_hints=[],
                is_likely_unclear=True,
                confidence=0.0,
            )

        msg = message.strip()
        coord = self.coordinator.detect_basic_intents(msg)

        # Use rule engine for tool intents (delegates to existing rule logic)
        rule_result = self._get_rule_result(msg)

        result = RecognizerResult(
            primary_intent=rule_result.get("primary_intent", "unknown"),
            tool_key=rule_result.get("tool_key", "unknown"),
            intent_hints=rule_result.get("intent_hints", []),
            # is_negated：仅当规则引擎链路判定“需要阻断工具”时为 True
            is_negated=bool(rule_result.get("is_negated", False)),
            is_greeting=coord.get("is_greeting", False),
            is_goodbye=coord.get("is_goodbye", False),
            is_help=coord.get("is_help", False),
            is_confirmation=coord.get("is_confirmation", False),
            is_negation_intent=coord.get("is_negation_intent", False),
            is_likely_unclear=len(msg) <= 4 or rule_result.get("is_likely_unclear", False),
            confidence=rule_result.get("confidence", 0.5),
            sources_used=["coordinator", "rule"],
            raw_results={"coordinator": coord, "rule": rule_result},
        )

        return result

    def _get_rule_result(self, message: str) -> Dict[str, Any]:
        """委托给现有规则引擎 (避免重复代码)"""
        try:
            # Import inside method to avoid circular imports with services
            from app.services.intent_service import recognize_intents
            return recognize_intents(message)
        except Exception as e:
            # Fallback to basic keyword match from config
            config = self._config
            tool_intents = config.get("tool_intents", [])
            msg_lower = message.lower()

            for intent in tool_intents:
                keywords = intent.get("keywords", [])
                if any(kw.lower() in msg_lower for kw in keywords):
                    return {
                        "primary_intent": intent["id"],
                        "tool_key": intent.get("tool_key", intent["id"]),
                        "intent_hints": [intent["id"]],
                        "confidence": 0.7,
                    }
            return {
                "primary_intent": "unknown",
                "tool_key": None,
                "intent_hints": [],
                "confidence": 0.3,
            }

    def recognize_batch(self, messages: List[str]) -> List[RecognizerResult]:
        """批量识别 (typed version)"""
        return [self.recognize(msg) for msg in messages]

    def get_intent_hints(self, message: str) -> List[str]:
        """获取意图提示 (for UI)"""
        result = self.recognize(message)
        return result.intent_hints


def get_intent_recognition_service() -> IntentRecognitionService:
    """获取领域意图识别服务 (Composition Root 友好)"""
    return IntentRecognitionService()
