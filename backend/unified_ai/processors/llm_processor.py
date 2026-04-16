"""
LLM处理器 - Tool Calling
"""

import json
import time
import logging
from dataclasses import dataclass, field
from typing import Any

from ..utils.metrics import get_metrics

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    success: bool
    intent: str = ""
    confidence: float = 0.0
    entities: dict[str, Any] = field(default_factory=dict)
    response: str = ""
    processing_time_ms: float = 0.0
    error: str = ""


class LLMProcessor:
    def __init__(self):
        self._enabled = True
        self._timeout_ms = 10000

    async def process(self, user_input: str, context: dict[str, Any] | None = None) -> LLMResult:
        if not self._enabled:
            return LLMResult(success=False, error="LLM disabled")

        start = time.perf_counter()

        try:
            from backend.llm_config import get_llm_client, require_api_key

            try:
                require_api_key()
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000
                return LLMResult(
                    success=False,
                    error=f"LLM not available: {e}",
                    processing_time_ms=elapsed_ms
                )

            client = get_llm_client()

            intent_defs = []
            for name, intent in (context or {}).get("intent_registry", {}).items():
                intent_defs.append(f"- {name}: {intent.description}")

            default_intents = "- sales_contract: 生成销售合同\n- product_query: 查询产品\n- price_list_export: 导出价格表\n- general_chat: 通用对话"
            intent_list_str = chr(10).join(intent_defs) if intent_defs else default_intents

            prompt = f"""你是一个智能助手。请分析用户输入，识别其意图。

用户输入：{user_input}

可用意图：
{intent_list_str}

请以JSON格式返回分析结果：
{{
    "intent": "意图名称",
    "confidence": 0.0-1.0之间的置信度,
    "entities": {{"实体名称": "实体值"}},
    "response": "如果需要直接回复的文本（否则为空字符串）"
}}

只返回JSON，不要其他内容。"""

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
            )

            content = response.choices[0].message.content.strip()

            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            result = json.loads(content)

            elapsed_ms = (time.perf_counter() - start) * 1000
            get_metrics().histogram("llm_processor.duration_ms", elapsed_ms)
            get_metrics().inc("llm_processor.calls")

            logger.debug(f"[LLMProcessor] 完成 ({elapsed_ms:.2f}ms)")

            return LLMResult(
                success=True,
                intent=result.get("intent", "general_chat"),
                confidence=result.get("confidence", 0.8),
                entities=result.get("entities", {}),
                response=result.get("response", ""),
                processing_time_ms=elapsed_ms
            )

        except json.JSONDecodeError as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.warning(f"[LLMProcessor] JSON解析失败: {e}, content: {content if 'content' in dir() else 'N/A'}")
            return LLMResult(
                success=False,
                error=f"JSON解析失败: {e}",
                processing_time_ms=elapsed_ms
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.warning(f"[LLMProcessor] 处理异常: {e}")
            return LLMResult(
                success=False,
                error=str(e),
                processing_time_ms=elapsed_ms
            )

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False
