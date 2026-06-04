"""包装 services.conversation.llm_adapter.OpenAICompatibleAdapter。"""
from __future__ import annotations

import os
import time
from typing import Any

from app.utils.metrics import record_ai_call


class OpenAICompatibleProvider:
    provider_id = "openai_compatible"

    def __init__(self, adapter: Any | None = None):
        self._adapter = adapter

    @property
    def is_configured(self) -> bool:
        if self._adapter is not None:
            return bool(getattr(self._adapter, "is_configured", False))
        from app.infrastructure.llm.providers.credentials import resolve_openai_env_credentials

        key, _ = resolve_openai_env_credentials()
        return bool(key)

    def _ensure_adapter(self) -> Any | None:
        if self._adapter is not None:
            return self._adapter
        import os

        from app.services.conversation.llm_adapter import OpenAICompatibleAdapter

        provider = (os.environ.get("LLM_PROVIDER") or os.environ.get("XCAGI_LLM_PROVIDER") or "deepseek").strip()
        api_key = (os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or "").strip()
        if not api_key:
            return None
        self._adapter = OpenAICompatibleAdapter(
            provider=provider,
            api_key=api_key,
            model=(os.environ.get("LLM_MODEL") or os.environ.get("DEEPSEEK_MODEL") or "").strip() or None,
            base_url=(os.environ.get("OPENAI_BASE_URL") or "").strip() or None,
        )
        return self._adapter

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        adapter = self._ensure_adapter()
        if adapter is None or not getattr(adapter, "is_configured", False):
            return None
        t0 = time.perf_counter()
        try:
            result = await adapter.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            record_ai_call(self.provider_id, "chat", "success", time.perf_counter() - t0)
            return result
        except Exception:
            record_ai_call(self.provider_id, "chat", "error", time.perf_counter() - t0)
            raise
