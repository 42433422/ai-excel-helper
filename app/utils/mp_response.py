"""
小程序 API 统一响应工具（基于 Werkzeug Response 工具）。
"""

from __future__ import annotations

from typing import Any

from app.http.json_response import json_response


def success(data=None, message="success", code=200):
    """成功响应"""
    body: dict[str, Any] = {
        "code": code,
        "message": message,
        "success": True,
    }
    if data is not None:
        body["data"] = data
    return json_response(body, code), code


def error(message="error", code=400, data=None):
    """错误响应"""
    body: dict[str, Any] = {
        "code": code,
        "message": message,
        "success": False,
    }
    if data is not None:
        body["data"] = data
    return json_response(body, code), code


def paginate(items, total, page=1, page_size=20, **extra):
    """分页响应"""
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    payload = {
        "items": items,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
        **extra,
    }
    return success(data=payload)
