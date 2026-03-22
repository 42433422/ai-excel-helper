"""
定价引擎领域服务

负责价格计算和折扣策略
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class CustomerType(Enum):
    """客户类型"""
    RETAIL = "retail"
    WHOLESALE = "wholesale"
    VIP = "vip"
    DISTRIBUTOR = "distributor"


@dataclass
class PriceBreakdown:
    """价格明细"""
    base_price: float
    discount: float
    tax: float
    total: float


class PricingEngine:
    """
    定价引擎领域服务

    核心职责：
    - 计算产品价格
    - 应用折扣策略
    - 计算税费
    """

    def __init__(self):
        self._discount_strategies: Dict[CustomerType, Callable] = {
            CustomerType.VIP: self._vip_discount,
            CustomerType.DISTRIBUTOR: self._distributor_discount,
            CustomerType.WHOLESALE: self._wholesale_discount,
            CustomerType.RETAIL: self._retail_discount,
        }
        self._tax_rate = 0.13

    def calculate_price(
        self,
        base_price: float,
        quantity: int,
        customer_type: CustomerType = CustomerType.RETAIL,
        **kwargs
    ) -> PriceBreakdown:
        """
        计算价格

        Args:
            base_price: 基本价格
            quantity: 数量
            customer_type: 客户类型
            **kwargs: 其他参数

        Returns:
            价格明细
        """
        subtotal = base_price * quantity

        discount_strategy = self._discount_strategies.get(
            customer_type,
            self._retail_discount
        )
        discount = discount_strategy(subtotal, **kwargs)

        discounted_subtotal = subtotal - discount

        tax = discounted_subtotal * self._tax_rate

        total = discounted_subtotal + tax

        return PriceBreakdown(
            base_price=base_price,
            discount=discount,
            tax=round(tax, 2),
            total=round(total, 2)
        )

    def _vip_discount(self, subtotal: float, **kwargs) -> float:
        """VIP 客户折扣"""
        if subtotal >= 10000:
            return subtotal * 0.15
        elif subtotal >= 5000:
            return subtotal * 0.10
        return subtotal * 0.05

    def _distributor_discount(self, subtotal: float, **kwargs) -> float:
        """经销商折扣"""
        if subtotal >= 20000:
            return subtotal * 0.20
        elif subtotal >= 10000:
            return subtotal * 0.15
        return subtotal * 0.10

    def _wholesale_discount(self, subtotal: float, **kwargs) -> float:
        """批发客户折扣"""
        if subtotal >= 5000:
            return subtotal * 0.08
        return subtotal * 0.03

    def _retail_discount(self, subtotal: float, **kwargs) -> float:
        """零售客户折扣"""
        return 0.0

    def calculate_bulk_discount(
        self,
        items: List[Dict[str, Any]],
        threshold: int = 10
    ) -> float:
        """
        计算批量折扣

        Args:
            items: 产品项列表
            threshold: 触发批量折扣的最小项数

        Returns:
            批量折扣金额
        """
        if len(items) < threshold:
            return 0.0

        subtotal = sum(
            item.get("price", 0.0) * item.get("quantity", 1)
            for item in items
        )

        if len(items) >= 20:
            return subtotal * 0.05
        elif len(items) >= 10:
            return subtotal * 0.03

        return 0.0

    def get_volume_tier(self, quantity: int) -> str:
        """
        根据数量获取阶梯等级

        Args:
            quantity: 数量

        Returns:
            阶梯等级
        """
        if quantity >= 1000:
            return "tier_1"
        elif quantity >= 500:
            return "tier_2"
        elif quantity >= 100:
            return "tier_3"
        elif quantity >= 50:
            return "tier_4"
        return "standard"


def get_pricing_engine() -> PricingEngine:
    """获取定价引擎实例"""
    return PricingEngine()
