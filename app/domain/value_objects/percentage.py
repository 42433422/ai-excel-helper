"""
Percentage 值对象

表示百分比值，用于折扣、税率、完成率等场景。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class Percentage:
    """
    百分比值对象

    内部存储为 Decimal（如 10% 存储为 10，不是 0.1）
    便于计算和显示。

    Examples:
        >>> discount = Percentage(10)  # 10%
        >>> price = Money(Decimal("100"), Currency.CNY)
        >>> discounted_price = price * discount
    """

    value: Decimal

    def __post_init__(self):
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(str(self.value)))
        # 标准化：保留两位小数
        rounded = self.value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        object.__setattr__(self, "value", rounded)

    @classmethod
    def from_float(cls, value: float) -> Percentage:
        """从浮点数创建"""
        return cls(Decimal(str(value)))

    @classmethod
    def from_fraction(cls, fraction: Decimal) -> Percentage:
        """从分数创建（如 0.1 -> 10%）"""
        return cls(fraction * Decimal("100"))

    @classmethod
    def zero(cls) -> Percentage:
        """0%"""
        return cls(Decimal("0"))

    @classmethod
    def full(cls) -> Percentage:
        """100%"""
        return cls(Decimal("100"))

    @property
    def as_fraction(self) -> Decimal:
        """转换为分数（如 10% -> 0.1）"""
        return self.value / Decimal("100")

    @property
    def as_display_string(self) -> str:
        """显示字符串（如 "10%"）"""
        if self.value == self.value.to_integral_value():
            return f"{int(self.value)}%"
        return f"{float(self.value)}%"

    def add(self, other: Percentage) -> Percentage:
        """加法"""
        return Percentage(self.value + other.value)

    def subtract(self, other: Percentage) -> Percentage:
        """减法"""
        result = self.value - other.value
        if result < Decimal("0"):
            raise ValueError("Result would be negative")
        return Percentage(result)

    def multiply(self, factor: int | float | Decimal) -> Percentage:
        """乘法"""
        return Percentage(self.value * Decimal(str(factor)))

    def apply_to(self, amount: Decimal) -> Decimal:
        """
        应用到金额
        Returns: amount * percentage
        """
        return amount * self.as_fraction

    def discount_from(self, amount: Decimal) -> Decimal:
        """
        从金额计算折扣后的值
        Returns: amount * (1 - percentage)
        """
        return amount * (Decimal("1") - self.as_fraction)

    def is_zero(self) -> bool:
        """是否为 0%"""
        return self.value == Decimal("0")

    def is_full(self) -> bool:
        """是否为 100%"""
        return self.value == Decimal("100")

    def greater_than(self, other: Percentage) -> bool:
        """是否大于"""
        return self.value > other.value

    def less_than(self, other: Percentage) -> bool:
        """是否小于"""
        return self.value < other.value

    def to_dict(self) -> dict:
        return {"value": float(self.value), "display": self.as_display_string}

    @classmethod
    def from_dict(cls, data: dict) -> Percentage:
        return cls(Decimal(str(data["value"])))

    def __str__(self) -> str:
        return self.as_display_string

    def __repr__(self) -> str:
        return f"Percentage(value={self.value})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Percentage):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __float__(self) -> float:
        return float(self.value)

    def __mul__(self, amount: Decimal) -> Decimal:
        """支持 amount * percentage"""
        return self.apply_to(amount)

    def __rmul__(self, amount: Decimal) -> Decimal:
        """支持 percentage * amount"""
        return self.apply_to(amount)
