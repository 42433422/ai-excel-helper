"""进程启动前准备：默认管理员账号（SQLite ORM，避免 NOW() 方言问题）。"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from sqlalchemy import select

logger = logging.getLogger(__name__)


def ensure_sandbox_admin() -> None:
    username = (os.environ.get("SANDBOX_ADMIN_USERNAME") or "sandbox").strip()
    password = (os.environ.get("SANDBOX_ADMIN_PASSWORD") or "sandbox").strip()
    display_name = (os.environ.get("SANDBOX_ADMIN_DISPLAY_NAME") or "沙盒管理员").strip()

    from app.db import SessionLocal
    from app.db.models.user import User
    from app.utils.password_hash import generate_password_hash

    db = SessionLocal()
    try:
        existing = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if existing:
            logger.info("sandbox admin exists: %s", username)
            return
        user = User(
            username=username,
            password=generate_password_hash(password),
            display_name=display_name,
            email="",
            role="admin",
            is_active=True,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(user)
        db.commit()
        logger.info("sandbox admin created: %s", username)
    except Exception:
        logger.exception("ensure_sandbox_admin failed")
        db.rollback()
    finally:
        db.close()
