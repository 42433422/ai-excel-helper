from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from app.domain.value_objects_industry import get_current_industry_config


@dataclass(frozen=True)
class Money:
    """金额值对象 - 不可变"""

    amount: float
    currency: str = "CNY"

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("金额不能为负数")

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("货币单位不一致")
        return Money(self.amount + other.amount, self.currency)

    def __mul__(self, multiplier: float) -> "Money":
        return Money(self.amount * multiplier, self.currency)

    def to_yuan(self) -> float:
        return self.amount


class Quantity:
    """
    数量值对象 - 支持多行业配置

    默认使用涂料行业字段（tins/kg），通过行业配置支持扩展
    """

    __slots__ = ("primary", "secondary", "spec", "_industry_config")

    def __init__(
        self,
        primary: int = 0,
        secondary: float = 0.0,
        spec: float = 10.0,
        industry_config: Optional[Dict[str, Any]] = None,
    ):
        self.primary = primary
        self.secondary = secondary
        self.spec = spec
        self._industry_config = industry_config or get_current_industry_config()

    @property
    def tins(self) -> int:
        """涂料行业兼容：获取桶数"""
        return self.primary

    @property
    def kg(self) -> float:
        """涂料行业兼容：获取公斤"""
        return self.secondary

    @property
    def spec_per_tin(self) -> float:
        """涂料行业兼容：获取每桶规格"""
        return self.spec

    @property
    def primary_value(self) -> int:
        """通用获取主数量值"""
        return self.primary

    @property
    def secondary_value(self) -> float:
        """通用获取辅助数量值"""
        return self.secondary

    @property
    def primary_label(self) -> str:
        """获取主单位标签（如：桶数、件数、斤数）"""
        return self._industry_config.get("primary_label", "数量")

    @property
    def secondary_label(self) -> str:
        """获取辅助单位标签（如：公斤、箱数）"""
        return self._industry_config.get("secondary_label", "重量")

    @property
    def spec_label(self) -> str:
        """获取规格标签"""
        return self._industry_config.get("spec_label", "规格")

    @property
    def primary_unit(self) -> str:
        """获取主单位（如：桶、件、斤）"""
        return self._industry_config.get("primary", "桶")

    @property
    def secondary_unit(self) -> str:
        """获取辅助单位（如：kg、箱）"""
        return self._industry_config.get("secondary", "kg")

    def __repr__(self) -> str:
        return f"Quantity({self.primary}{self.primary_unit}, {self.secondary}{self.secondary_unit}, spec={self.spec})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Quantity):
            return False
        return (
            self.primary == other.primary
            and self.secondary == other.secondary
            and self.spec == other.spec
        )

    def __hash__(self) -> int:
        return hash((self.primary, self.secondary, self.spec))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，支持多行业"""
        config = self._industry_config
        return {
            config.get("primary_field", "tins"): self.primary,
            config.get("secondary_field", "kg"): self.secondary,
            config.get("spec_field", "spec_per_tin"): self.spec,
        }

    def to_industry_dict(self) -> Dict[str, Any]:
        """转换为包含行业标签的字典"""
        return {
            "primary": self.primary,
            "primary_label": self.primary_label,
            "primary_unit": self.primary_unit,
            "secondary": self.secondary,
            "secondary_label": self.secondary_label,
            "secondary_unit": self.secondary_unit,
            "spec": self.spec,
            "spec_label": self.spec_label,
        }

    @classmethod
    def from_tins_and_spec(cls, tins: int, spec_per_tin: float = 10.0) -> "Quantity":
        """涂料行业兼容工厂方法"""
        return cls(primary=tins, secondary=tins * spec_per_tin, spec=spec_per_tin)

    @classmethod
    def from_primary_and_spec(cls, primary: int, spec: float) -> "Quantity":
        """通用工厂方法：根据主数量和规格创建"""
        industry_config = get_current_industry_config()
        secondary = primary * spec
        conversion_key = (
            f"{industry_config.get('primary', '桶')}_to_{industry_config.get('secondary', 'kg')}"
        )
        conversion = industry_config.get("conversion", {}).get(conversion_key, spec)
        secondary = primary * conversion
        return cls(primary=primary, secondary=secondary, spec=spec)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Quantity":
        """从字典创建，支持多行业字段名"""
        industry_config = get_current_industry_config()
        primary_field = industry_config.get("primary_field", "tins")
        secondary_field = industry_config.get("secondary_field", "kg")
        spec_field = industry_config.get("spec_field", "spec_per_tin")

        primary = data.get(primary_field, data.get("tins", data.get("primary", 0)))
        secondary = data.get(secondary_field, data.get("kg", data.get("secondary", 0.0)))
        spec = data.get(spec_field, data.get("spec_per_tin", data.get("spec", 10.0)))

        return cls(primary=int(primary), secondary=float(secondary), spec=float(spec))


@dataclass(frozen=True)
class OrderNumber:
    """订单号值对象 - 不可变"""

    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("订单号不能为空")

    @classmethod
    def generate(cls) -> "OrderNumber":
        return cls(value=datetime.now().strftime("%Y%m%d%H%M%S"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ContactInfo:
    """联系方式值对象 - 不可变"""

    person: str
    phone: str
    address: Optional[str] = None

    @classmethod
    def empty(cls) -> "ContactInfo":
        """允许在未采集到联系人时使用的空对象。"""
        return cls(person="", phone="", address=None)


@dataclass(frozen=True)
class Price:
    """价格值对象 - 不可变"""

    unit_price: float
    discount_rate: float = 1.0

    def __post_init__(self):
        if self.unit_price < 0:
            raise ValueError("单价不能为负数")
        if not 0 <= self.discount_rate <= 1:
            raise ValueError("折扣率必须在 0-1 之间")

    def final_price(self) -> float:
        return self.unit_price * self.discount_rate

    def calculate_amount(self, quantity: Quantity) -> float:
        return self.final_price() * quantity.kg


@dataclass(frozen=True)
class ModelNumber:
    """产品型号值对象 - 不可变"""

    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("型号不能为空")

    def __str__(self) -> str:
        return self.value

    def matches(self, other: "ModelNumber") -> bool:
        return self.value.lower() == other.value.lower()

    def contains(self, keyword: str) -> bool:
        return keyword.lower() in self.value.lower()
