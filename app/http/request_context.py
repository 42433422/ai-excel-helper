"""当前 HTTP 请求的 Starlette/FastAPI ``Request``（ContextVar），供同步装饰器读取。"""

from __future__ import annotations

from contextvars import ContextVar, Token

from starlette.requests import Request

_http_request_ctx: ContextVar[Request | None] = ContextVar("http_request", default=None)


def set_current_http_request(request: Request | None) -> Token[Request | None]:
    return _http_request_ctx.set(request)


def reset_current_http_request(token: Token[Request | None]) -> None:
    _http_request_ctx.reset(token)


def get_current_http_request() -> Request | None:
    return _http_request_ctx.get()
