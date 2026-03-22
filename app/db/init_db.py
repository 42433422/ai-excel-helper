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
from typing import Iterable

from app.utils.path_utils import get_app_data_dir, get_base_dir, get_resource_path

logger = logging.getLogger(__name__)


DEFAULT_DB_FILES: tuple[str, ...] = (
    "products.db",
    "customers.db",
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
            cur = sqlite3.connect(target_path).cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            _ = cur.fetchall()
            cur.connection.close()
        except Exception as e:
            logger.warning("复制数据库失败 %s -> %s: %s", source_path, target_path, e)


def get_db_path(db_name: str = "products.db") -> str:
    """获取主数据库（或指定 db）路径。"""
    return os.path.join(get_app_data_dir(), db_name)


def get_customers_db_path() -> str:
    return get_db_path("customers.db")


def get_distillation_db_path() -> str:
    return get_db_path("distillation.db")


def init_wechat_tasks_table() -> None:
    """初始化 wechat_tasks 表（存放从微信解析出来的任务）"""
    db_path = get_db_path("products.db")
    conn = sqlite3.connect(db_path)
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
    conn.close()

