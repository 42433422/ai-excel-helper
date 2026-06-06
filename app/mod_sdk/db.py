"""SQLAlchemy 会话工厂（SDK re-export）。

``SessionLocal()`` 返回一个可作上下文使用的 ORM Session；
Mod 代码应在 ``try/finally`` 中显式 ``close()``，或用 ``contextlib.closing``。
"""

from __future__ import annotations

from app.db import SessionLocal  # noqa: F401

__all__ = ["SessionLocal"]
