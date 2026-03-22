# -*- coding: utf-8 -*-
"""
结构化日志模块

提供 JSON 格式的结构化日志，支持标准字段和上下文传递。
"""

import json
import logging
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional


class StructuredLogFormatter(logging.Formatter):
    """JSON 格式日志格式化器"""

    DEFAULT_FIELDS = {
        "service": "xcagi",
        "environment": "production",
        "version": "1.0.0"
    }

    def __init__(self, service_name: str = "xcagi", environment: str = "production", version: str = "1.0.0"):
        super().__init__()
        self.service_name = service_name
        self.environment = environment
        self.version = version

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "service": self.service_name,
            "environment": self.environment,
            "version": self.version,
        }

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "duration"):
            log_data["duration_ms"] = record.duration
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        if hasattr(record, "error_code"):
            log_data["error_code"] = record.error_code
        if hasattr(record, "stack_id"):
            log_data["stack_id"] = record.stack_id

        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }

        return json.dumps(log_data, ensure_ascii=False)


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._context: Dict[str, Any] = {}
        
    def _log(
        self, 
        level: int, 
        message: str, 
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        duration: Optional[float] = None,
        **kwargs
    ):
        extra = {"extra_data": kwargs} if kwargs else {}
        if request_id:
            extra["request_id"] = request_id
        if user_id:
            extra["user_id"] = user_id
        if duration is not None:
            extra["duration"] = duration
            
        self.logger.log(level, message, extra=extra)
        
    def debug(self, msg: str, **kwargs):
        self._log(logging.DEBUG, msg, **kwargs)
        
    def info(self, msg: str, **kwargs):
        self._log(logging.INFO, msg, **kwargs)
        
    def warning(self, msg: str, **kwargs):
        self._log(logging.WARNING, msg, **kwargs)
        
    def error(self, msg: str, **kwargs):
        self._log(logging.ERROR, msg, **kwargs)
        
    def critical(self, msg: str, **kwargs):
        self._log(logging.CRITICAL, msg, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    """获取结构化日志记录器"""
    return StructuredLogger(name)


def setup_structured_logging(
    level: int = logging.INFO,
    service_name: str = "xcagi",
    environment: str = "production",
    version: str = "1.0.0"
):
    """配置结构化日志"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredLogFormatter(service_name, environment, version))

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]


def log_operation(operation_name: str):
    """操作日志装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            request_id = str(uuid.uuid4())
            
            try:
                logger.info(
                    f"Operation started: {operation_name}",
                    operation=operation_name,
                    request_id=request_id
                )
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                logger.info(
                    f"Operation completed: {operation_name}",
                    operation=operation_name,
                    request_id=request_id,
                    duration=duration
                )
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logger.error(
                    f"Operation failed: {operation_name}",
                    operation=operation_name,
                    request_id=request_id,
                    duration=duration,
                    error=str(e)
                )
                raise
                
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            request_id = str(uuid.uuid4())
            
            try:
                logger.info(
                    f"Operation started: {operation_name}",
                    operation=operation_name,
                    request_id=request_id
                )
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                logger.info(
                    f"Operation completed: {operation_name}",
                    operation=operation_name,
                    request_id=request_id,
                    duration=duration
                )
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logger.error(
                    f"Operation failed: {operation_name}",
                    operation=operation_name,
                    request_id=request_id,
                    duration=duration,
                    error=str(e)
                )
                raise
                
        if asyncio_iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


import asyncio


def asyncio_iscoroutinefunction(func):
    """检查是否是异步函数"""
    return asyncio.iscoroutinefunction(func)