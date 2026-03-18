"""
日志工具函数模块

提供 NDJSON 日志、调试日志等工具函数。
"""

import os
import json
import time
from typing import Dict, Any


def get_debug_log_path() -> str:
    """
    获取调试日志文件路径
    
    Returns:
        调试日志文件路径
    """
    from .path_utils import get_log_dir
    return os.path.join(get_log_dir(), 'debug_ndjson.log')


def debug_ndjson(payload: Dict[str, Any]) -> None:
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


def debug_client_log() -> Dict[str, Any]:
    """
    处理客户端调试日志请求
    
    Returns:
        响应字典
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from flask import request
        data = request.get_json(silent=True) or {}
        
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
        level=getattr(logging, level.upper(), logging.INFO),
        format=format_string,
        encoding='utf-8'
    )
