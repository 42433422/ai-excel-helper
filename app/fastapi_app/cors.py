"""CORS 白名单与开发态局域网 Origin 正则。"""

from __future__ import annotations

import os


def resolve_cors_allow_origins() -> list[str]:
    raw = (os.environ.get("CORS_ALLOW_ORIGINS") or "").strip()
    if raw:
        origins = [x.strip() for x in raw.split(",") if x.strip() and x.strip() != "*"]
        if origins:
            return origins
    return [
        "http://127.0.0.1:5001",
        "http://localhost:5001",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:5000",
        "http://localhost:5000",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]


def lan_origin_regex_enabled() -> bool:
    """是否启用私网 Origin 正则（手机 / 平板用 http://192.168.*.*:5001 打开前端时 CORS 预检需要）。"""
    raw = (os.environ.get("XCAGI_DEV_ALLOW_LAN_CORS") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return os.environ.get("XCAGI_DEBUG", "1").strip() == "1"


def resolve_cors_allow_origin_regex() -> str | None:
    """
    与 allow_origins 并列；用于开发机局域网 IP 访问 Vite（如 http://192.168.1.2:5001）
    且带 credentials 的 API 预检。生产请设 XCAGI_DEBUG=0，并显式配置 CORS_ALLOW_ORIGINS。
    """
    explicit = (os.environ.get("CORS_ALLOW_ORIGIN_REGEX") or "").strip()
    if explicit:
        return explicit
    if lan_origin_regex_enabled():
        return (
            r"^http://(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            r"|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})(:\d+)?$"
        )
    return None
