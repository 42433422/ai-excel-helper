"""
Money 值对象

表示货币金额，包含数值和货币类型。
确保金额计算的准确性和货币一致性。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum


class Currency(Enum):
    """支持的货币类型"""

    CNY = "CNY"  # 人民币
    USD = "USD"  # 美元
    EUR = "EUR"  # 欧元
    GBP = "GBP"  # 英镑
    JPY = "JPY"  # 日元


@dataclass(frozen=True)
class Money:
    """
    金额值对象

    特性：
    - 使用 Decimal 确保精度
    - 支持货币转换验证
    - 支持基本的算术运算

    Examples:
        >>> price = Money(Decimal("100.50"), Currency.CNY)
        >>> total = price * 3
        >>> discount = price * Percentage(10)
    """

    amount: Decimal
    currency: Currency

    def __post_init__(self):
        # 确保 amount 是 Decimal
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        # 标准化：保留两位小数
        rounded = self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        object.__setattr__(self, "amount", rounded)
        if self.amount < Decimal("0"):
            raise ValueError("金额不能为负数")

    @classmethod
    def from_float(cls, amount: float, currency: Currency = Currency.CNY) -> Money:
        """从浮点数创建（注意精度问题）"""
        return cls(Decimal(str(amount)), currency)

    @classmethod
    def from_string(cls, amount: str, currency: str = "CNY") -> Money:
        """从字符串创建"""
        return cls(Decimal(amount), Currency(currency))

    @classmethod
    def zero(cls, currency: Currency = Currency.CNY) -> Money:
        """创建零金额"""
        return cls(Decimal("0"), currency)

    def add(self, other: Money) -> Money:
        """加法：相同货币才能相加"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: Money) -> Money:
        """减法：相同货币才能相减"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {self.currency} and {other.currency}")
        return Money(self.amount - other.amount, self.currency)

    def multiply(self, factor: int | float | Decimal) -> Money:
        """乘法：金额 × 数量"""
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def divide(self, divisor: int | float | Decimal) -> Money:
        """除法：金额 ÷ 数量"""
        if divisor == 0:
            raise ValueError("Cannot divide by zero")
        return Money(self.amount / Decimal(str(divisor)), self.currency)

    def percentage(self, percent: int | float) -> Money:
        """计算百分比金额"""
        return Money(self.amount * Decimal(str(percent)) / Decimal("100"), self.currency)

    def is_zero(self) -> bool:
        """是否为零金额"""
        return self.amount == Decimal("0")

    def is_positive(self) -> bool:
        """是否为正数"""
        return self.amount > Decimal("0")

    def is_negative(self) -> bool:
        """是否为负数"""
        return self.amount < Decimal("0")

    def compare_to(self, other: Money) -> int:
        """
        比较两个金额
        Returns: -1 (小于), 0 (等于), 1 (大于)
        """
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare {self.currency} and {other.currency}")
        if self.amount < other.amount:
            return -1
        elif self.amount > other.amount:
            return 1
        return 0

    def greater_than(self, other: Money) -> bool:
        """是否大于"""
        return self.compare_to(other) > 0

    def less_than(self, other: Money) -> bool:
        """是否小于"""
        return self.compare_to(other) < 0

    def greater_than_or_equal(self, other: Money) -> bool:
        """是否大于等于"""
        return self.compare_to(other) >= 0

    def less_than_or_equal(self, other: Money) -> bool:
        """是否小于等于"""
        return self.compare_to(other) <= 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {"amount": float(self.amount), "currency": self.currency.value}

    @classmethod
    def from_dict(cls, data: dict) -> Money:
        """从字典创建"""
        return cls(
            amount=Decimal(str(data["amount"])), currency=Currency(data.get("currency", "CNY"))
        )

    def __str__(self) -> str:
        return f"{self.currency.value} {self.amount:.2f}"

    def __repr__(self) -> str:
        return f"Money(amount={self.amount}, currency={self.currency})"

    def __add__(self, other: Money) -> Money:
        return self.add(other)

    def __sub__(self, other: Money) -> Money:
        return self.subtract(other)

    def __mul__(self, factor: int | float | Decimal) -> Money:
        return self.multiply(factor)

    def __truediv__(self, divisor: int | float | Decimal) -> Money:
        return self.divide(divisor)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency

    def __hash__(self) -> int:
        return hash((self.amount, self.currency))
