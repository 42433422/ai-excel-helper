from app.db.models import User
from app.db.models.user import Session as UserSession
from app.db.session import get_db


class SessionService:
    SESSION_EXPIRE_HOURS = 24

    def __init__(self):
        pass

    def create_session(self, user_id: int):
        with get_db() as db:
            import uuid
            from datetime import datetime, timedelta

            session_id = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(hours=self.SESSION_EXPIRE_HOURS)

            user_session = UserSession(
                session_id=session_id,
                user_id=user_id,
                created_at=datetime.utcnow(),
                expires_at=expires_at
            )
            db.add(user_session)
            db.commit()

            return {
                "success": True,
                "session_id": session_id,
                "expires_at": expires_at.isoformat(),
                "user_id": user_id
            }

    def validate_session(self, session_id: str):
        with get_db() as db:
            from datetime import datetime

            user_session = db.query(UserSession).filter(
                UserSession.session_id == session_id
            ).first()

            if not user_session:
                return None

            if user_session.expires_at < datetime.utcnow():
                db.delete(user_session)
                db.commit()
                return None

            return user_session.user

    def get_session_info(self, session_id: str):
        with get_db() as db:
            from datetime import datetime

            user_session = db.query(UserSession).filter(
                UserSession.session_id == session_id
            ).first()

            if not user_session:
                return None

            if user_session.expires_at < datetime.utcnow():
                return None

            return {
                "session_id": user_session.session_id,
                "user_id": user_session.user_id,
                "username": user_session.user.username,
                "created_at": user_session.created_at.isoformat(),
                "expires_at": user_session.expires_at.isoformat()
            }

    def delete_session(self, session_id: str) -> bool:
        with get_db() as db:
            user_session = db.query(UserSession).filter(
                UserSession.session_id == session_id
            ).first()

            if not user_session:
                return False

            db.delete(user_session)
            db.commit()
            return True

    def delete_user_sessions(self, user_id: int) -> int:
        with get_db() as db:
            count = db.query(UserSession).filter(
                UserSession.user_id == user_id
            ).delete()
            db.commit()
            return count

    def cleanup_expired_sessions(self) -> int:
        with get_db() as db:
            from datetime import datetime

            count = db.query(UserSession).filter(
                UserSession.expires_at < datetime.utcnow()
            ).delete()
            db.commit()
            return count


_session_service = None


def get_session_service() -> "SessionService":
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service
