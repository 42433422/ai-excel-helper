"""
会话管理基础设施

提供用户会话管理的数据库操作。
"""

import os
from datetime import timedelta

from sqlalchemy.orm import joinedload, make_transient

from app.db.models.user import Session as UserSession
from app.db.models.user import User
from app.db.session import get_db
from app.utils.time import utc_now_naive


class SessionManager:
    SESSION_EXPIRE_HOURS = int(os.environ.get("SESSION_EXPIRE_HOURS", "87600"))

    def __init__(self):
        pass

    def create_session_with_db(self, db, user_id: int) -> dict:
        """在调用方已有的事务内创建会话行（避免登录路径嵌套 ``get_db()`` 导致 SQLite 锁/冲突）。"""
        import uuid

        session_id = str(uuid.uuid4())
        now = utc_now_naive()
        expires_at = now + timedelta(hours=self.SESSION_EXPIRE_HOURS)

        user_session = UserSession(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            expires_at=expires_at,
        )
        db.add(user_session)

        return {
            "success": True,
            "session_id": session_id,
            "expires_at": expires_at.isoformat(),
            "user_id": user_id,
        }

    def create_session(self, user_id: int):
        with get_db() as db:
            return self.create_session_with_db(db, user_id)

    @staticmethod
    def _detach_user_for_response(user: User | None) -> User | None:
        """在 get_db() 退出后仍可读 user 标量字段，避免 DetachedInstanceError。"""
        if user is None:
            return None
        _ = (
            user.id,
            user.username,
            user.display_name,
            user.email,
            user.role,
            user.is_active,
        )
        make_transient(user)
        return user

    def validate_session(self, session_id: str):
        with get_db() as db:
            user_session = (
                db.query(UserSession)
                .options(joinedload(UserSession.user))
                .filter(UserSession.session_id == session_id)
                .first()
            )

            if not user_session:
                return None

            if user_session.expires_at < utc_now_naive():
                db.delete(user_session)
                db.commit()
                return None

            return self._detach_user_for_response(user_session.user)

    def get_session_info(self, session_id: str):
        with get_db() as db:
            user_session = (
                db.query(UserSession).filter(UserSession.session_id == session_id).first()
            )

            if not user_session:
                return None

            if user_session.expires_at < utc_now_naive():
                return None

            return {
                "session_id": user_session.session_id,
                "user_id": user_session.user_id,
                "username": user_session.user.username,
                "created_at": user_session.created_at.isoformat(),
                "expires_at": user_session.expires_at.isoformat(),
            }

    def delete_session(self, session_id: str) -> bool:
        with get_db() as db:
            user_session = (
                db.query(UserSession).filter(UserSession.session_id == session_id).first()
            )

            if not user_session:
                return False

            db.delete(user_session)
            db.commit()
            return True

    def delete_user_sessions(self, user_id: int) -> int:
        with get_db() as db:
            count = db.query(UserSession).filter(UserSession.user_id == user_id).delete()
            db.commit()
            return count

    def cleanup_expired_sessions(self) -> int:
        with get_db() as db:
            count = db.query(UserSession).filter(UserSession.expires_at < utc_now_naive()).delete()
            db.commit()
            return count


_session_manager = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
