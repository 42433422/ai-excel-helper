from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class PurchaseUnit(Base):
    __tablename__ = "purchase_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    unit_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_person: Mapped[Optional[str]] = mapped_column(String(100))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50))
    address: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self):
        return {
            "id": self.id,
            "customer_name": self.unit_name,
            "contact_person": self.contact_person or "",
            "contact_phone": self.contact_phone or "",
            "contact_address": self.address or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


Customer = PurchaseUnit
