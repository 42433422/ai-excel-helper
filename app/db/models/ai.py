from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

logger = logging.getLogger(__name__)


class AIToolCategory(Base):
    __tablename__ = "ai_tool_categories"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_name: Mapped[str] = mapped_column(String, nullable=False)
    category_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String)
    icon: Mapped[Optional[str]] = mapped_column(String)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    tools: Mapped[list[AITool]] = relationship("AITool", back_populates="category")


class AITool(Base):
    __tablename__ = "ai_tools"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tool_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ai_tool_categories.id", ondelete="SET NULL")
    )
    description: Mapped[Optional[str]] = mapped_column(String)
    parameters: Mapped[Optional[str]] = mapped_column(String)
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    category: Mapped[Optional[AIToolCategory]] = relationship(
        "AIToolCategory", back_populates="tools"
    )


class AIConversation(Base):
    __tablename__ = "ai_conversations"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("ai_conversation_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[Optional[str]] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    intent: Mapped[Optional[str]] = mapped_column(String)
    conversation_metadata: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    session: Mapped[AIConversationSession] = relationship(
        "AIConversationSession", back_populates="conversations"
    )


class AIConversationSession(Base):
    __tablename__ = "ai_conversation_sessions"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )
    title: Mapped[Optional[str]] = mapped_column(String)
    summary: Mapped[Optional[str]] = mapped_column(String)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    user: Mapped[Optional[User]] = relationship("User", back_populates="ai_conversation_sessions")
    conversations: Mapped[list[AIConversation]] = relationship(
        "AIConversation", back_populates="session", cascade="all, delete-orphan"
    )


class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    preference_key: Mapped[str] = mapped_column(String, nullable=False)
    preference_value: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class UserMemory(Base):
    __tablename__ = "user_memories"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    preferences: Mapped[Optional[str]] = mapped_column(Text)
    frequent_actions: Mapped[Optional[str]] = mapped_column(Text)
    historical_contexts: Mapped[Optional[str]] = mapped_column(Text)
    feedback_history: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    ttl_days: Mapped[int] = mapped_column(Integer, default=90)
    max_preferences: Mapped[int] = mapped_column(Integer, default=50)
    max_actions: Mapped[int] = mapped_column(Integer, default=30)
    max_contexts: Mapped[int] = mapped_column(Integer, default=100)
    max_feedback: Mapped[int] = mapped_column(Integer, default=50)

    @property
    def preferences_dict(self) -> dict[str, Any]:
        if self.preferences:
            return json.loads(self.preferences)
        return {}

    @property
    def frequent_actions_list(self) -> list[dict[str, Any]]:
        if self.frequent_actions:
            return json.loads(self.frequent_actions)
        return []

    @property
    def historical_contexts_list(self) -> list[dict[str, Any]]:
        if self.historical_contexts:
            return json.loads(self.historical_contexts)
        return []

    @property
    def feedback_history_list(self) -> list[dict[str, Any]]:
        if self.feedback_history:
            return json.loads(self.feedback_history)
        return []

    def update_from_dict(self, data: dict[str, Any]) -> None:
        if "preferences" in data:
            prefs = data["preferences"]
            if isinstance(prefs, dict) and len(prefs) > (self.max_preferences or 50):
                prefs = dict(list(prefs.items())[: self.max_preferences or 50])
            self.preferences = json.dumps(prefs, ensure_ascii=False)

        if "frequent_actions" in data:
            actions = data["frequent_actions"]
            if isinstance(actions, list):
                actions = sorted(
                    actions,
                    key=lambda x: x.get("count", 0) if isinstance(x, dict) else 0,
                    reverse=True,
                )
                actions = actions[: self.max_actions or 30]
            self.frequent_actions = json.dumps(actions, ensure_ascii=False)

        if "historical_contexts" in data:
            contexts = data["historical_contexts"]
            if isinstance(contexts, list):
                contexts = contexts[: self.max_contexts or 100]
            self.historical_contexts = json.dumps(contexts, ensure_ascii=False)

        if "feedback_history" in data:
            feedback = data["feedback_history"]
            if isinstance(feedback, list):
                feedback = feedback[: self.max_feedback or 50]
            self.feedback_history = json.dumps(feedback, ensure_ascii=False)

        self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "preferences": self.preferences_dict,
            "frequent_actions": self.frequent_actions_list,
            "historical_contexts": self.historical_contexts_list,
            "feedback_history": self.feedback_history_list,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "ttl_days": self.ttl_days,
        }

    @classmethod
    def cleanup_old_records(cls, db_session, days: int = 90) -> int:
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)

        result = db_session.query(cls).filter(cls.updated_at < cutoff).delete()

        db_session.commit()
        logger.info(f"Cleaned up {result} old UserMemory records older than {days} days")
        return result


from app.db.models.user import User  # noqa: E402
