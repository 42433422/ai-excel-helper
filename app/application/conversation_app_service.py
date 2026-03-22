"""
对话应用服务

此模块已迁移到 app/application/
"""

import logging
import uuid
from datetime import datetime
from typing import Any, List, Optional, Tuple

from app.db.models import AIConversation, AIConversationSession
from app.db.session import get_db

logger = logging.getLogger(__name__)


class ConversationApplicationService:
    """对话应用服务"""

    def __init__(self):
        pass

    def save_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        intent: str = "",
        metadata: str = ""
    ) -> int:
        with get_db() as db:
            message = AIConversation(
                session_id=session_id,
                user_id=user_id,
                role=role,
                content=content,
                intent=intent,
                metadata=metadata
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            return message.id

    def get_session_messages(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Tuple]:
        with get_db() as db:
            messages = db.query(AIConversation).filter(
                AIConversation.session_id == session_id
            ).order_by(
                AIConversation.created_at.desc()
            ).limit(limit).all()

            result = []
            for msg in messages:
                result.append((
                    msg.id,
                    msg.role,
                    msg.content,
                    msg.intent,
                    msg.metadata,
                    msg.created_at.isoformat() if msg.created_at else None
                ))

            return list(reversed(result))

    def create_session(self, user_id: str = "default") -> str:
        with get_db() as db:
            session = AIConversationSession(
                user_id=user_id,
                context={}
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            return session.session_id

    def get_or_create_session(self, user_id: str = "default") -> str:
        with get_db() as db:
            session = db.query(AIConversationSession).filter(
                AIConversationSession.user_id == user_id
            ).order_by(
                AIConversationSession.created_at.desc()
            ).first()

            if session:
                return session.session_id

            new_session = AIConversationSession(
                user_id=user_id,
                context={}
            )
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            return new_session.session_id

    def get_sessions(self, user_id: str = "default", limit: int = 10) -> List[dict]:
        with get_db() as db:
            sessions = db.query(AIConversationSession).filter(
                AIConversationSession.user_id == user_id
            ).order_by(
                AIConversationSession.created_at.desc()
            ).limit(limit).all()

            return [
                {
                    "session_id": s.session_id,
                    "user_id": s.user_id,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None
                }
                for s in sessions
            ]

    def delete_session(self, session_id: str) -> bool:
        with get_db() as db:
            session = db.query(AIConversationSession).filter(
                AIConversationSession.session_id == session_id
            ).first()

            if not session:
                return False

            db.query(AIConversation).filter(
                AIConversation.session_id == session_id
            ).delete()

            db.delete(session)
            db.commit()
            return True


_conversation_app_service: Optional[ConversationApplicationService] = None


def get_conversation_app_service() -> ConversationApplicationService:
    global _conversation_app_service
    if _conversation_app_service is None:
        _conversation_app_service = ConversationApplicationService()
    return _conversation_app_service
