"""LLM Provider 协议与统一返回结构。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ChatResult:
    """OpenAI chat/completions 兼容的精简结果。"""

    raw: dict[str, Any]
    provider_id: str
    model: str
    token_count: int = 0

    @property
    def content(self) -> str:
        choices = self.raw.get("choices") or []
        if not choices:
            return ""
        msg = choices[0].get("message") or {}
        return str(msg.get("content") or "")


@runtime_checkable
class LLMProvider(Protocol):
    """可插拔 LLM 提供方。"""

    @property
    def provider_id(self) -> str:
        ...

    @property
    def is_configured(self) -> bool:
        ...

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        ...
