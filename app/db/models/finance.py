from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")

    reference_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reference_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)

    counterparty_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    counterparty_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_fin_txn_type_date", "transaction_type", "transaction_date"),
        Index("ix_fin_txn_ref", "reference_type", "reference_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "transaction_type": self.transaction_type,
            "amount": float(self.amount) if self.amount is not None else None,
            "currency": self.currency,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "description": self.description,
            "transaction_date": (
                self.transaction_date.isoformat() if self.transaction_date else None
            ),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "counterparty_name": self.counterparty_name,
            "counterparty_id": self.counterparty_id,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
