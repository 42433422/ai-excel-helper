# -*- coding: utf-8 -*-
"""
规则引擎 v2

基于配置文件的意图规则匹配引擎，支持：
- 关键词匹配
- 正则表达式模式匹配
- 优先级排序
- 热更新配置
"""

import hashlib
import logging
import re
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from app.utils.cache_manager import get_intent_rule_cache
from resources.config.intent_config import get_intent_config, reload_intent_config

logger = logging.getLogger(__name__)

_match_cache = get_intent_rule_cache()


def _make_cache_key(message: str, intent_id: str) -> str:
    return hashlib.md5(f"{intent_id}:{message.strip().lower()}".encode()).hexdigest()


class RuleEngine:
    """规则引擎"""

    def __init__(self):
        self._config = get_intent_config()

    def reload(self):
        """重新加载配置"""
        self._config = reload_intent_config()
        _match_cache.clear()

    def _normalize(self, msg: str) -> str:
        """标准化消息"""
        return (msg or "").strip()

    def _match_keywords(self, message: str, keywords: List[str]) -> bool:
        """匹配关键词"""
        msg_lower = message.lower()
        for kw in keywords:
            if kw in message or kw.lower() in msg_lower:
                return True
        return False

    def _match_patterns(self, message: str, patterns: List[str]) -> Optional[Dict[str, Any]]:
        """匹配正则表达式模式"""
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                return match.groupdict() if match.groupdict() else {"match": match.group(0)}
        return None

    def match_tool_intent(self, message: str, intent_def: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        匹配工具意图

        Returns:
            (是否匹配, 捕获的组字典)
        """
        keywords = intent_def.get("keywords", [])
        patterns = intent_def.get("patterns", [])

        if self._match_keywords(message, keywords):
            if patterns:
                captured = self._match_patterns(message, patterns)
                return True, captured
            return True, None

        return False, None

    def match_intents(self, message: str) -> List[Dict[str, Any]]:
        """
        匹配所有意图

        Returns:
            匹配的意图列表，按优先级降序
        """
        msg = self._normalize(message)
        if not msg:
            return []

        matches = []
        tool_intents = self._config.get("tool_intents", [])

        for intent_def in tool_intents:
            matched, captured = self.match_tool_intent(msg, intent_def)
            if matched:
                matches.append({
                    "id": intent_def["id"],
                    "tool_key": intent_def.get("tool_key", intent_def["id"]),
                    "priority": intent_def.get("priority", 0),
                    "block_if_negated": intent_def.get("block_if_negated", False),
                    "keywords": intent_def.get("keywords", []),
                    "captured": captured,
                })

        matches.sort(key=lambda x: x["priority"], reverse=True)
        return matches

    def match_hint_intents(self, message: str) -> List[str]:
        """匹配提示意图"""
        msg = self._normalize(message)
        if not msg:
            return []

        hints = []
        hint_intents = self._config.get("hint_intents", [])

        for hint_def in hint_intents:
            keywords = hint_def.get("keywords", [])
            if self._match_keywords(msg, keywords):
                hints.append(hint_def["id"])

        return hints

    def check_special_intent(self, message: str) -> Dict[str, bool]:
        """检查特殊意图（问候、告别、帮助、否定等）"""
        msg = self._normalize(message)
        if not msg:
            return {}

        msg_lower = msg.lower()

        negation_config = self._config.get("negation", {})
        negation_prefixes = negation_config.get("prefixes", [])
        negation_phrases = negation_config.get("phrases", [])

        is_negation = False
        for phrase in negation_phrases:
            if phrase in msg or phrase in msg_lower:
                is_negation = True
                break

        if not is_negation:
            for prefix in negation_prefixes:
                if msg_lower.startswith(prefix) or msg.startswith(prefix):
                    is_negation = True
                    break
                if (" " + prefix in msg_lower) or ("，" + prefix in msg_lower):
                    is_negation = True
                    break

        greeting_config = self._config.get("greeting", {})
        greeting_patterns = greeting_config.get("patterns", [])
        is_greeting = any(p in msg_lower or p in msg for p in greeting_patterns)

        goodbye_config = self._config.get("goodbye", {})
        goodbye_patterns = goodbye_config.get("patterns", [])
        is_goodbye = any(p in msg_lower or p in msg for p in goodbye_patterns)

        help_config = self._config.get("help", {})
        help_patterns = help_config.get("patterns", [])
        is_help = any(p in msg_lower or p in msg for p in help_patterns)

        confirmation_keywords = self._config.get("confirmation_keywords", [])
        is_confirmation = any(kw == msg or msg.startswith(kw) for kw in confirmation_keywords)

        negation_keywords = self._config.get("negation_keywords", [])
        is_negation_intent = any(kw == msg or msg.startswith(kw) for kw in negation_keywords)

        return {
            "is_negation": is_negation,
            "is_greeting": is_greeting,
            "is_goodbye": is_goodbye,
            "is_help": is_help,
            "is_confirmation": is_confirmation,
            "is_negation_intent": is_negation_intent,
        }


_rule_engine: Optional[RuleEngine] = None


def get_rule_engine() -> RuleEngine:
    """获取规则引擎单例"""
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = RuleEngine()
    return _rule_engine


def reload_rule_engine() -> RuleEngine:
    """重新加载规则引擎"""
    global _rule_engine
    _rule_engine = RuleEngine()
    return _rule_engine
