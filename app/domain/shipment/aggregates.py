from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from app.domain.value_objects import ContactInfo, Money, OrderNumber, Quantity


@dataclass
class ShipmentItem:
    """发货单项实体"""

    id: Optional[int] = None
    product_name: str = ""
    model_number: str = ""
    quantity: Quantity = field(default_factory=lambda: Quantity(0, 0))
    unit_price: Money = field(default_factory=lambda: Money(0))
    amount: Money = field(default_factory=lambda: Money(0))
    raw_data: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.product_name:
            raise ValueError("产品名称不能为空")

    def calculate_amount(self) -> Money:
        self.amount = self.unit_price * (self.quantity.kg / 10.0) if self.quantity.kg else Money(0)
        return self.amount

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_name": self.product_name,
            "model_number": self.model_number,
            "quantity_tins": self.quantity.tins,
            "quantity_kg": self.quantity.kg,
            "spec_per_tin": self.quantity.spec_per_tin,
            "unit_price": self.unit_price.amount,
            "amount": self.amount.amount,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShipmentItem":
        quantity = Quantity.from_tins_and_spec(
            tins=data.get("quantity_tins", 0),
            spec_per_tin=data.get("tin_spec", data.get("spec_per_tin", 10.0)),
        )
        unit_price = Money(data.get("unit_price", 0))
        amount = Money(data.get("amount", 0))

        return cls(
            id=data.get("id"),
            product_name=data.get("product_name", data.get("name", "")),
            model_number=data.get("model_number", ""),
            quantity=quantity,
            unit_price=unit_price,
            amount=amount,
            raw_data=data,
        )


@dataclass
class Shipment:
    """发货单聚合根"""

    id: Optional[int] = None
    order_number: OrderNumber = field(default_factory=OrderNumber.generate)
    purchase_unit_name: str = ""
    contact_info: ContactInfo = field(default_factory=lambda: ContactInfo("", ""))
    items: List[ShipmentItem] = field(default_factory=list)
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    printed_at: Optional[datetime] = None
    printer_name: Optional[str] = None
    raw_text: Optional[str] = None
    total_amount: Money = field(default_factory=lambda: Money(0))
    total_quantity: Quantity = field(default_factory=lambda: Quantity(0, 0))

    def __post_init__(self):
        if not self.purchase_unit_name:
            raise ValueError("购买单位不能为空")

    def add_item(self, item: ShipmentItem) -> None:
        self.items.append(item)
        self._recalculate_totals()
        self.updated_at = datetime.now()

    def remove_item(self, index: int) -> ShipmentItem:
        if 0 <= index < len(self.items):
            removed = self.items.pop(index)
            self._recalculate_totals()
            self.updated_at = datetime.now()
            return removed
        raise IndexError("索引超出范围")

    def _recalculate_totals(self) -> None:
        total = Money(0)
        total_tins = 0
        total_kg = 0.0

        for item in self.items:
            total = total + item.amount
            total_tins += item.quantity.tins
            total_kg += item.quantity.kg

        self.total_amount = total
        self.total_quantity = Quantity(total_tins, total_kg)

    def mark_as_printed(self, printer_name: str = "") -> None:
        self.status = "printed"
        self.printed_at = datetime.now()
        self.printer_name = printer_name
        self.updated_at = datetime.now()

    def cancel(self) -> None:
        self.status = "cancelled"
        self.updated_at = datetime.now()

    def is_valid(self) -> bool:
        return bool(self.purchase_unit_name) and len(self.items) > 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_number": str(self.order_number),
            "purchase_unit": self.purchase_unit_name,
            "contact_person": self.contact_info.person,
            "contact_phone": self.contact_info.phone,
            "contact_address": self.contact_info.address,
            "items": [item.to_dict() for item in self.items],
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "printed_at": self.printed_at.isoformat() if self.printed_at else None,
            "printer_name": self.printer_name,
            "total_amount": self.total_amount.amount,
            "total_quantity_tins": self.total_quantity.tins,
            "total_quantity_kg": self.total_quantity.kg,
        }

    @classmethod
    def create(cls, unit_name: str, contact_info: ContactInfo = None) -> "Shipment":
        return cls(
            order_number=OrderNumber.generate(),
            purchase_unit_name=unit_name,
            contact_info=contact_info or ContactInfo("", ""),
        )
