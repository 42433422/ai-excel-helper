"""包装 ModstorePlatformAdapter。"""
from __future__ import annotations

import time
from typing import Any

from app.utils.metrics import record_ai_call


class ModstoreProvider:
    provider_id = "modstore"

    def __init__(self, adapter: Any | None = None):
        self._adapter = adapter

    @property
    def is_configured(self) -> bool:
        return self._adapter is not None

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        if self._adapter is None:
            return None
        t0 = time.perf_counter()
        try:
            result = await self._adapter.chat_completion(
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
