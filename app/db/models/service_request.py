from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func as sql_func

from app.db.base import Base


class ServiceRequestStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ServiceRequestPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_instance_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_instance_name: Mapped[str] = mapped_column(String(128), nullable=False)
    request_type: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ServiceRequestPriority.NORMAL.value
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ServiceRequestStatus.PENDING.value, index=True
    )
    response: Mapped[Optional[str]] = mapped_column(Text)
    responded_by: Mapped[Optional[str]] = mapped_column(String(64))
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    extra_data: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=sql_func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=sql_func.now(), onupdate=sql_func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_instance_id": self.source_instance_id,
            "source_instance_name": self.source_instance_name,
            "request_type": self.request_type,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "response": self.response,
            "responded_by": self.responded_by,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ServiceBridgeConfig(Base):
    __tablename__ = "service_bridge_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(256))
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=sql_func.now(), onupdate=sql_func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "config_key": self.config_key,
            "config_value": self.config_value,
            "description": self.description,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
