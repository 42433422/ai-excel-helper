"""
运行时包装 Application 服务类的公开实例方法，发出 application.service.trace。

跳过 __init__ / __new__ / __del__；不包装 classmethod/staticmethod（由各类自行处理）。
"""

from __future__ import annotations

import inspect
import threading
import time
from collections.abc import Callable
from typing import Any

from app.neuro_bus.application_neuro_bridge import neuro_trace_app_service_call

_tls = threading.local()


def _app_enter() -> bool:
    d = getattr(_tls, "app_depth", 0) + 1
    _tls.app_depth = d
    if d == 1:
        try:
            from app.neuro_bus.neuro_trace_config import should_sample_app_service

            _tls.app_emit = should_sample_app_service()
        except Exception:
            _tls.app_emit = True
    return bool(getattr(_tls, "app_emit", False))


def _app_exit() -> None:
    _tls.app_depth = max(getattr(_tls, "app_depth", 1) - 1, 0)
    if _tls.app_depth == 0:
        _tls.app_emit = False


def _wrap_function(
    service_label: str, method_name: str, fn: Callable[..., Any]
) -> Callable[..., Any]:
    if inspect.iscoroutinefunction(fn):

        async def awrapped(*args: Any, **kwargs: Any) -> Any:
            emit = _app_enter()
            t0 = time.perf_counter()
            if emit:
                neuro_trace_app_service_call(service_label, method_name, "start")
            try:
                out = await fn(*args, **kwargs)
            except Exception as exc:
                if emit:
                    neuro_trace_app_service_call(
                        service_label,
                        method_name,
                        "error",
                        duration_ms=(time.perf_counter() - t0) * 1000.0,
                        error=str(exc),
                    )
                raise
            else:
                if emit:
                    neuro_trace_app_service_call(
                        service_label,
                        method_name,
                        "end",
                        duration_ms=(time.perf_counter() - t0) * 1000.0,
                    )
                return out
            finally:
                _app_exit()

        return awrapped

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        emit = _app_enter()
        t0 = time.perf_counter()
        if emit:
            neuro_trace_app_service_call(service_label, method_name, "start")
        try:
            out = fn(*args, **kwargs)
        except Exception as exc:
            if emit:
                neuro_trace_app_service_call(
                    service_label,
                    method_name,
                    "error",
                    duration_ms=(time.perf_counter() - t0) * 1000.0,
                    error=str(exc),
                )
            raise
        else:
            if emit:
                neuro_trace_app_service_call(
                    service_label,
                    method_name,
                    "end",
                    duration_ms=(time.perf_counter() - t0) * 1000.0,
                )
            return out
        finally:
            _app_exit()

    return wrapped


_SKIP_NAMES = frozenset({"__init__", "__new__", "__del__", "__repr__", "__str__"})


def instrument_application_service_class(
    cls: type[Any],
    service_name: str | None = None,
) -> type[Any]:
    label = service_name or cls.__name__
    for name, member in list(cls.__dict__.items()):
        if name.startswith("_") or name in _SKIP_NAMES:
            continue
        if isinstance(member, (classmethod, staticmethod, property)):
            continue
        if not callable(member):
            continue
        setattr(cls, name, _wrap_function(label, name, member))
    return cls


def instrument_approval_service_class(cls: type[Any]) -> type[Any]:
    """workflow.ApprovalService 等非 *ApplicationService 命名。"""
    return instrument_application_service_class(cls, service_name=cls.__name__)
