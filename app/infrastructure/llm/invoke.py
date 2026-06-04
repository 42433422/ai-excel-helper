"""卫星调用点统一入口 — 避免硬编码 api.deepseek.com。"""

from __future__ import annotations

import logging
from typing import Any

from app.infrastructure.llm.providers.registry import get_active_provider

logger = logging.getLogger(__name__)


async def chat_completion_openai_format(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    profile: str = "default",
    request: Any | None = None,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """按 LLM_ROUTING_ORDER / LLM_PROVIDER 解析 Provider 并调用 chat/completions。"""
    provider = get_active_provider(request=request, profile=profile)
    if provider is None:
        logger.error("No configured LLM provider (profile=%s)", profile)
        return None
    return await provider.chat_completion(
        messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )
