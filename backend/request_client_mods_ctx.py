"""HTTP 请求内「客户端原版模式」标记（由请求头注入，进程内 ContextVar）。"""

from __future__ import annotations

from contextvars import ContextVar, Token

_client_mods_ui_off: ContextVar[bool] = ContextVar("client_mods_ui_off", default=False)


def get_request_client_mods_ui_off() -> bool:
    return _client_mods_ui_off.get()


def set_request_client_mods_ui_off(value: bool) -> Token:
    return _client_mods_ui_off.set(bool(value))


def reset_request_client_mods_ui_off(token: Token) -> None:
    _client_mods_ui_off.reset(token)


def parse_client_mods_off_header(headers_lower: dict[str, str]) -> bool:
    """解析 ASGI/FastAPI 已规范为小写键名的 headers 映射。"""
    for hk in ("x-client-mods-off", "x-xcagi-client-mods-off"):
        raw = str(headers_lower.get(hk, "")).strip().lower()
        if raw in ("1", "true", "yes", "on"):
            return True
    return False
