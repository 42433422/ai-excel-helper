"""统一凭证解析：env → OPENAI/DEEPSEEK → 可选 resources 配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMCredentials:
    api_key: str
    api_url: str
    model: str


def default_chat_completions_url() -> str:
    creds = resolve_deepseek_credentials()
    return creds.api_url if creds else "https://api.deepseek.com/v1/chat/completions"


def resolve_deepseek_credentials() -> LLMCredentials | None:
    key = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    if not key:
        return None
    url = (
        os.environ.get("DEEPSEEK_API_URL") or ""
    ).strip() or "https://api.deepseek.com/v1/chat/completions"
    model = (os.environ.get("DEEPSEEK_MODEL") or "").strip() or "deepseek-chat"
    return LLMCredentials(api_key=key, api_url=url, model=model)


def resolve_openai_env_credentials() -> tuple[str, str | None]:
    """与 infrastructure.llm.client._first_api_key 一致。"""
    oa = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if oa:
        base = (os.environ.get("OPENAI_BASE_URL") or "").strip() or None
        return oa, base
    ds = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    if ds:
        base = (os.environ.get("OPENAI_BASE_URL") or "").strip() or "https://api.deepseek.com"
        return ds, base
    return "", None
