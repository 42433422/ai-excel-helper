"""
OpenAI 兼容客户端与 online/offline（Ollama）模式切换。

进程内全局状态，供 ``http_app``、``planner``、XCAGI 兼容路由使用。
"""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.error
import urllib.request
from typing import Any, Literal

logger = logging.getLogger(__name__)

_mode_lock = threading.Lock()
_client_lock = threading.Lock()

_mode: Literal["online", "offline"]
_offline_model: str | None = None
_openai_client: Any | None = None


def _env_mode() -> Literal["online", "offline"] | None:
    raw = (os.environ.get("FHD_LLM_MODE") or os.environ.get("LLM_MODE") or "").strip().lower()
    if raw in ("offline", "local", "ollama"):
        return "offline"
    if raw in ("online", "cloud", "api"):
        return "online"
    return None


def _initial_mode() -> Literal["online", "offline"]:
    m = _env_mode()
    if m is not None:
        return m
    return "online"


_mode = _initial_mode()


def resolve_mode() -> Literal["online", "offline"]:
    with _mode_lock:
        return _mode


def set_mode(mode: str, model: str | None = None) -> None:
    """切换 ``online`` / ``offline``；offline 时可传入 Ollama 模型名。"""
    global _mode, _offline_model, _openai_client
    if mode not in ("online", "offline"):
        raise ValueError("mode must be 'online' or 'offline'")
    with _mode_lock:
        _mode = mode  # type: ignore[assignment]
        if mode == "offline":
            if model is not None:
                s = str(model).strip()
                _offline_model = s or None
        else:
            _offline_model = None
    with _client_lock:
        _openai_client = None


def _first_api_key() -> tuple[str, str | None]:
    """
    返回 (api_key, base_url 可选)。
    优先 OPENAI；否则 DeepSeek（常用兼容基座）。
    """
    oa = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if oa:
        base = (os.environ.get("OPENAI_BASE_URL") or "").strip() or None
        return oa, base
    ds = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    if ds:
        base = (os.environ.get("OPENAI_BASE_URL") or "").strip() or "https://api.deepseek.com"
        return ds, base
    return "", None


def require_api_key() -> None:
    if resolve_mode() == "offline":
        return
    key, _ = _first_api_key()
    if not key:
        raise RuntimeError(
            "未配置 OPENAI_API_KEY（或 DEEPSEEK_API_KEY）；online 模式下无法调用云端大模型。"
        )


def get_llm_client() -> Any | None:
    """
    online：返回 ``openai.OpenAI`` 单例（需已配置密钥）。
    offline：返回 ``None``（由本地 Ollama 等路径处理，不强制云端客户端）。
    """
    if resolve_mode() == "offline":
        return None
    require_api_key()
    global _openai_client
    with _client_lock:
        if _openai_client is not None:
            return _openai_client
        from openai import OpenAI

        api_key, base_url = _first_api_key()
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        _openai_client = OpenAI(**kwargs)
        return _openai_client


def dispose_llm_client() -> None:
    global _openai_client
    with _client_lock:
        _openai_client = None


def get_offline_status() -> dict[str, Any]:
    """供 ``GET /api/mode`` 展示本机 Ollama 是否可达。"""
    host = (os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
    url = f"{host}/api/tags"
    with _mode_lock:
        preferred = _offline_model
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        models_raw = body.get("models") or []
        names: list[str] = []
        for m in models_raw:
            if isinstance(m, dict) and m.get("name"):
                names.append(str(m["name"]))
            elif isinstance(m, str):
                names.append(m)
        return {
            "ollama_host": host,
            "ollama_reachable": True,
            "models": names,
            "preferred_offline_model": preferred,
        }
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as e:
        logger.debug("ollama probe failed: %s", e)
        return {
            "ollama_host": host,
            "ollama_reachable": False,
            "models": [],
            "preferred_offline_model": preferred,
            "error": str(e),
        }
