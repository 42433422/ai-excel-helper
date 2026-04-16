"""
OpenAI-compatible Chat API credentials + 离线模式路由。

优先使用 DP / DeepSeek（与站点「DeepSeek AI」一致），其次 OpenAI 官方。
支持 LLM_MODE=offline 切换到 Ollama 本地模型。
"""

from __future__ import annotations

import os
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

# DeepSeek 官方 OpenAI 兼容网关（仅在使用 DP/DeepSeek 密钥且未显式配置 base_url 时作为默认）
_DEFAULT_DEEPSEEK_BASE = "https://api.deepseek.com"

# 运行时模式缓存（支持动态切换）
_current_mode: str | None = None
_offline_model_override: str | None = None


def resolve_mode() -> str:
    """返回当前 LLM 模式：'online' 或 'offline'。"""
    global _current_mode
    if _current_mode is not None:
        return _current_mode
    return os.environ.get("LLM_MODE", "online").strip().lower()


def set_mode(mode: str, model: str | None = None) -> None:
    """运行时切换 LLM 模式（用于 /api/mode POST 接口）。"""
    global _current_mode, _offline_model_override
    _current_mode = mode.strip().lower()
    if model:
        _offline_model_override = model.strip()
    logger.info("llm_mode switched to %s (model=%s)", _current_mode, model or "-")


def resolve_api_key() -> str | None:
    if resolve_mode() == "offline":
        return "ollama"
    return (
        os.environ.get("DP_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )


def resolve_base_url() -> str | None:
    if resolve_mode() == "offline":
        return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    explicit = (
        os.environ.get("DP_BASE_URL")
        or os.environ.get("DEEPSEEK_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
    )
    if explicit:
        return explicit.strip() or None
    # 用户只配了 DP/DeepSeek key 时，默认走 DeepSeek 网关
    if os.environ.get("DP_API_KEY") or os.environ.get("DEEPSEEK_API_KEY"):
        return _DEFAULT_DEEPSEEK_BASE
    return None


def resolve_chat_model() -> str:
    if resolve_mode() == "offline":
        return _offline_model_override or os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    m = (
        os.environ.get("DP_MODEL")
        or os.environ.get("DEEPSEEK_MODEL")
        or os.environ.get("LLM_MODEL")
    )
    if m:
        return m
    base = (resolve_base_url() or "").lower()
    if "deepseek" in base:
        return "deepseek-chat"
    return "gpt-4o-mini"


def require_api_key() -> str:
    """离线模式下跳过 API Key 校验，返回占位值。"""
    if resolve_mode() == "offline":
        return "ollama-offline"
    key = resolve_api_key()
    if not key:
        raise RuntimeError(
            "未配置大模型 API Key：请设置 DP_API_KEY 或 DEEPSEEK_API_KEY 或 OPENAI_API_KEY"
            "\n或设置 LLM_MODE=offline 使用本地模型"
        )
    return key


def get_openai_compatible_client() -> OpenAI:
    """
    获取在线 OpenAI 兼容客户端。
    注意：此函数在离线模式下会抛出异常，请使用 get_llm_client() 替代。
    """
    return OpenAI(
        api_key=require_api_key(),
        base_url=resolve_base_url(),
    )


def get_llm_client():
    """
    统一客户端工厂：根据 LLM_MODE 返回在线 OpenAI 客户端或离线 OfflineClient。

    返回的客户端统一支持 .chat.completions.create() 接口，
    planner / text-to-pandas / schema-service 可无感知使用。
    """
    mode = resolve_mode()
    if mode == "offline":
        from backend.offline_llm import get_offline_client

        model = _offline_model_override or os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
        base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        logger.info("using offline LLM client: base=%s model=%s", base, model)
        return get_offline_client(base_url=base, model=model)

    logger.info("using online LLM client: base=%s", resolve_base_url())
    return get_openai_compatible_client()


def get_offline_status() -> dict:
    """获取离线模式的可用状态信息。"""
    from backend.offline_llm import check_ollama_available

    available, models = check_ollama_available()
    current_model = _offline_model_override or os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    return {
        "available": available,
        "ollama_running": available,
        "models": models,
        "current_model": current_model,
    }
