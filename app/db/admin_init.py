"""
管理员初始化（显式调用）。

为避免“import 即创建默认管理员”的副作用，本模块只提供函数，不在导入时做任何写入。
"""

from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
from typing import Optional

from app.utils.path_utils import get_app_data_dir

logger = logging.getLogger(__name__)


def get_user_db_path() -> str:
    return os.path.join(get_app_data_dir(), "users.db")


def init_user_db() -> str:
    db_path = get_user_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            display_name TEXT DEFAULT '',
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    conn.commit()
    conn.close()
    return db_path


def create_admin_user(
    *,
    username: str,
    password: str,
    display_name: str = "管理员",
    role: str = "admin",
) -> dict:
    db_path = init_user_db()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return {"success": True, "message": "管理员已存在"}

    hashed_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
    cursor.execute(
        """
        INSERT INTO users (username, password, display_name, role)
        VALUES (?, ?, ?, ?)
        """,
        (username, hashed_password, display_name, role),
    )
    conn.commit()
    conn.close()
    logger.info("管理员账户已创建 (%s)", username)
    return {"success": True, "message": "管理员已创建"}


def create_admin_from_env() -> dict:
    """
    从环境变量创建管理员（显式调用时使用）。
    需要：
    - ADMIN_USERNAME
    - ADMIN_PASSWORD
    """
    username = (os.environ.get("ADMIN_USERNAME") or "").strip()
    password = (os.environ.get("ADMIN_PASSWORD") or "").strip()
    display_name = (os.environ.get("ADMIN_DISPLAY_NAME") or "管理员").strip()
    if not username or not password:
        return {"success": False, "message": "缺少 ADMIN_USERNAME/ADMIN_PASSWORD"}
    return create_admin_user(username=username, password=password, display_name=display_name)

