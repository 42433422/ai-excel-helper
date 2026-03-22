import json
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class AIToolCategory(Base):
    __tablename__ = "ai_tool_categories"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String, nullable=False)
    category_key = Column(String, unique=True, nullable=False)
    description = Column(String)
    icon = Column(String)
    sort_order = Column(Integer, default=0)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    
    # Relationship mappings
    tools = relationship("AITool", back_populates="category")


class AITool(Base):
    __tablename__ = "ai_tools"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    tool_key = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey('ai_tool_categories.id', ondelete='SET NULL'))
    description = Column(String)
    parameters = Column(String)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    
    # Relationship mappings
    category = relationship("AIToolCategory", back_populates="tools")


class AIConversation(Base):
    __tablename__ = "ai_conversations"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey('ai_conversation_sessions.session_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String)
    role = Column(String, nullable=False)
    content = Column(String, nullable=False)
    intent = Column(String)
    conversation_metadata = Column(String)
    created_at = Column(DateTime)
    
    # Relationship mappings
    session = relationship("AIConversationSession", back_populates="conversations")


class AIConversationSession(Base):
    __tablename__ = "ai_conversation_sessions"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, unique=True, nullable=False)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'))
    title = Column(String)
    summary = Column(String)
    message_count = Column(Integer, default=0)
    last_message_at = Column(DateTime)
    created_at = Column(DateTime)
    
    # Relationship mappings
    user = relationship("User", back_populates="ai_conversation_sessions")
    conversations = relationship("AIConversation", back_populates="session", cascade="all, delete-orphan")


class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    preference_key = Column(String, nullable=False)
    preference_value = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class UserMemory(Base):
    __tablename__ = "user_memories"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    preferences = Column(Text)
    frequent_actions = Column(Text)
    historical_contexts = Column(Text)
    feedback_history = Column(Text)
    updated_at = Column(DateTime)

    @property
    def preferences_dict(self) -> Dict[str, Any]:
        if self.preferences:
            return json.loads(self.preferences)
        return {}

    @property
    def frequent_actions_list(self) -> List[Dict[str, Any]]:
        if self.frequent_actions:
            return json.loads(self.frequent_actions)
        return []

    @property
    def historical_contexts_list(self) -> List[Dict[str, Any]]:
        if self.historical_contexts:
            return json.loads(self.historical_contexts)
        return []

    @property
    def feedback_history_list(self) -> List[Dict[str, Any]]:
        if self.feedback_history:
            return json.loads(self.feedback_history)
        return []

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        if "preferences" in data:
            self.preferences = json.dumps(data["preferences"], ensure_ascii=False)
        if "frequent_actions" in data:
            self.frequent_actions = json.dumps(data["frequent_actions"], ensure_ascii=False)
        if "historical_contexts" in data:
            self.historical_contexts = json.dumps(data["historical_contexts"], ensure_ascii=False)
        if "feedback_history" in data:
            self.feedback_history = json.dumps(data["feedback_history"], ensure_ascii=False)
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "preferences": self.preferences_dict,
            "frequent_actions": self.frequent_actions_list,
            "historical_contexts": self.historical_contexts_list,
            "feedback_history": self.feedback_history_list,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
