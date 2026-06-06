"""
为 Services 层类（如 HybridIntentService）包装公开方法，发出 service.module.trace。

与 Application 层采样使用同一套 ``should_sample_app_service``，但使用独立 depth 计数，避免与 Application 嵌套冲突。
"""

from __future__ import annotations

import inspect
import threading
import time
from collections.abc import Callable
from typing import Any

from app.neuro_bus.application_neuro_bridge import neuro_trace_service_call

_tls = threading.local()


def _svc_enter() -> bool:
    d = getattr(_tls, "svc_depth", 0) + 1
    _tls.svc_depth = d
    if d == 1:
        try:
            from app.neuro_bus.neuro_trace_config import should_sample_app_service

            _tls.svc_emit = should_sample_app_service()
        except Exception:
            _tls.svc_emit = True
    return bool(getattr(_tls, "svc_emit", False))


def _svc_exit() -> None:
    _tls.svc_depth = max(getattr(_tls, "svc_depth", 1) - 1, 0)
    if _tls.svc_depth == 0:
        _tls.svc_emit = False


def _wrap_fn(module_label: str, method_name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    if inspect.iscoroutinefunction(fn):

        async def awrapped(*args: Any, **kwargs: Any) -> Any:
            emit = _svc_enter()
            t0 = time.perf_counter()
            if emit:
                neuro_trace_service_call(module_label, method_name, "start")
            try:
                out = await fn(*args, **kwargs)
            except Exception as exc:
                if emit:
                    neuro_trace_service_call(
                        module_label,
                        method_name,
                        "error",
                        duration_ms=(time.perf_counter() - t0) * 1000.0,
                        error=str(exc),
                    )
                raise
            else:
                if emit:
                    neuro_trace_service_call(
                        module_label,
                        method_name,
                        "end",
                        duration_ms=(time.perf_counter() - t0) * 1000.0,
                    )
                return out
            finally:
                _svc_exit()

        return awrapped

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        emit = _svc_enter()
        t0 = time.perf_counter()
        if emit:
            neuro_trace_service_call(module_label, method_name, "start")
        try:
            out = fn(*args, **kwargs)
        except Exception as exc:
            if emit:
                neuro_trace_service_call(
                    module_label,
                    method_name,
                    "error",
                    duration_ms=(time.perf_counter() - t0) * 1000.0,
                    error=str(exc),
                )
            raise
        else:
            if emit:
                neuro_trace_service_call(
                    module_label,
                    method_name,
                    "end",
                    duration_ms=(time.perf_counter() - t0) * 1000.0,
                )
            return out
        finally:
            _svc_exit()

    return wrapped


_SKIP = frozenset({"__init__", "__new__", "__del__", "__repr__", "__str__"})


def instrument_service_layer_class(cls: type[Any], module_label: str) -> type[Any]:
    for name, member in list(cls.__dict__.items()):
        if name.startswith("_") or name in _SKIP:
            continue
        if isinstance(member, (classmethod, staticmethod, property)):
            continue
        if not callable(member):
            continue
        setattr(cls, name, _wrap_fn(module_label, name, member))
    return cls
