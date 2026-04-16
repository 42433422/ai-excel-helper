"""
产品匹配工具
"""

import logging
from typing import Any

from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ProductTool(BaseTool):
    name = "product_match"
    description = "根据产品型号或名称匹配产品信息"

    def execute(self, query: str, customer_name: str = "", **kwargs) -> ToolResult:
        try:
            from backend.product_semantic_matcher import semantic_match_product

            result = semantic_match_product(query)

            if result:
                return ToolResult(
                    success=True,
                    data={
                        "matches": [result] if result else [],
                        "best_match": result
                    },
                    message="产品匹配成功"
                )
            else:
                return ToolResult(
                    success=True,
                    data={"matches": [], "best_match": None},
                    message="未找到匹配产品"
                )

        except Exception as e:
            logger.warning(f"[ProductTool] 匹配异常: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="产品匹配失败"
            )

    def validate_input(self, **kwargs) -> tuple[bool, str]:
        if not kwargs.get("query"):
            return False, "查询内容不能为空"
        return True, ""
