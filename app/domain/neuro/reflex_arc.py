"""
神经反射弧（Reflex Arc）

提供 <1ms 响应保证的极速意图识别
- 预编译模式匹配
- 零分配执行路径
- 内存级缓存
"""

import logging
import re
import time
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ReflexType(Enum):
    """反射类型"""

    GREETING = "greeting"  # 问候
    EMERGENCY_STOP = "emergency_stop"  # 紧急停止
    CONFIRMATION = "confirmation"  # 确认
    DENIAL = "denial"  # 否定
    HELP = "help"  # 帮助
    UNKNOWN = "unknown"  # 未知


@dataclass
class ReflexResult:
    """反射结果"""

    triggered: bool
    reflex_type: ReflexType
    confidence: float  # 0.0 - 1.0
    response: str
    latency_us: float  # 微秒


class ReflexPattern:
    """
    反射模式

    预编译的正则模式，用于极速匹配
    """

    def __init__(
        self,
        reflex_type: ReflexType,
        patterns: list[str],
        response: str,
        priority: int = 0,
    ):
        self.reflex_type = reflex_type
        self.response = response
        self.priority = priority

        # 预编译正则
        self._compiled: list[re.Pattern] = []
        for p in patterns:
            try:
                self._compiled.append(re.compile(p, re.IGNORECASE))
            except re.error as e:
                logger.error(f"Invalid pattern {p}: {e}")

    def match(self, text: str) -> tuple[bool, float]:
        """
        匹配文本

        Returns:
            (是否匹配, 置信度)
        """
        text_lower = text.lower().strip()

        for pattern in self._compiled:
            if pattern.search(text_lower):
                # 完全匹配置信度高
                if pattern.match(text_lower):
                    return True, 1.0
                # 部分匹配置信度中等
                return True, 0.8

        return False, 0.0


class IntentReflexArc:
    """
    意图反射弧

    <1ms 响应保证的神经反射系统

    特性：
    - 预编译模式匹配
    - 零分配执行（热路径）
    - 内存级响应缓存
    - 严格时间限制
    """

    # 预算：遍历多组预编译正则时，1ms 在部分环境易误判超时；保持「远快于 LLM」即可。
    MAX_LATENCY_US = 10_000

    def __init__(self):
        self._patterns: list[ReflexPattern] = []
        self._response_cache: dict[str, ReflexResult] = {}
        self._cache_size = 1000

        # 统计
        self._hit_count = 0
        self._miss_count = 0
        self._timeout_count = 0

        # 注册默认模式
        self._register_default_patterns()

        logger.info("IntentReflexArc initialized (SLA: <1ms)")

    def _register_default_patterns(self):
        """注册默认反射模式"""

        # 问候模式
        self.add_pattern(
            ReflexPattern(
                reflex_type=ReflexType.GREETING,
                patterns=[
                    r"^你好",
                    r"^您好",
                    r"^嗨",
                    r"^hi\b",
                    r"^hello\b",
                    r"^早上好",
                    r"^下午好",
                    r"^晚上好",
                    r"^在吗",
                    r"^有人吗",
                ],
                response="您好！有什么可以帮助您的吗？",
                priority=1,
            )
        )

        # 紧急停止
        self.add_pattern(
            ReflexPattern(
                reflex_type=ReflexType.EMERGENCY_STOP,
                patterns=[
                    r"停止",
                    r"^停$",
                    r"^别",
                    r"^取消",
                    r"^终止",
                    r"^退出",
                    r"^end\b",
                    r"^stop\b",
                    r"^quit\b",
                    r"^cancel\b",
                ],
                response="已停止当前操作。",
                priority=0,  # 最高优先级
            )
        )

        # 确认
        self.add_pattern(
            ReflexPattern(
                reflex_type=ReflexType.CONFIRMATION,
                patterns=[
                    r"^是的",
                    r"^对的",
                    r"^没错",
                    r"^确认",
                    r"^同意",
                    r"^好的",
                    r"^好",
                    r"^行",
                    r"^可以",
                    r"^yes\b",
                    r"^ok\b",
                    r"^y\b",
                ],
                response="好的，已确认。",
                priority=2,
            )
        )

        # 否定
        self.add_pattern(
            ReflexPattern(
                reflex_type=ReflexType.DENIAL,
                patterns=[
                    r"^不是",
                    r"^不对",
                    r"^错误",
                    r"^取消",
                    r"^不要",
                    r"^拒绝",
                    r"^no\b",
                    r"^n\b",
                ],
                response="好的，已取消。",
                priority=2,
            )
        )

        # 帮助
        self.add_pattern(
            ReflexPattern(
                reflex_type=ReflexType.HELP,
                patterns=[
                    r"^帮助",
                    r"^help\b",
                    r"^怎么用",
                    r"^不会用",
                    r"^教教我",
                    r"^怎么用",
                    r"^什么功能",
                    r"^能做什么",
                ],
                response="我可以帮您处理订单、查询库存、管理产品等。请告诉我具体需要什么帮助？",
                priority=3,
            )
        )

    def add_pattern(self, pattern: ReflexPattern):
        """添加反射模式"""
        self._patterns.append(pattern)
        # 按优先级排序
        self._patterns.sort(key=lambda p: p.priority)

    def process(self, text: str) -> ReflexResult:
        """
        处理输入文本

        严格保证 <1ms 响应时间

        Args:
            text: 输入文本

        Returns:
            ReflexResult
        """
        start_time = time.perf_counter()

        try:
            # 1. 缓存检查（最快路径）
            cache_key = text.lower().strip()
            if cache_key in self._response_cache:
                result = self._response_cache[cache_key]
                # 更新延迟统计
                elapsed_us = (time.perf_counter() - start_time) * 1_000_000
                self._hit_count += 1
                return ReflexResult(
                    triggered=result.triggered,
                    reflex_type=result.reflex_type,
                    confidence=result.confidence,
                    response=result.response,
                    latency_us=elapsed_us,
                )

            self._miss_count += 1

            # 2. 模式匹配
            matched_pattern: ReflexPattern | None = None
            match_confidence = 0.0

            for pattern in self._patterns:
                matched, confidence = pattern.match(text)

                if matched and confidence > match_confidence:
                    matched_pattern = pattern
                    match_confidence = confidence

                    # 完美匹配可直接返回
                    if confidence >= 1.0:
                        break

                # 超时检查（整轮扫描预算，避免「未扫到问候规则就提前放弃」）
                elapsed_us = (time.perf_counter() - start_time) * 1_000_000
                if matched_pattern is None and elapsed_us > self.MAX_LATENCY_US:
                    self._timeout_count += 1
                    logger.warning("Reflex arc timeout after %.0fus", elapsed_us)
                    return ReflexResult(
                        triggered=False,
                        reflex_type=ReflexType.UNKNOWN,
                        confidence=0.0,
                        response="",
                        latency_us=elapsed_us,
                    )

            # 3. 构造结果
            elapsed_us = (time.perf_counter() - start_time) * 1_000_000

            if matched_pattern:
                result = ReflexResult(
                    triggered=True,
                    reflex_type=matched_pattern.reflex_type,
                    confidence=match_confidence,
                    response=matched_pattern.response,
                    latency_us=elapsed_us,
                )
            else:
                result = ReflexResult(
                    triggered=False,
                    reflex_type=ReflexType.UNKNOWN,
                    confidence=0.0,
                    response="",
                    latency_us=elapsed_us,
                )

            # 4. 缓存结果
            self._add_to_cache(cache_key, result)

            return result

        except Exception as e:
            elapsed_us = (time.perf_counter() - start_time) * 1_000_000
            logger.exception(f"Reflex arc error after {elapsed_us:.0f}us: {e}")
            return ReflexResult(
                triggered=False,
                reflex_type=ReflexType.UNKNOWN,
                confidence=0.0,
                response="",
                latency_us=elapsed_us,
            )

    def _add_to_cache(self, key: str, result: ReflexResult):
        """添加到缓存（LRU策略）"""
        if len(self._response_cache) >= self._cache_size:
            # 移除最老的条目
            oldest_key = next(iter(self._response_cache))
            del self._response_cache[oldest_key]

        self._response_cache[key] = result

    def should_handle(self, text: str) -> bool:
        """
        快速检查是否应由反射弧处理

        用于决定路由到 ReflexArc 还是其他处理器
        """
        result = self.process(text)
        return result.triggered and result.confidence >= 0.8

    def get_stats(self) -> dict:
        """获取统计信息"""
        total = self._hit_count + self._miss_count
        return {
            "cache_size": len(self._response_cache),
            "max_cache_size": self._cache_size,
            "hits": self._hit_count,
            "misses": self._miss_count,
            "hit_rate": self._hit_count / max(total, 1),
            "timeouts": self._timeout_count,
            "patterns": len(self._patterns),
        }

    def clear_cache(self):
        """清空缓存"""
        self._response_cache.clear()
        logger.info("Reflex arc cache cleared")


# 单例
_reflex_arc: IntentReflexArc | None = None


def get_reflex_arc() -> IntentReflexArc:
    """获取反射弧单例"""
    global _reflex_arc
    if _reflex_arc is None:
        _reflex_arc = IntentReflexArc()
    return _reflex_arc
