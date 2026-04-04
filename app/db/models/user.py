from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
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

    wx_openid = Column(String(64), unique=True, index=True)
    wx_unionid = Column(String(64), index=True)
    wx_avatar_url = Column(Text)
    mp_phone = Column(String(20))
    mp_nickname = Column(String(64))

    created_user = relationship("User", remote_side=[id], backref="created_users", foreign_keys=[created_by])
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    ai_conversation_sessions = relationship("AIConversationSession", back_populates="user", cascade="all, delete-orphan")
    mp_orders = relationship("MpOrder", back_populates="user")
    mp_carts = relationship("MpCart")
    mp_addresses = relationship("MpAddress")
    mp_browse_history = relationship("MpBrowseHistory")
    mp_favorites = relationship("MpFavorite")
    mp_notifications = relationship("MpNotification")
    mp_feedbacks = relationship("MpFeedback", foreign_keys="MpFeedback.user_id")


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="sessions")
