"""
值对象层 (Value Objects)

值对象是领域驱动设计中的核心概念，特点：
- 不可变性 (Immutable)
- 通过属性值判断相等性
- 无唯一标识
- 业务规则的载体

Level 3 领域模型关键组件
"""

from .address import Address, ContactInfo
from .date_range import DateRange
from .email import Email
from .model_number import ModelNumber
from .money import Currency, Money
from .order_number import OrderNumber
from .percentage import Percentage
from .phone import PhoneNumber
from .price import Price
from .quantity import Quantity, UnitOfMeasure

__all__ = [
    # Money
    "Money",
    "Currency",
    # Quantity
    "Quantity",
    "UnitOfMeasure",
    # Address
    "Address",
    "ContactInfo",
    # Date
    "DateRange",
    # Percentage
    "Percentage",
    # Contact
    "Email",
    "PhoneNumber",
    "OrderNumber",
    "ModelNumber",
    "Price",
]
