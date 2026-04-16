"""
反射弧处理器 - <1ms 预定义响应
"""

import time
import logging
from dataclasses import dataclass
from typing import Any

from ..registry.reflex_registry import match_reflex, ReflexPattern
from ..utils.metrics import get_metrics

logger = logging.getLogger(__name__)


@dataclass
class ReflexResult:
    matched: bool
    response: str = ""
    intent: str = "unknown"
    processing_time_ms: float = 0.0
    reflex_name: str = ""


class ReflexProcessor:
    def __init__(self):
        self._enabled = True

    def process(self, user_input: str) -> ReflexResult:
        if not self._enabled:
            return ReflexResult(matched=False)

        start = time.perf_counter()

        try:
            pattern = match_reflex(user_input)
            if pattern:
                elapsed_ms = (time.perf_counter() - start) * 1000
                get_metrics().histogram("reflex_processor.duration_ms", elapsed_ms)
                get_metrics().inc("reflex_processor.hit")

                logger.debug(f"[ReflexProcessor] 命中反射: {pattern.regex.pattern} ({elapsed_ms:.2f}ms)")

                return ReflexResult(
                    matched=True,
                    response=pattern.response,
                    intent=pattern.intent,
                    processing_time_ms=elapsed_ms,
                    reflex_name=pattern.regex.pattern
                )

            elapsed_ms = (time.perf_counter() - start) * 1000
            return ReflexResult(matched=False, processing_time_ms=elapsed_ms)

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.warning(f"[ReflexProcessor] 处理异常: {e}")
            return ReflexResult(matched=False, processing_time_ms=elapsed_ms)

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False
