"""
日志工具函数模块

提供 NDJSON 日志、调试日志等工具函数。
"""

import json
import os
import time
from typing import Any


def get_debug_log_path() -> str:
    """
    获取调试日志文件路径

    Returns:
        调试日志文件路径
    """
    from .path_utils import get_log_dir

    return os.path.join(get_log_dir(), "debug_ndjson.log")


def ingest_client_debug_json(data: dict[str, Any] | None) -> dict[str, Any]:
    """
    将前端 ``/api/debug/client-log`` 的 JSON 体规范后写入 ``debug_ndjson.log``。

    FastAPI 路由应直接传入解析后的 body，不再依赖 ``request._body``。
    """
    data = dict(data or {})
    payload = {
        "runId": data.get("runId") or "client",
        "hypothesisId": data.get("hypothesisId") or "H?",
        "location": data.get("location") or "client",
        "message": data.get("message") or "event",
        "data": data.get("data") if isinstance(data.get("data"), dict) else {},
        "timestamp": int(time.time() * 1000),
    }
    debug_ndjson(payload)
    return {"success": True}


def debug_ndjson(payload: dict[str, Any]) -> None:
    """
    写入一行 NDJSON 格式的调试日志

    Args:
        payload: 要记录的数据字典
    """
    try:
        payload = dict(payload or {})
        payload.setdefault("timestamp", int(time.time() * 1000))

        log_path = get_debug_log_path()
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def debug_client_log() -> dict[str, Any]:
    """
    处理客户端调试日志请求

    Returns:
        响应字典
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        data: dict[str, Any] = {}
        from app.http.request_context import get_current_http_request

        req = get_current_http_request()
        if req is not None:
            raw = getattr(req, "_body", None)
            if raw:
                try:
                    data = json.loads(raw.decode())
                except Exception:
                    data = {}
            else:
                data = {}

        return ingest_client_debug_json(data)
    except Exception as e:
        logger.exception("处理客户端调试日志失败")
        return {"success": False, "message": str(e)}


def setup_logging(level: str = "INFO", format_string: str = None) -> None:
    """
    配置日志系统

    Args:
        level: 日志级别
        format_string: 日志格式字符串
    """
    import logging

    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO), format=format_string, encoding="utf-8"
    )
