"""
Mod 员工脚本用的窄 LLM 入口（经 ``app.mod_sdk`` 暴露）。

由 MODstore 生成的 ``mods/<id>/backend/blueprints.py`` 内 ``_call_llm`` 优先调用本模块，
避免 Mod 代码直接依赖 ``app.services.*`` 或 ``modstore_server``。

支持 OpenAI 兼容 Chat Completions：
- 默认委托 ``AIConversationService.call_deepseek_api``（与宿主 DEEPSEEK 配置一致）。
- 可选：设置 ``XCAGI_LLM_PROVIDER`` + ``{PROVIDER}_API_KEY`` + ``{PROVIDER}_BASE_URL``（或内置默认 URL）
  时，对该 URL 直接发起 ``httpx`` 请求（真正切换供应商，而非仅改文案）。
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_CHAT_URLS: dict[str, str] = {
    "deepseek": "https://api.deepseek.com/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
}


def _resolve_provider_override() -> dict[str, Any]:
    """若配置了 provider + key（及可选 base_url），则走直连 OpenAI 兼容 API。"""
    provider = os.environ.get("XCAGI_LLM_PROVIDER", "").strip().lower()
    api_key = ""
    base_url: str | None = None
    model: str | None = None

    if provider:
        env_key = f"{provider.upper()}_API_KEY"
        api_key = os.environ.get(env_key, "").strip()
        env_base = f"{provider.upper()}_BASE_URL"
        bu = os.environ.get(env_base, "").strip()
        if bu:
            base_url = bu.rstrip("/")
        model = os.environ.get(f"{provider.upper()}_MODEL", "").strip() or None

    if not api_key or not provider:
        return {"use_direct": False}

    if not base_url:
        base_url = _DEFAULT_CHAT_URLS.get(provider)
    if not base_url:
        return {
            "use_direct": False,
            "error": f"未设置 {provider.upper()}_BASE_URL，且无内置默认 chat/completions URL",
        }

    chat_url = base_url if "/chat/completions" in base_url else f"{base_url}/v1/chat/completions"

    if not model:
        model = os.environ.get("XCAGI_EMPLOYEE_LLM_MODEL", "").strip() or (
            "gpt-4o-mini" if provider == "openai" else "deepseek-chat"
        )

    return {
        "use_direct": True,
        "api_key": api_key,
        "chat_url": chat_url,
        "model": model,
        "provider": provider,
    }


async def _call_openai_compatible_chat(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    chat_url: str,
    model: str,
    max_tokens: int,
    temperature: float,
    response_format: Any,
) -> dict[str, Any] | None:
    import httpx

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
    }
    if response_format is not None:
        payload["response_format"] = response_format

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
            r = await client.post(chat_url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()
    except Exception as e:  # noqa: BLE001
        logger.exception("mod_employee_complete: OpenAI-compatible chat 请求失败: %s", e)
        return None


async def mod_employee_complete(
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 1024,
    temperature: float = 0.2,
    response_format: Any = None,
) -> dict[str, Any]:
    """
    为员工 ``run(payload, ctx)`` 提供单次补全，返回形状与 MODstore ``chat_dispatch`` 对齐::

        {"ok": bool, "content": str, "error": str}

    ``response_format`` 若不为 None，会原样传入底层 API（若上游支持）。
    """
    if not isinstance(messages, list) or not messages:
        return {"ok": False, "content": "", "error": "messages 必须为非空列表"}

    override = _resolve_provider_override()
    if override.get("error"):
        return {"ok": False, "content": "", "error": str(override["error"])[:500]}

    if override.get("use_direct"):
        raw = await _call_openai_compatible_chat(
            messages,
            api_key=str(override["api_key"]),
            chat_url=str(override["chat_url"]),
            model=str(override["model"]),
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
        )
        if not raw:
            return {
                "ok": False,
                "content": "",
                "error": "LLM 返回空（请检查密钥、BASE_URL 与网络）",
            }
        return _parse_chat_completions_response(raw)

    try:
        from app.services.ai_conversation_service import get_ai_conversation_service
    except ImportError as e:
        logger.warning("mod_employee_complete: get_ai_conversation_service 不可用: %s", e)
        return {"ok": False, "content": "", "error": "get_ai_conversation_service not available"}

    svc = get_ai_conversation_service()
    if not getattr(svc, "api_key", None):
        return {
            "ok": False,
            "content": "",
            "error": "宿主未配置 DEEPSEEK_API_KEY（或 resources/config/deepseek_config.py），无法为员工调用 LLM",
        }

    kwargs: dict[str, Any] = {}
    if response_format is not None:
        kwargs["response_format"] = response_format

    try:
        raw: dict[str, Any] | None = await svc.call_deepseek_api(
            messages,
            temperature=float(temperature),
            max_tokens=int(max_tokens),
            **kwargs,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("mod_employee_complete: call_deepseek_api 异常")
        return {"ok": False, "content": "", "error": str(e)[:500]}

    if not raw:
        return {"ok": False, "content": "", "error": "LLM 返回空（请检查密钥与网络）"}

    return _parse_chat_completions_response(raw)


def _parse_chat_completions_response(raw: dict[str, Any]) -> dict[str, Any]:
    try:
        choices = raw.get("choices")
        if not choices:
            return {"ok": False, "content": "", "error": "LLM 响应缺少 choices"}
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if content is None:
            return {"ok": False, "content": "", "error": "LLM 响应缺少 message.content"}
        return {"ok": True, "content": str(content), "error": ""}
    except (KeyError, IndexError, TypeError) as e:
        return {"ok": False, "content": "", "error": f"无法解析 LLM 响应: {e}"[:500]}
