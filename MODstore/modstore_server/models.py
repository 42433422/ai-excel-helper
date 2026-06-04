"""MODstore 在线市场数据库模型（SQLite + SQLAlchemy）。"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=True)
    password_hash = Column(String(256), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utc_now_naive)


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    balance = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=_utc_now_naive)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    txn_type = Column(String(32), nullable=False)
    status = Column(String(16), default="completed")
    description = Column(Text, default="")
    created_at = Column(DateTime, default=_utc_now_naive)


class CatalogItem(Base):
    __tablename__ = "catalog_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pkg_id = Column(String(128), unique=True, nullable=False, index=True)
    version = Column(String(32), nullable=False)
    name = Column(String(256), nullable=False)
    description = Column(Text, default="")
    price = Column(Float, default=0.0)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    artifact = Column(String(32), default="mod")
    stored_filename = Column(String(256), default="")
    sha256 = Column(String(64), default="")
    is_public = Column(Boolean, default=True)
    compliance_status = Column(String(32), default="approved")
    created_at = Column(DateTime, default=_utc_now_naive)


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    catalog_id = Column(Integer, ForeignKey("catalog_items.id"), nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=_utc_now_naive)


class Workflow(Base):
    """Minimal workflow row for ``employee_config_v2`` validation in tests."""

    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)


def default_db_path() -> Path:
    raw = (os.environ.get("MODSTORE_DB_PATH") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parent / "modstore.db"


def _sqlite_url(db_file: Path) -> str:
    """Build a sqlite URL that tolerates non-ASCII paths on Windows."""
    posix = db_file.expanduser().resolve().as_posix()
    return f"sqlite:///{posix}"


def _migrate_sqlite_schema(engine) -> None:
    """Add columns introduced after early deployments (create_all does not alter tables)."""
    if engine.dialect.name != "sqlite":
        return
    insp = inspect(engine)
    if not insp.has_table("catalog_items"):
        return
    existing = {col["name"] for col in insp.get_columns("catalog_items")}
    alters = [
        ("artifact", "VARCHAR(32) DEFAULT 'mod'"),
        ("stored_filename", "VARCHAR(256) DEFAULT ''"),
        ("sha256", "VARCHAR(64) DEFAULT ''"),
        ("is_public", "BOOLEAN DEFAULT 1"),
        ("compliance_status", "VARCHAR(32) DEFAULT 'approved'"),
        ("created_at", "DATETIME"),
    ]
    with engine.begin() as conn:
        for name, ddl in alters:
            if name not in existing:
                conn.execute(text(f"ALTER TABLE catalog_items ADD COLUMN {name} {ddl}"))


_engine = None
_SessionFactory = None


def reset_session_factory() -> None:
    """Clear cached engine (tests set ``MODSTORE_DB_PATH`` per case)."""
    global _engine, _SessionFactory
    _engine = None
    _SessionFactory = None


def get_engine(db_path: Optional[Path] = None):
    global _engine
    if _engine is None:
        p = db_path or default_db_path()
        if p.exists() and p.is_dir():
            raise ValueError(f"MODSTORE_DB_PATH must be a file path, got directory: {p}")
        p.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(_sqlite_url(p), echo=False)
    return _engine


def get_session_factory(db_path: Optional[Path] = None):
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine(db_path)
        Base.metadata.create_all(engine)
        _migrate_sqlite_schema(engine)
        _SessionFactory = sessionmaker(bind=engine)
    return _SessionFactory


def init_db(db_path: Optional[Path] = None):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    _migrate_sqlite_schema(engine)
