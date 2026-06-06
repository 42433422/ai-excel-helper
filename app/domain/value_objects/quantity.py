"""
Quantity 值对象

表示数量和计量单位，用于库存、订单等场景。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum


class UnitOfMeasure(Enum):
    """计量单位"""

    # 重量
    KG = "kg"  # 千克
    G = "g"  # 克
    TON = "ton"  # 吨
    # 体积
    LITER = "L"  # 升
    ML = "ml"  # 毫升
    CUBIC_METER = "m³"  # 立方米
    # 数量
    PIECE = "pcs"  # 件
    BOX = "box"  # 箱
    BOTTLE = "bottle"  # 瓶
    BUCKET = "bucket"  # 桶
    SET = "set"  # 套
    ROLL = "roll"  # 卷
    # 长度
    METER = "m"  # 米
    CENTIMETER = "cm"  # 厘米


@dataclass(frozen=True)
class Quantity:
    """
    数量值对象

    特性：
    - 数值 + 单位
    - 支持单位转换
    - 支持基本运算

    Examples:
        >>> qty = Quantity(Decimal("100"), UnitOfMeasure.KG)
        >>> total = qty * 3
        >>> qty.to_unit(UnitOfMeasure.TON)  # 转换为吨
    """

    value: Decimal
    unit: UnitOfMeasure

    def __post_init__(self):
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(str(self.value)))
        # 标准化精度
        rounded = self.value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        object.__setattr__(self, "value", rounded)

    @classmethod
    def from_float(cls, value: float, unit: UnitOfMeasure) -> Quantity:
        """从浮点数创建"""
        return cls(Decimal(str(value)), unit)

    @classmethod
    def from_int(cls, value: int, unit: UnitOfMeasure) -> Quantity:
        """从整数创建"""
        return cls(Decimal(value), unit)

    @classmethod
    def zero(cls, unit: UnitOfMeasure = UnitOfMeasure.PIECE) -> Quantity:
        """创建零数量"""
        return cls(Decimal("0"), unit)

    def add(self, other: Quantity) -> Quantity:
        """加法：相同单位才能相加"""
        if self.unit != other.unit:
            raise ValueError(f"Cannot add {self.unit} and {other.unit}")
        return Quantity(self.value + other.value, self.unit)

    def subtract(self, other: Quantity) -> Quantity:
        """减法：相同单位才能相减"""
        if self.unit != other.unit:
            raise ValueError(f"Cannot subtract {self.unit} and {other.unit}")
        result = self.value - other.value
        if result < Decimal("0"):
            raise ValueError("Result would be negative")
        return Quantity(result, self.unit)

    def multiply(self, factor: int | float | Decimal) -> Quantity:
        """乘法"""
        return Quantity(self.value * Decimal(str(factor)), self.unit)

    def divide(self, divisor: int | float | Decimal) -> Quantity:
        """除法"""
        if divisor == 0:
            raise ValueError("Cannot divide by zero")
        return Quantity(self.value / Decimal(str(divisor)), self.unit)

    def to_unit(self, target_unit: UnitOfMeasure) -> Quantity:
        """
        转换单位（支持常用转换）
        """
        # 重量转换
        weight_conversions = {
            (UnitOfMeasure.G, UnitOfMeasure.KG): Decimal("0.001"),
            (UnitOfMeasure.KG, UnitOfMeasure.G): Decimal("1000"),
            (UnitOfMeasure.KG, UnitOfMeasure.TON): Decimal("0.001"),
            (UnitOfMeasure.TON, UnitOfMeasure.KG): Decimal("1000"),
        }
        # 体积转换
        volume_conversions = {
            (UnitOfMeasure.ML, UnitOfMeasure.LITER): Decimal("0.001"),
            (UnitOfMeasure.LITER, UnitOfMeasure.ML): Decimal("1000"),
        }
        # 长度转换
        length_conversions = {
            (UnitOfMeasure.CENTIMETER, UnitOfMeasure.METER): Decimal("0.01"),
            (UnitOfMeasure.METER, UnitOfMeasure.CENTIMETER): Decimal("100"),
        }

        all_conversions = {**weight_conversions, **volume_conversions, **length_conversions}

        if self.unit == target_unit:
            return self

        key = (self.unit, target_unit)
        if key in all_conversions:
            new_value = self.value * all_conversions[key]
            return Quantity(new_value, target_unit)

        raise ValueError(f"Cannot convert from {self.unit} to {target_unit}")

    def is_zero(self) -> bool:
        """是否为零"""
        return self.value == Decimal("0")

    def is_positive(self) -> bool:
        """是否为正数"""
        return self.value > Decimal("0")

    def greater_than(self, other: Quantity) -> bool:
        """是否大于"""
        if self.unit != other.unit:
            raise ValueError(f"Cannot compare {self.unit} and {other.unit}")
        return self.value > other.value

    def less_than(self, other: Quantity) -> bool:
        """是否小于"""
        if self.unit != other.unit:
            raise ValueError(f"Cannot compare {self.unit} and {other.unit}")
        return self.value < other.value

    def greater_than_or_equal(self, other: Quantity) -> bool:
        """是否大于等于"""
        if self.unit != other.unit:
            raise ValueError(f"Cannot compare {self.unit} and {other.unit}")
        return self.value >= other.value

    def less_than_or_equal(self, other: Quantity) -> bool:
        """是否小于等于"""
        if self.unit != other.unit:
            raise ValueError(f"Cannot compare {self.unit} and {other.unit}")
        return self.value <= other.value

    def to_dict(self) -> dict:
        """转换为字典"""
        return {"value": float(self.value), "unit": self.unit.value}

    @classmethod
    def from_dict(cls, data: dict) -> Quantity:
        """从字典创建"""
        return cls(value=Decimal(str(data["value"])), unit=UnitOfMeasure(data.get("unit", "pcs")))

    def __str__(self) -> str:
        return f"{self.value} {self.unit.value}"

    def __repr__(self) -> str:
        return f"Quantity(value={self.value}, unit={self.unit})"

    def __add__(self, other: Quantity) -> Quantity:
        return self.add(other)

    def __sub__(self, other: Quantity) -> Quantity:
        return self.subtract(other)

    def __mul__(self, factor: int | float | Decimal) -> Quantity:
        return self.multiply(factor)

    def __truediv__(self, divisor: int | float | Decimal) -> Quantity:
        return self.divide(divisor)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Quantity):
            return False
        return self.value == other.value and self.unit == other.unit

    def __hash__(self) -> int:
        return hash((self.value, self.unit))
