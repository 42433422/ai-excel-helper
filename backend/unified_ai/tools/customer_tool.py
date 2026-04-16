"""
客户查询工具
"""

import logging
from typing import Any

from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class CustomerQueryTool(BaseTool):
    name = "customer_query"
    description = "查询客户信息"

    async def execute(
        self,
        customer_name: str = "",
        customer_id: str = "",
        **kwargs
    ) -> ToolResult:
        try:
            import httpx

            params = {}
            if customer_name:
                params["search"] = customer_name
            if customer_id:
                params["customer_id"] = customer_id

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "http://127.0.0.1:8000/api/customers/list",
                    params=params
                )

                if response.status_code == 200:
                    result = response.json()
                    customers = result.get("data", [])
                    return ToolResult(
                        success=True,
                        data={"customers": customers, "total": len(customers)},
                        message=f"查询到 {len(customers)} 个客户"
                    )
                else:
                    return await self._fallback_query(customer_name, customer_id)

        except Exception as e:
            logger.warning(f"[CustomerQueryTool] API调用失败，降级处理: {e}")
            return await self._fallback_query(customer_name, customer_id)

    async def _fallback_query(self, customer_name: str, customer_id: str) -> ToolResult:
        try:
            from backend.routers.xcagi_compat import _load_customers_rows

            customers = _load_customers_rows()

            if customer_name:
                customers = [
                    c for c in customers
                    if customer_name in (c.get("customer_name") or c.get("name") or c.get("unit_name") or "")
                ]

            if customer_id:
                customers = [
                    c for c in customers
                    if str(c.get("id", "")) == str(customer_id)
                ]

            return ToolResult(
                success=True,
                data={"customers": customers, "total": len(customers)},
                message=f"查询到 {len(customers)} 个客户"
            )
        except Exception as e:
            logger.exception(f"[CustomerQueryTool] 降级查询异常: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="客户查询失败"
            )
