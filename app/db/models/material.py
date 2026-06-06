from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String)
    specification: Mapped[Optional[str]] = mapped_column(String)
    unit: Mapped[str] = mapped_column(String, default="个")
    quantity: Mapped[float] = mapped_column(Float, default=0)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), default=0)
    supplier: Mapped[Optional[str]] = mapped_column(String)
    warehouse_location: Mapped[Optional[str]] = mapped_column(String)
    min_stock: Mapped[float] = mapped_column(Float, default=0)
    max_stock: Mapped[float] = mapped_column(Float, default=0)
    description: Mapped[Optional[str]] = mapped_column(String)
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
