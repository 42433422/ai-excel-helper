"""
合同校验工具
"""

import logging
from typing import Any

from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ContractTool(BaseTool):
    name = "contract_validate"
    description = "校验销售合同中的客户名称和产品型号是否有效"

    def execute(self, customer_name: str, products: list[dict[str, Any]], **kwargs) -> ToolResult:
        try:
            from backend.contract_validator import (
                augment_validate_contract_client_fields,
                validate_contract,
            )
            from backend.sales_contract_intent_bridge import merge_planner_sales_contract_args

            um = str(kwargs.get("_user_message") or "").strip()
            if um:
                merged = merge_planner_sales_contract_args(
                    {"customer_name": customer_name, "products": list(products or [])},
                    um,
                )
                customer_name = str(merged.get("customer_name") or customer_name)
                products = merged.get("products", products)

            result = validate_contract(customer_name, products)
            result = augment_validate_contract_client_fields(result)

            if result.get("valid"):
                return ToolResult(
                    success=True,
                    data=result,
                    message="合同校验通过"
                )
            else:
                return ToolResult(
                    success=True,
                    data=result,
                    message=result.get("message", "合同校验发现问题")
                )

        except Exception as e:
            logger.warning(f"[ContractTool] 校验异常: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="合同校验失败"
            )

    def validate_input(self, **kwargs) -> tuple[bool, str]:
        if not kwargs.get("customer_name"):
            return False, "客户名称不能为空"
        if not kwargs.get("products"):
            return False, "产品列表不能为空"
        return True, ""
