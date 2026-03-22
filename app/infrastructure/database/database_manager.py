"""
数据库管理基础设施

负责数据库连接和会话管理
"""

from contextlib import contextmanager
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


class DatabaseManager:
    """
    数据库管理器

    负责：
    - 数据库连接管理
    - 会话创建和销毁
    - 连接池管理
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        pool_size: int = 5,
        max_overflow: int = 10
    ):
        self._database_url = database_url or "sqlite:///xcagi.db"
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._engine = None
        self._session_factory = None
        self._init_engine()

    def _init_engine(self):
        """初始化数据库引擎"""
        if "sqlite" in self._database_url:
            self._engine = create_engine(
                self._database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False
            )
        else:
            self._engine = create_engine(
                self._database_url,
                pool_size=self._pool_size,
                max_overflow=self._max_overflow,
                echo=False
            )

        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False
        )

    @contextmanager
    def get_session(self) -> Session:
        """
        获取数据库会话上下文管理器

        Yields:
            数据库会话

        Example:
            with db_manager.get_session() as session:
                session.query(User).all()
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session_factory(self):
        """获取会话工厂"""
        return self._session_factory

    def get_engine(self):
        """获取数据库引擎"""
        return self._engine

    def dispose(self):
        """释放数据库连接池"""
        if self._engine:
            self._engine.dispose()


_database_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """获取数据库管理器单例"""
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
    return _database_manager


def init_database_manager(database_url: str) -> DatabaseManager:
    """初始化数据库管理器"""
    global _database_manager
    _database_manager = DatabaseManager(database_url)
    return _database_manager
