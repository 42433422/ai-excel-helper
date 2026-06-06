from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_unit", "unit"),
        Index("ix_products_model_number", "model_number"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_number: Mapped[Optional[str]] = mapped_column(String)
    name: Mapped[str] = mapped_column(String, nullable=False)
    specification: Mapped[Optional[str]] = mapped_column(String)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), default=0.0)
    quantity: Mapped[Optional[int]] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(String)
    category: Mapped[Optional[str]] = mapped_column(String)
    brand: Mapped[Optional[str]] = mapped_column(String)
    unit: Mapped[str] = mapped_column(String, default="个")
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
