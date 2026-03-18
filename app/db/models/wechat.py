from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class WechatTask(Base):
    __tablename__ = "wechat_tasks"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer)
    username = Column(String)
    display_name = Column(String)
    message_id = Column(String)
    msg_timestamp = Column(Integer)
    raw_text = Column(Text, nullable=False)
    task_type = Column(String, nullable=False, default="unknown")
    status = Column(String, nullable=False, default="pending")
    last_status_at = Column(DateTime, server_default=func.current_timestamp())
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp())


class WechatContact(Base):
    __tablename__ = "wechat_contacts"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_name = Column(String, nullable=False)
    remark = Column(String)
    wechat_id = Column(String)
    contact_type = Column(String, default="contact")
    is_active = Column(Integer, default=1)
    is_starred = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp())


class WechatContactContext(Base):
    __tablename__ = "wechat_contact_context"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, nullable=False)
    wechat_id = Column(String)
    context_json = Column(Text)
    message_count = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.current_timestamp())
