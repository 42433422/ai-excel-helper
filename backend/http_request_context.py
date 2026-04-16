"""HTTP 请求作用域的 request_id（ContextVar），供 Planner/工具链日志与后续链路追踪复用。"""

from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from typing import Callable

_http_request_id: ContextVar[str | None] = ContextVar("http_request_id", default=None)

_log_record_factory_installed = False
_prev_log_record_factory: Callable[..., logging.LogRecord] | None = None


def get_http_request_id() -> str | None:
    return _http_request_id.get()


def set_http_request_id(value: str) -> Token:
    return _http_request_id.set(value)


def reset_http_request_id(token: Token) -> None:
    _http_request_id.reset(token)


def install_log_record_request_id() -> None:
    """
    为每条 LogRecord 注入 request_id 属性（无 HTTP 上下文时为 "-"），便于 Formatter 使用 %(request_id)s。
    幂等：多次调用不会重复包装 factory。
    """
    global _log_record_factory_installed, _prev_log_record_factory
    if _log_record_factory_installed:
        return
    _log_record_factory_installed = True
    _prev_log_record_factory = logging.getLogRecordFactory()

    def _factory(*args: object, **kwargs: object) -> logging.LogRecord:
        assert _prev_log_record_factory is not None
        record = _prev_log_record_factory(*args, **kwargs)
        rid = _http_request_id.get()
        record.__dict__["request_id"] = rid if rid else "-"
        return record

    logging.setLogRecordFactory(_factory)
