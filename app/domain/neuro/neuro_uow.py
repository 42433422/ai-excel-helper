"""NeuroUnitOfWork：单库 SQLAlchemy 会话边界，commit/rollback 与可选总线回调。"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class NeuroUnitOfWork:
    """
    用法::

        with NeuroUnitOfWork() as session:
            session.add(...)
        # 无异常则 commit，有异常则 rollback
    """

    def __init__(
        self,
        session_factory: Callable[[], Any] | None = None,
        on_commit: Callable[[], None] | None = None,
    ):
        self._session_factory = session_factory
        self._on_commit = on_commit
        self._session: Any = None

    def __enter__(self) -> Any:
        if self._session_factory is not None:
            self._session = self._session_factory()
        else:
            from app.db import SessionLocal

            self._session = SessionLocal()
        return self._session

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._session is None:
            return
        try:
            if exc_type is None:
                self._session.commit()
                if self._on_commit is not None:
                    try:
                        self._on_commit()
                    except Exception:
                        logger.exception("NeuroUnitOfWork on_commit hook failed")
            else:
                self._session.rollback()
        finally:
            self._session.close()
            self._session = None


@contextmanager
def neuro_uow_session(
    *,
    session_factory: Callable[[], Any] | None = None,
    on_commit: Callable[[], None] | None = None,
) -> Iterator[Any]:
    """与 ``NeuroUnitOfWork`` 等价的 ``contextmanager`` 写法。"""
    uow = NeuroUnitOfWork(session_factory=session_factory, on_commit=on_commit)
    with uow as session:
        yield session
