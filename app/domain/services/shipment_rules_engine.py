"""
发货规则引擎领域服务

负责发货单的业务规则验证和计算
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ShipmentRuleViolation:
    """发货规则违反"""
    rule_name: str
    message: str
    severity: str


class ShipmentValidationResult:
    """发货单验证结果"""

    def __init__(self):
        self.violations: List[ShipmentRuleViolation] = []

    @property
    def is_valid(self) -> bool:
        return len(self.violations) == 0

    def add_violation(self, rule_name: str, message: str, severity: str = "error"):
        self.violations.append(
            ShipmentRuleViolation(
                rule_name=rule_name,
                message=message,
                severity=severity
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "violations": [
                {
                    "rule": v.rule_name,
                    "message": v.message,
                    "severity": v.severity
                }
                for v in self.violations
            ]
        }


class ShipmentRulesEngine:
    """
    发货规则引擎领域服务

    核心职责：
    - 验证发货单数据的合法性
    - 应用业务规则进行检查
    - 计算发货单相关费用
    """

    def __init__(self):
        self._validation_rules = []
        self._init_default_rules()

    def _init_default_rules(self):
        """初始化默认规则"""
        self._validation_rules = [
            ("non_empty_unit", self._rule_non_empty_unit),
            ("valid_items", self._rule_valid_items),
            ("positive_quantity", self._rule_positive_quantity),
            ("valid_date", self._rule_valid_date),
        ]

    def validate(self, shipment_data: Dict[str, Any]) -> ShipmentValidationResult:
        """
        验证发货单数据

        Args:
            shipment_data: 发货单数据

        Returns:
            验证结果
        """
        result = ShipmentValidationResult()

        for rule_name, rule_func in self._validation_rules:
            violation = rule_func(shipment_data)
            if violation:
                result.add_violation(rule_name, violation)

        return result

    def _rule_non_empty_unit(self, data: Dict[str, Any]) -> Optional[str]:
        """规则：单位名称不能为空"""
        unit_name = data.get("unit_name") or data.get("customer_name")
        if not unit_name:
            return "单位名称不能为空"
        return None

    def _rule_valid_items(self, data: Dict[str, Any]) -> Optional[str]:
        """规则：必须有有效的货物项目"""
        items = data.get("items") or []
        if not items or len(items) == 0:
            return "发货单必须包含至少一个货物项目"
        return None

    def _rule_positive_quantity(self, data: Dict[str, Any]) -> Optional[str]:
        """规则：所有货物数量必须为正数"""
        items = data.get("items") or []
        for idx, item in enumerate(items):
            quantity = item.get("quantity", 0)
            if quantity <= 0:
                return f"第 {idx + 1} 项货物数量必须大于 0"
        return None

    def _rule_valid_date(self, data: Dict[str, Any]) -> Optional[str]:
        """规则：日期必须有效"""
        date_str = data.get("date")
        if date_str:
            try:
                datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                return "日期格式无效"
        return None

    def calculate_total(self, shipment_data: Dict[str, Any]) -> float:
        """
        计算发货单总金额

        Args:
            shipment_data: 发货单数据

        Returns:
            总金额
        """
        items = shipment_data.get("items") or []
        total = 0.0

        for item in items:
            quantity = item.get("quantity", 0)
            price = item.get("price", 0.0)
            total += quantity * price

        return total

    def suggest_priority(self, shipment_data: Dict[str, Any]) -> int:
        """
        根据发货单特征建议优先级

        Args:
            shipment_data: 发货单数据

        Returns:
            优先级 (1-5, 1 最高)
        """
        priority = 3

        unit_name = shipment_data.get("unit_name", "")
        if any(kw in unit_name for kw in ["紧急", "加急", "优先"]):
            priority = 1
        elif any(kw in unit_name for kw in ["vip", "重要", "大客户"]):
            priority = 2

        items_count = len(shipment_data.get("items") or [])
        if items_count > 10:
            priority = min(priority + 1, 5)

        return priority


def get_shipment_rules_engine() -> ShipmentRulesEngine:
    """获取发货规则引擎实例"""
    return ShipmentRulesEngine()
