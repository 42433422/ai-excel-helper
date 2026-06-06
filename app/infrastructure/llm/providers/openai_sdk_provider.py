"""包装 infrastructure.llm.client OpenAI SDK 单例。"""

from __future__ import annotations

import time
from typing import Any

from app.utils.metrics import record_ai_call


class OpenAISdkProvider:
    provider_id = "openai_sdk"

    @property
    def is_configured(self) -> bool:
        from app.infrastructure.llm.client import get_llm_client

        return get_llm_client() is not None

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        import asyncio
        import os

        from app.infrastructure.llm.client import get_llm_client, require_api_key

        require_api_key()
        client = get_llm_client()
        if client is None:
            return None
        model_name = model or (os.environ.get("OPENAI_MODEL") or "").strip() or "deepseek-chat"
        t0 = time.perf_counter()

        def _sync_call() -> dict[str, Any]:
            resp = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **{k: v for k, v in kwargs.items() if k not in ("model",)},
            )
            if hasattr(resp, "model_dump"):
                return resp.model_dump()
            return dict(resp)  # type: ignore[arg-type]

        try:
            result = await asyncio.to_thread(_sync_call)
            record_ai_call(self.provider_id, "chat", "success", time.perf_counter() - t0)
            return result
        except Exception:
            record_ai_call(self.provider_id, "chat", "error", time.perf_counter() - t0)
            raise
