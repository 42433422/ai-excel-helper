"""
管理员初始化（显式调用）。

为避免“import 即创建默认管理员”的副作用，本模块只提供函数，不在导入时做任何写入。
"""

from __future__ import annotations

import hashlib
import logging
import os

from sqlalchemy import text

from app.db import SessionLocal

logger = logging.getLogger(__name__)


def init_user_db() -> bool:
    """用户表由 Alembic 管理，保留兼容入口。"""
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
        db.commit()
    return True


def create_admin_user(
    *,
    username: str,
    password: str,
    display_name: str = "管理员",
    role: str = "admin",
) -> dict:
    init_user_db()
    with SessionLocal() as db:
        row = db.execute(
            text("SELECT id FROM users WHERE username = :username LIMIT 1"),
            {"username": username},
        ).fetchone()
        if row:
            return {"success": True, "message": "管理员已存在"}

        hashed_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
        db.execute(
            text(
                """
                INSERT INTO users (username, password, display_name, role, is_active, created_at)
                VALUES (:username, :password, :display_name, :role, 1, NOW())
                """
            ),
            {
                "username": username,
                "password": hashed_password,
                "display_name": display_name,
                "role": role,
            },
        )
        db.commit()
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

