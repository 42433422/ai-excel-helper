"""Werkzeug 风格 URL 规则与 OpenAPI 路径模板之间的相互转换。

原实现位于 ``app.fastapi_routes.archive_explicit_proxy``,Phase 2C 迁入 utils
以让 ``scripts/route_inventory_diff.py``、``scripts/check_openapi_consistency.py``
等脚本摆脱对 archive 模块的依赖。
"""

from __future__ import annotations

import re
from collections.abc import Iterable

__all__ = [
    "url_rule_to_openapi_path",
    "normalize_path_template",
    "filter_proxy_request_headers",
]

_SKIP_REQUEST_HEADERS: frozenset[str] = frozenset(
    {"host", "content-length", "connection", "transfer-encoding"}
)


def url_rule_to_openapi_path(rule: str) -> str:
    """``/api/x/<int:a>/<path:p>`` → ``/api/x/{a:int}/{p:path}``"""

    def repl(m: re.Match[str]) -> str:
        conv = m.group(1)
        name = m.group(2)
        if conv == "int":
            return f"{{{name}:int}}"
        if conv == "float":
            return f"{{{name}:float}}"
        if conv == "path":
            return f"{{{name}:path}}"
        if conv == "uuid":
            return f"{{{name}}}"
        if conv == "string" or conv is None:
            return f"{{{name}}}"
        return f"{{{name}}}"

    return re.sub(
        r"<(?:(int|float|path|string|uuid):)?([a-zA-Z_][a-zA-Z0-9_]*)>",
        repl,
        rule,
    )


def normalize_path_template(path: str) -> str:
    """用于与已注册 FastAPI 路由比对（去掉 ``{x:int}`` 中的类型）。"""
    if not path:
        return "/"
    p = path if path == "/" else path.rstrip("/") or "/"
    return re.sub(r"\{([^:}]+):[^}]+\}", r"{\1}", p)


def filter_proxy_request_headers(raw: Iterable[tuple[bytes, bytes]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in raw:
        key = k.decode("latin-1")
        if key.lower() in _SKIP_REQUEST_HEADERS:
            continue
        out[key] = v.decode("latin-1")
    return out
