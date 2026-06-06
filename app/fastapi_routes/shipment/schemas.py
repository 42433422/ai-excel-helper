from __future__ import annotations

from pydantic import BaseModel, Field


class ShipmentItem(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    product_name: str | None = None
    unit_price: float | None = None
    amount: float | None = None


class ShipmentGenerateRequest(BaseModel):
    customer_name: str | None = None
    items: list[ShipmentItem] = Field(default_factory=list)
    notes: str | None = None


class ShipmentPrintRequest(BaseModel):
    shipment_id: int
    printer_name: str | None = None
    copies: int = Field(default=1, ge=1, le=10)
