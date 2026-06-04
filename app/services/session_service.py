"""基于数据库的用户会话：创建、校验、清理过期记录。"""

import uuid
from datetime import timedelta

from app.db.models.user import Session as UserSession
from app.db.session import get_db
from app.neuro_bus.event_publisher_mixin import NeuroEventPublisherMixin
from app.utils.time import utc_now_naive


class SessionService(NeuroEventPublisherMixin):
    SESSION_EXPIRE_HOURS = 24

    def __init__(self):
        pass

    def create_session(self, user_id: int):
        with get_db() as db:
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
            db.commit()

            return {
                "success": True,
                "session_id": session_id,
                "expires_at": expires_at.isoformat(),
                "user_id": user_id,
            }

    def validate_session(self, session_id: str):
        from app.infrastructure.session.session_manager import get_session_manager

        return get_session_manager().validate_session(session_id)

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


def get_session_service() -> "SessionService":
    from app.di.registry import get_service_registry

    return get_service_registry().session_service


# NEURO-DDD: 为 Services 层类添加 instrumentation
from app.neuro_bus.neuro_service_instrumentation import instrument_service_layer_class

instrument_service_layer_class(SessionService, "app.services.session_service")
