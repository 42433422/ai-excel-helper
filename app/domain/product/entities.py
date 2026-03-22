from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.domain.value_objects import ModelNumber, Money


@dataclass
class Product:
    """产品实体"""
    id: Optional[int] = None
    model_number: ModelNumber = None
    name: str = ""
    specification: str = ""
    price: Money = field(default_factory=lambda: Money(0))
    quantity: int = 0
    description: str = ""
    category: str = ""
    brand: str = ""
    unit: str = "个"
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.name:
            raise ValueError("产品名称不能为空")

    def apply_discount(self, discount_rate: float) -> Money:
        return Money(self.price.amount * discount_rate)

    def is_available(self) -> bool:
        return self.is_active and self.quantity > 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model_number": str(self.model_number) if self.model_number else "",
            "name": self.name,
            "specification": self.specification,
            "price": self.price.amount,
            "quantity": self.quantity,
            "description": self.description,
            "category": self.category,
            "brand": self.brand,
            "unit": self.unit,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def create(cls, name: str, model_number: str = "", price: float = 0.0) -> 'Product':
        return cls(
            name=name,
            model_number=ModelNumber(model_number) if model_number else None,
            price=Money(price),
        )

    def match(self, name: str = "", model_number: str = "") -> bool:
        if model_number and self.model_number:
            if self.model_number.matches(ModelNumber(model_number)):
                return True
        if name and self.name:
            return name.lower() in self.name.lower() or self.name.lower() in name.lower()
        return False
