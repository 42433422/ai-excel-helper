from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.domain.value_objects import ContactInfo


@dataclass
class Customer:
    """客户实体"""
    id: Optional[int] = None
    customer_name: str = ""
    contact_info: ContactInfo = field(default_factory=lambda: ContactInfo("", ""))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.customer_name:
            raise ValueError("客户名称不能为空")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_name": self.customer_name,
            "contact_person": self.contact_info.person,
            "contact_phone": self.contact_info.phone,
            "contact_address": self.contact_info.address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def create(cls, customer_name: str, contact_person: str = "", phone: str = "", address: str = "") -> 'Customer':
        return cls(
            customer_name=customer_name,
            contact_info=ContactInfo(person=contact_person, phone=phone, address=address),
        )


@dataclass
class PurchaseUnit:
    """购买单位实体"""
    id: Optional[int] = None
    unit_name: str = ""
    contact_person: str = ""
    contact_phone: str = ""
    address: str = ""
    discount_rate: float = 1.0
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.unit_name:
            raise ValueError("单位名称不能为空")
        if not 0 <= self.discount_rate <= 1:
            raise ValueError("折扣率必须在 0-1 之间")

    def get_contact_info(self) -> ContactInfo:
        return ContactInfo(
            person=self.contact_person,
            phone=self.contact_phone,
            address=self.address
        )

    def apply_discount(self, original_price: float) -> float:
        return original_price * self.discount_rate

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "unit_name": self.unit_name,
            "contact_person": self.contact_person,
            "contact_phone": self.contact_phone,
            "address": self.address,
            "discount_rate": self.discount_rate,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def create(cls, unit_name: str, discount_rate: float = 1.0) -> 'PurchaseUnit':
        return cls(unit_name=unit_name, discount_rate=discount_rate)
