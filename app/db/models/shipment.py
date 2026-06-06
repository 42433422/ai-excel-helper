from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, Float, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.fk_validation import ForeignKeyValidator


class ShipmentRecord(Base):
    __tablename__ = "shipment_records"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_unit: Mapped[str] = mapped_column(String, nullable=False)
    unit_id: Mapped[Optional[int]] = mapped_column(Integer)
    product_name: Mapped[str] = mapped_column(String, nullable=False)
    model_number: Mapped[Optional[str]] = mapped_column(String)
    quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    quantity_tins: Mapped[int] = mapped_column(Integer, nullable=False)
    tin_spec: Mapped[Optional[float]] = mapped_column(Float)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), default=0)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    printed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    printer_name: Mapped[Optional[str]] = mapped_column(String)
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    parsed_data: Mapped[Optional[str]] = mapped_column(Text)

    @validates("unit_id")
    def validate_unit_id(self, key: str, unit_id: Any) -> Any:
        if unit_id is None:
            return unit_id

        if not isinstance(unit_id, int):
            raise ValueError(f"Invalid unit_id type: {type(unit_id)}. Must be integer.")

        if unit_id <= 0:
            raise ValueError(f"Invalid unit_id: {unit_id}. Must be positive integer.")

        return unit_id

    def validate_foreign_keys(self, validator: ForeignKeyValidator) -> bool:
        return validator.validate_purchase_unit_exists(self.unit_id)

    def to_dict_with_validation(self, validator: ForeignKeyValidator) -> dict:
        data = self.to_dict()
        data["_fk_valid"] = self.validate_foreign_keys(validator)
        if self.unit_id and not data["_fk_valid"]:
            data["_fk_warning"] = f"unit_id={self.unit_id} does not exist in purchase_units"
        return data

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "purchase_unit": self.purchase_unit,
            "unit_id": self.unit_id,
            "product_name": self.product_name,
            "model_number": self.model_number,
            "quantity_kg": self.quantity_kg,
            "quantity_tins": self.quantity_tins,
            "tin_spec": self.tin_spec,
            "unit_price": self.unit_price,
            "amount": self.amount,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "printed_at": self.printed_at.isoformat() if self.printed_at else None,
            "printer_name": self.printer_name,
            "raw_text": self.raw_text,
            "parsed_data": self.parsed_data,
        }
