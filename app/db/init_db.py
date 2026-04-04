"""
XCAGI 数据库路径与初始化入口（应用内）。

目标：
- 让 app/* 不再依赖仓库根目录 db.py
- 兼容 PyInstaller（_MEIPASS）与开发环境
- 支持从 resources/db_seed 复制初始 sqlite
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import sys
from typing import TYPE_CHECKING, Iterable

from app.utils.external_sqlite import sqlite_conn

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
from app.utils.path_utils import get_app_data_dir, get_base_dir, get_resource_path

logger = logging.getLogger(__name__)


DEFAULT_DB_FILES: tuple[str, ...] = (
    "products.db",
    "inventory.db",
    "voice_learning.db",
    "error_collection.db",
)


def _iter_seed_dirs() -> Iterable[str]:
    """
    返回可能的种子 db 来源目录（按优先级）。
    - resources/db_seed（推荐）
    - base_dir（兼容旧行为）
    - _MEIPASS（打包时解包目录）
    """
    yield get_resource_path("db_seed")
    yield get_base_dir()
    if hasattr(sys, "_MEIPASS"):
        yield sys._MEIPASS  # type: ignore[attr-defined]


def initialize_databases(db_files: Iterable[str] = DEFAULT_DB_FILES) -> None:
    """
    初始化数据库文件（主要用于首次运行/打包环境）。
    规则：如果目标目录已存在同名 db，则不覆盖。
    """
    work_dir = get_app_data_dir()
    os.makedirs(work_dir, exist_ok=True)

    for db_file in db_files:
        target_path = os.path.join(work_dir, db_file)
        if os.path.exists(target_path):
            continue

        source_path = None
        for seed_dir in _iter_seed_dirs():
            cand = os.path.join(seed_dir, db_file)
            if os.path.exists(cand):
                source_path = cand
                break

        if not source_path:
            logger.warning("未找到种子数据库文件：%s（将由 ORM/运行时创建）", db_file)
            continue

        try:
            shutil.copy2(source_path, target_path)
            # 轻量检查
            with sqlite_conn(target_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                _ = cur.fetchall()
        except Exception as e:
            logger.warning("复制数据库失败 %s -> %s: %s", source_path, target_path, e)


def get_db_path(db_name: str = "products.db") -> str:
    """获取主数据库（或指定 db）路径。"""
    return os.path.join(get_app_data_dir(), db_name)


def get_customers_db_path() -> str:
    return get_db_path("customers.db")


def get_distillation_db_path() -> str:
    return get_db_path("distillation.db")


def init_wechat_tasks_table(db_path: str | None = None) -> None:
    """初始化 wechat_tasks 表（存放从微信解析出来的任务）"""
    db_path = db_path or get_db_path("products.db")
    with sqlite_conn(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wechat_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER,
                username TEXT,
                display_name TEXT,
                message_id TEXT,
                msg_timestamp INTEGER,
                raw_text TEXT NOT NULL,
                task_type TEXT NOT NULL DEFAULT 'unknown',
                status TEXT NOT NULL DEFAULT 'pending',
                last_status_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_wechat_tasks_contact_status
            ON wechat_tasks (contact_id, status)
            """
        )

        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_wechat_tasks_msg_unique
            ON wechat_tasks (message_id, username)
            """
        )

        conn.commit()


def init_distillation_tables(engine: "Engine") -> None:
    """
    在主库上创建蒸馏样本表 distillation_log / training_stats。
    与 SessionLocal 使用同一引擎，避免切换 SQLite/PostgreSQL 后路由与采集脚本连库不一致。
    """
    from sqlalchemy import text

    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "sqlite":
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS distillation_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query TEXT NOT NULL,
                        intent TEXT NOT NULL,
                        slots TEXT,
                        confidence REAL DEFAULT 1.0,
                        source TEXT DEFAULT 'manual',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        used_for_training INTEGER DEFAULT 0
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS training_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        intent TEXT NOT NULL,
                        count INTEGER DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
        else:
            # PostgreSQL 等与 Alembic b1f4a6d2e8c1 一致
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS distillation_log (
                        id BIGSERIAL PRIMARY KEY,
                        query TEXT NOT NULL,
                        intent TEXT NOT NULL,
                        slots TEXT,
                        confidence DOUBLE PRECISION DEFAULT 1.0,
                        source TEXT DEFAULT 'manual',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        used_for_training INTEGER DEFAULT 0
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS training_stats (
                        id BIGSERIAL PRIMARY KEY,
                        intent TEXT NOT NULL,
                        count INTEGER DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_intent ON distillation_log(intent)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_used ON distillation_log(used_for_training)"))


def init_template_tables(db_path: str | None = None) -> None:
    """
    初始化模板相关表：
    - templates
    - template_usage_log

    兼容策略：
    - 表不存在时创建
    - 表已存在但缺少新字段时自动补齐
    """
    db_path = db_path or get_db_path("products.db")
    with sqlite_conn(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_key TEXT,
                template_name TEXT NOT NULL,
                template_type TEXT,
                original_file_path TEXT,
                analyzed_data TEXT,
                editable_config TEXT,
                zone_config TEXT,
                merged_cells_config TEXT,
                style_config TEXT,
                business_rules TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS template_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_templates_type_active
            ON templates (template_type, is_active)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_template_usage_log_template_id
            ON template_usage_log (template_id)
            """
        )

        # 旧库兼容：若历史 versions 缺少字段，则补齐
        cur.execute("PRAGMA table_info(templates)")
        templates_columns = {str(row[1]).strip() for row in (cur.fetchall() or [])}
        required_templates_columns = {
            "template_key": "ALTER TABLE templates ADD COLUMN template_key TEXT",
            "template_name": "ALTER TABLE templates ADD COLUMN template_name TEXT",
            "template_type": "ALTER TABLE templates ADD COLUMN template_type TEXT",
            "original_file_path": "ALTER TABLE templates ADD COLUMN original_file_path TEXT",
            "analyzed_data": "ALTER TABLE templates ADD COLUMN analyzed_data TEXT",
            "editable_config": "ALTER TABLE templates ADD COLUMN editable_config TEXT",
            "zone_config": "ALTER TABLE templates ADD COLUMN zone_config TEXT",
            "merged_cells_config": "ALTER TABLE templates ADD COLUMN merged_cells_config TEXT",
            "style_config": "ALTER TABLE templates ADD COLUMN style_config TEXT",
            "business_rules": "ALTER TABLE templates ADD COLUMN business_rules TEXT",
            "is_active": "ALTER TABLE templates ADD COLUMN is_active INTEGER DEFAULT 1",
            "created_at": "ALTER TABLE templates ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "ALTER TABLE templates ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        }
        for column_name, sql in required_templates_columns.items():
            if column_name not in templates_columns:
                cur.execute(sql)

        cur.execute("PRAGMA table_info(template_usage_log)")
        usage_columns = {str(row[1]).strip() for row in (cur.fetchall() or [])}
        required_usage_columns = {
            "template_id": "ALTER TABLE template_usage_log ADD COLUMN template_id INTEGER",
            "action": "ALTER TABLE template_usage_log ADD COLUMN action TEXT",
            "result": "ALTER TABLE template_usage_log ADD COLUMN result TEXT",
            "created_at": "ALTER TABLE template_usage_log ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        }
        for column_name, sql in required_usage_columns.items():
            if column_name not in usage_columns:
                cur.execute(sql)

        conn.commit()

