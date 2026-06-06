"""
反射模式库

预定义的反射模式匹配规则
"""

import logging
import re
from dataclasses import dataclass

from app.domain.neuro.reflex_arc import ReflexType

logger = logging.getLogger(__name__)


@dataclass
class PatternRule:
    """模式规则定义"""

    pattern: str
    weight: float = 1.0
    context_required: list[str] = None


class ReflexPatternMatcher:
    """
    反射模式匹配器

    扩展的模式匹配库，支持上下文感知匹配
    """

    # 问候模式
    GREETING_PATTERNS = [
        PatternRule(r"^你好[！!。]?$", weight=1.0),
        PatternRule(r"^您好[！!。]?$", weight=1.0),
        PatternRule(r"^嗨[！!。]?$", weight=0.9),
        PatternRule(r"^\s*hi\b", weight=0.8),
        PatternRule(r"^\s*hello\b", weight=0.8),
        PatternRule(r"^早上好", weight=0.9),
        PatternRule(r"^下午好", weight=0.9),
        PatternRule(r"^晚上好", weight=0.9),
        PatternRule(r"^在吗[？?]?$", weight=0.7),
        PatternRule(r"^有人吗[？?]?$", weight=0.7),
        PatternRule(r"^在不在[？?]?$", weight=0.7),
        PatternRule(r"^哈喽", weight=0.8),
        PatternRule(r"^嘿[！!。]?$", weight=0.7),
    ]

    # 紧急停止模式
    EMERGENCY_STOP_PATTERNS = [
        PatternRule(r"停止", weight=0.9),
        PatternRule(r"^停[！!.。]?$", weight=1.0),
        PatternRule(r"^别[！!.。]?$", weight=0.9),
        PatternRule(r"^取消[！!.。]?$", weight=0.9),
        PatternRule(r"^终止[！!.。]?$", weight=1.0),
        PatternRule(r"^退出[！!.。]?$", weight=0.9),
        PatternRule(r"^结束[！!.。]?$", weight=0.9),
        PatternRule(r"^不[要做了][！!.。]?$", weight=0.8),
        PatternRule(r"^stop\b", weight=1.0),
        PatternRule(r"^end\b", weight=0.9),
        PatternRule(r"^quit\b", weight=0.9),
        PatternRule(r"^cancel\b", weight=0.9),
        PatternRule(r"^abort\b", weight=1.0),
        PatternRule(r"^halt\b", weight=1.0),
    ]

    # 确认模式
    CONFIRMATION_PATTERNS = [
        PatternRule(r"^是的[！!.。]?$", weight=1.0),
        PatternRule(r"^对的[！!.。]?$", weight=1.0),
        PatternRule(r"^没错[！!.。]?$", weight=1.0),
        PatternRule(r"^确认[！!.。]?$", weight=1.0),
        PatternRule(r"^同意[！!.。]?$", weight=0.9),
        PatternRule(r"^好的[！!.。]?$", weight=0.9),
        PatternRule(r"^好[！!.。]?$", weight=0.8),
        PatternRule(r"^行[！!.。]?$", weight=0.8),
        PatternRule(r"^可以[！!.。]?$", weight=0.8),
        PatternRule(r"^没问题[！!.。]?$", weight=0.9),
        PatternRule(r"^要[的][！!.。]?$", weight=0.8),
        PatternRule(r"^yes\b", weight=1.0),
        PatternRule(r"^ok\b", weight=0.9),
        PatternRule(r"^okay\b", weight=0.9),
        PatternRule(r"^y\b", weight=0.8),
        PatternRule(r"^sure\b", weight=0.8),
        PatternRule(r"^当然[！!.。]?$", weight=0.9),
    ]

    # 否定模式
    DENIAL_PATTERNS = [
        PatternRule(r"^不是[！!.。]?$", weight=1.0),
        PatternRule(r"^不对[！!.。]?$", weight=1.0),
        PatternRule(r"^错误[！!.。]?$", weight=0.9),
        PatternRule(r"^否[！!.。]?$", weight=1.0),
        PatternRule(r"^不要[！!.。]?$", weight=0.9),
        PatternRule(r"^拒绝[！!.。]?$", weight=0.9),
        PatternRule(r"^算了[！!.。]?$", weight=0.8),
        PatternRule(r"^no\b", weight=1.0),
        PatternRule(r"^n\b", weight=0.9),
        PatternRule(r"^never\b", weight=0.9),
        PatternRule(r"^negative\b", weight=0.9),
    ]

    # 帮助模式
    HELP_PATTERNS = [
        PatternRule(r"^帮助[！!.。]?$", weight=1.0),
        PatternRule(r"^help\b", weight=1.0),
        PatternRule(r"^怎么用", weight=0.8),
        PatternRule(r"^不会用", weight=0.8),
        PatternRule(r"^教教我", weight=0.8),
        PatternRule(r"^什么功能", weight=0.8),
        PatternRule(r"^能做什么", weight=0.8),
        PatternRule(r"^支持什么", weight=0.8),
        PatternRule(r"^有什么功能", weight=0.8),
        PatternRule(r"^需要帮助", weight=0.9),
        PatternRule(r"^如何使用", weight=0.8),
        PatternRule(r"^说明[书]?", weight=0.7),
        PatternRule(r"^指导", weight=0.8),
        PatternRule(r"^\?+$", weight=0.6),  # 纯问号
    ]

    def __init__(self):
        self._pattern_groups: dict[ReflexType, list[tuple[re.Pattern, float]]] = {}
        self._compile_patterns()
        logger.info("ReflexPatternMatcher initialized")

    def _compile_patterns(self):
        """编译所有模式"""
        pattern_map = {
            ReflexType.GREETING: self.GREETING_PATTERNS,
            ReflexType.EMERGENCY_STOP: self.EMERGENCY_STOP_PATTERNS,
            ReflexType.CONFIRMATION: self.CONFIRMATION_PATTERNS,
            ReflexType.DENIAL: self.DENIAL_PATTERNS,
            ReflexType.HELP: self.HELP_PATTERNS,
        }

        for reflex_type, rules in pattern_map.items():
            compiled = []
            for rule in rules:
                try:
                    pattern = re.compile(rule.pattern, re.IGNORECASE | re.UNICODE)
                    compiled.append((pattern, rule.weight))
                except re.error as e:
                    logger.error(f"Failed to compile pattern {rule.pattern}: {e}")

            self._pattern_groups[reflex_type] = compiled

    def match(self, text: str) -> tuple[ReflexType | None, float]:
        """
        匹配文本

        Returns:
            (匹配到的类型, 置信度)
        """
        best_match: ReflexType | None = None
        best_confidence = 0.0

        for reflex_type, patterns in self._pattern_groups.items():
            for pattern, weight in patterns:
                if pattern.search(text):
                    confidence = weight

                    # 完全匹配加分
                    if pattern.match(text):
                        confidence = min(1.0, confidence + 0.1)

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = reflex_type

                    # 高置信度可提前返回
                    if confidence >= 1.0:
                        return best_match, best_confidence

        return best_match, best_confidence

    def get_patterns_for_type(self, reflex_type: ReflexType) -> list[str]:
        """获取指定类型的所有模式字符串"""
        pattern_map = {
            ReflexType.GREETING: self.GREETING_PATTERNS,
            ReflexType.EMERGENCY_STOP: self.EMERGENCY_STOP_PATTERNS,
            ReflexType.CONFIRMATION: self.CONFIRMATION_PATTERNS,
            ReflexType.DENIAL: self.DENIAL_PATTERNS,
            ReflexType.HELP: self.HELP_PATTERNS,
        }

        rules = pattern_map.get(reflex_type, [])
        return [rule.pattern for rule in rules]

    def add_custom_pattern(
        self,
        reflex_type: ReflexType,
        pattern: str,
        weight: float = 1.0,
    ) -> bool:
        """添加自定义模式"""
        try:
            compiled = re.compile(pattern, re.IGNORECASE | re.UNICODE)

            if reflex_type not in self._pattern_groups:
                self._pattern_groups[reflex_type] = []

            self._pattern_groups[reflex_type].append((compiled, weight))
            logger.info(f"Added custom pattern for {reflex_type}: {pattern}")
            return True

        except re.error as e:
            logger.error(f"Invalid pattern {pattern}: {e}")
            return False


# 响应模板
REFLEX_RESPONSES = {
    ReflexType.GREETING: [
        "您好！有什么可以帮助您的吗？",
        "您好！请问有什么可以帮您？",
        "你好！很高兴为您服务。",
    ],
    ReflexType.EMERGENCY_STOP: [
        "已停止当前操作。",
        "操作已取消。",
        "已终止。",
    ],
    ReflexType.CONFIRMATION: [
        "好的，已确认。",
        "收到。",
        "明白。",
    ],
    ReflexType.DENIAL: [
        "好的，已取消。",
        "明白，已停止。",
        "已拒绝。",
    ],
    ReflexType.HELP: [
        "我可以帮您处理订单、查询库存、管理产品等。请告诉我具体需要什么帮助？",
        "我能帮您：查询订单状态、查看库存、产品管理等。请问需要哪方面的帮助？",
    ],
    ReflexType.UNKNOWN: [
        "我不太理解，能否再说清楚一些？",
    ],
}


def get_reflex_response(reflex_type: ReflexType, variation: int = 0) -> str:
    """获取反射响应"""
    responses = REFLEX_RESPONSES.get(reflex_type, [""])
    if not responses:
        return ""

    index = variation % len(responses)
    return responses[index]
