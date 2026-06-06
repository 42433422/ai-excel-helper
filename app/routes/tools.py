"""
兼容层：``_parse_order_text`` / 工具执行等由 ``app.services.tools_execution_service`` 提供。
"""

from __future__ import annotations

from app.application.facades.tools_facade import (
    _parse_order_text,
    execute_registered_workflow_tool,
    execute_tool_from_payload,
    get_workflow_tool_registry,
    set_tool_execute_headers,
)

__all__ = [
    "execute_registered_workflow_tool",
    "execute_tool_from_payload",
    "get_workflow_tool_registry",
    "run_archive_tools_execute",
    "set_tool_execute_headers",
    "_parse_order_text",
]


def run_archive_tools_execute(body: dict | None) -> tuple[dict, int]:
    """
    调用 ``execute_tool_from_payload``（Werkzeug JSON Response）。

    供原生 FastAPI 路由 ``POST /api/tools/execute`` 复用。
    """
    raw = execute_tool_from_payload(body or {})

    if isinstance(raw, tuple):
        resp = raw[0]
        code = int(raw[1]) if len(raw) > 1 else 200
    else:
        resp = raw
        code = int(getattr(resp, "status_code", 200) or 200)

    if hasattr(resp, "get_json"):
        data = resp.get_json(silent=True)
        if not isinstance(data, dict):
            return {"success": False, "message": "invalid tools response"}, 500
        return data, code

    return {"success": False, "message": "invalid tools response"}, 500
