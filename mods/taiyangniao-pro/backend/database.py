"""
太阳鸟pro - 数据库连接和会话管理（Mod 私有 SQLite，与主库拆分并存）。
"""

from __future__ import annotations

import threading
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.mod_sdk.private_sqlite import resolve_mod_private_sqlite_path

try:
    from .models import Base
except ImportError:
    try:
        from models import Base
    except ImportError:
        Base = None  # type: ignore[misc,assignment]

DEFAULT_DB_NAME = "taiyangniao_pro.db"

_engine_lock = threading.Lock()
_engine = None
_session_factory: sessionmaker | None = None


def get_database_path():
    """Mod 业务库路径：与主应用 ``data`` / 桌面 ``DATABASE_PATH`` 对齐的 ``mod_dbs``。"""
    return resolve_mod_private_sqlite_path(DEFAULT_DB_NAME)


def get_engine():
    """进程内单例 Engine（SQLite NullPool + 超时，与主栈策略一致）。"""
    global _engine
    with _engine_lock:
        if _engine is None:
            db_path = get_database_path()
            _engine = create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False, "timeout": 45},
                poolclass=NullPool,
                echo=False,
            )
        return _engine


def init_database():
    """初始化数据库，创建所有表"""
    if Base is None:
        raise RuntimeError(
            "taiyangniao-pro: 缺少 backend/models.py（或无法导入 Base），无法 init_database。"
        )
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    return engine


def _sessionmaker() -> sessionmaker:
    global _session_factory
    with _engine_lock:
        if _session_factory is None:
            _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
        return _session_factory


def get_session() -> Generator[Session, None, None]:
    """获取数据库会话的生成器，用于依赖注入"""
    session = _sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def get_session_context() -> Session:
    """获取数据库会话（调用方负责 close）。"""
    return _sessionmaker()()
