"""微信小程序风格 JSON 响应（基于 Werkzeug Response 工具）。"""

from __future__ import annotations

from typing import Any

from app.http.json_response import json_response


def jsonify_response(code: int, message: str, data: Any = None, success: bool = True):
    """与历史 ``app.routes.wechat_miniprogram`` 字段一致：code / message / success / data。"""
    response_data: dict[str, Any] = {
        "code": code,
        "message": message,
        "success": success,
    }
    if data is not None:
        response_data["data"] = data
    return json_response(response_data, code), code
