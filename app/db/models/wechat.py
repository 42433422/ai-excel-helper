from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class WechatTask(Base):
    __tablename__ = "wechat_tasks"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("wechat_contacts.id", ondelete="CASCADE")
    )
    username: Mapped[Optional[str]] = mapped_column(String)
    display_name: Mapped[Optional[str]] = mapped_column(String)
    message_id: Mapped[Optional[str]] = mapped_column(String)
    msg_timestamp: Mapped[Optional[int]] = mapped_column(Integer)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    task_type: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    last_status_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    contact: Mapped[Optional[WechatContact]] = relationship("WechatContact", back_populates="tasks")


class WechatContact(Base):
    __tablename__ = "wechat_contacts"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_name: Mapped[str] = mapped_column(String, nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(String)
    wechat_id: Mapped[Optional[str]] = mapped_column(String)
    contact_type: Mapped[str] = mapped_column(String, default="contact")
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    is_starred: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    tasks: Mapped[list[WechatTask]] = relationship(
        "WechatTask", back_populates="contact", cascade="all, delete-orphan"
    )
    contexts: Mapped[list[WechatContactContext]] = relationship(
        "WechatContactContext", back_populates="contact", cascade="all, delete-orphan"
    )


class WechatContactContext(Base):
    __tablename__ = "wechat_contact_context"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wechat_contacts.id", ondelete="CASCADE"), nullable=False
    )
    wechat_id: Mapped[Optional[str]] = mapped_column(String)
    context_json: Mapped[Optional[str]] = mapped_column(Text)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    contact: Mapped[WechatContact] = relationship("WechatContact", back_populates="contexts")
