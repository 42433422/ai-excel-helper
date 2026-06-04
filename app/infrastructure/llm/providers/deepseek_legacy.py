"""DeepSeek 直连降级 Provider（httpx，OpenAI 兼容 JSON）。"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.infrastructure.llm.providers.credentials import resolve_deepseek_credentials
from app.utils.metrics import record_ai_call

logger = logging.getLogger(__name__)


class DeepSeekLegacyProvider:
    provider_id = "deepseek_legacy"

    def __init__(self, *, api_key: str | None = None, api_url: str | None = None, model: str | None = None):
        creds = resolve_deepseek_credentials()
        self._api_key = (api_key or (creds.api_key if creds else "")).strip()
        self._api_url = (api_url or (creds.api_url if creds else "")).strip() or (
            "https://api.deepseek.com/v1/chat/completions"
        )
        self._model = (model or (creds.model if creds else "")).strip() or "deepseek-chat"

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        if not self.is_configured:
            return None
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self._api_url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
            usage = result.get("usage") or {}
            tokens = int(usage.get("total_tokens") or 0)
            record_ai_call(
                self.provider_id,
                "chat",
                "success",
                time.perf_counter() - t0,
            )
            return result
        except Exception as exc:
            record_ai_call(self.provider_id, "chat", "error", time.perf_counter() - t0)
            logger.error("DeepSeekLegacyProvider failed: %s", exc)
            return None
