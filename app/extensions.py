"""
FastAPI 扩展管理

应用扩展统一初始化入口。

``celery_app``：优先使用真实 Celery（默认 ``memory://`` broker，便于本地/单测）；
未安装 ``celery`` 时回退到最小桩。
"""

from __future__ import annotations

import functools
import logging
import os
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def _build_celery_stub() -> Any:
    class _RetryableSelf:
        class MaxRetriesExceededError(Exception):
            pass

        def retry(self, exc: BaseException | None = None, countdown: int = 0) -> None:
            raise self.MaxRetriesExceededError()

    class _CeleryStub:
        def task(
            self,
            *_args: Any,
            bind: bool = False,
            max_retries: int = 0,
            **kwargs: Any,
        ) -> Callable[[F], F]:
            def decorator(fn: F) -> F:
                @functools.wraps(fn)
                def wrapper(*a: Any, **kw: Any) -> Any:
                    if bind:
                        return fn(_RetryableSelf(), *a, **kw)
                    return fn(*a, **kw)

                wrapper.delay = lambda *a2, **k2: wrapper(*a2, **k2)  # type: ignore[attr-defined]
                wrapper.apply_async = lambda *a2, **k2: wrapper(*a2, **k2)  # type: ignore[attr-defined]
                return wrapper  # type: ignore[return-value]

            return decorator

    return _CeleryStub()


try:
    from celery import Celery

    _broker = (os.environ.get("CELERY_BROKER_URL") or "memory://").strip()
    _backend = (os.environ.get("CELERY_RESULT_BACKEND") or "cache+memory://").strip()
    celery_app = Celery("xcagi", broker=_broker, backend=_backend)
except ImportError:  # pragma: no cover
    logger.warning("celery 未安装，使用内存任务桩")
    celery_app = _build_celery_stub()
