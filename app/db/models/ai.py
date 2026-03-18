from sqlalchemy import Column, Integer, String, DateTime, Text
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


class AITool(Base):
    __tablename__ = "ai_tools"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    tool_key = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    category_id = Column(Integer)
    description = Column(String)
    parameters = Column(String)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class AIConversation(Base):
    __tablename__ = "ai_conversations"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False)
    user_id = Column(String)
    role = Column(String, nullable=False)
    content = Column(String, nullable=False)
    intent = Column(String)
    conversation_metadata = Column(String)
    created_at = Column(DateTime)


class AIConversationSession(Base):
    __tablename__ = "ai_conversation_sessions"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, unique=True, nullable=False)
    user_id = Column(String)
    title = Column(String)
    summary = Column(String)
    message_count = Column(Integer, default=0)
    last_message_at = Column(DateTime)
    created_at = Column(DateTime)


class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    preference_key = Column(String, nullable=False)
    preference_value = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
