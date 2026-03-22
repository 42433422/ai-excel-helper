from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    display_name = Column(String, default="")
    email = Column(String, default="")
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime)
    last_login = Column(DateTime)

    created_user = relationship("User", remote_side=[id], backref="created_users", foreign_keys=[created_by])
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    ai_conversation_sessions = relationship("AIConversationSession", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="sessions")
