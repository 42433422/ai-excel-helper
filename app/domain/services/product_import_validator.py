"""
产品导入验证领域服务

负责验证产品导入数据的业务规则
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ValidationError:
    """验证错误"""
    field: str
    message: str
    severity: str = "error"


class ValidationResult:
    """验证结果"""

    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, field: str, message: str):
        self.errors.append(ValidationError(field=field, message=message, severity="error"))

    def add_warning(self, field: str, message: str):
        self.warnings.append(ValidationError(field=field, message=message, severity="warning"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": [{"field": e.field, "message": e.message} for e in self.errors],
            "warnings": [{"field": w.field, "message": w.message} for w in self.warnings]
        }


class ProductImportValidator:
    """
    产品导入验证领域服务

    核心职责：
    - 验证产品数据的完整性
    - 检查数据格式和范围
    - 提供验证建议
    """

    def __init__(self):
        self._required_fields = ["name", "price"]
        self._optional_fields = [
            "model_number", "specification", "quantity",
            "category", "brand", "unit", "description"
        ]
        self._numeric_fields = ["price", "quantity"]
        self._max_name_length = 200
        self._max_price = 9999999.99

    def validate(self, products: List[Dict[str, Any]]) -> ValidationResult:
        """
        验证产品数据列表

        Args:
            products: 产品数据列表

        Returns:
            验证结果
        """
        result = ValidationResult()

        if not products:
            result.add_error("products", "产品列表不能为空")
            return result

        for idx, product in enumerate(products):
            self._validate_single_product(product, idx, result)

        return result

    def _validate_single_product(
        self,
        product: Dict[str, Any],
        index: int,
        result: ValidationResult
    ):
        """验证单个产品数据"""
        prefix = f"产品[{index}]"

        if not product.get("name"):
            result.add_error(f"{prefix}.name", "产品名称不能为空")

        name = product.get("name", "")
        if len(name) > self._max_name_length:
            result.add_warning(
                f"{prefix}.name",
                f"产品名称过长 ({len(name)} > {self._max_name_length})"
            )

        if "price" in product:
            price = product["price"]
            if not isinstance(price, (int, float)):
                result.add_error(f"{prefix}.price", "价格必须是数字")
            elif price < 0:
                result.add_error(f"{prefix}.price", "价格不能为负数")
            elif price > self._max_price:
                result.add_warning(
                    f"{prefix}.price",
                    f"价格超出正常范围 (>{self._max_price})"
                )

        if "quantity" in product:
            quantity = product["quantity"]
            if not isinstance(quantity, (int, float)):
                result.add_error(f"{prefix}.quantity", "数量必须是数字")
            elif quantity < 0:
                result.add_error(f"{prefix}.quantity", "数量不能为负数")

    def validate_batch_size(self, products: List[Dict[str, Any]], max_size: int = 1000) -> ValidationResult:
        """验证批次大小"""
        result = ValidationResult()

        if len(products) > max_size:
            result.add_error(
                "batch_size",
                f"批次大小超出限制 ({len(products)} > {max_size})"
            )

        return result

    def suggest_fixes(self, result: ValidationResult) -> List[Dict[str, Any]]:
        """根据验证结果建议修复方案"""
        suggestions = []

        for error in result.errors:
            if error.field.endswith(".name") and "为空" in error.message:
                suggestions.append({
                    "field": error.field,
                    "suggestion": "请提供产品名称"
                })
            elif error.field.endswith(".price"):
                suggestions.append({
                    "field": error.field,
                    "suggestion": "请提供有效的价格数字"
                })

        return suggestions


def get_product_import_validator() -> ProductImportValidator:
    """获取产品导入验证器实例"""
    return ProductImportValidator()
