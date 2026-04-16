"""
对账单生成工具
"""

import logging
from typing import Any

from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class StatementGenerateTool(BaseTool):
    name = "statement_generate"
    description = "生成客户对账单"

    async def execute(
        self,
        customer_name: str,
        date_range: str = "",
        **kwargs
    ) -> ToolResult:
        try:
            import httpx

            payload = {
                "customer_name": customer_name,
                "date_range": date_range,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://127.0.0.1:8000/api/statement/generate",
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        return ToolResult(
                            success=True,
                            data=result.get("data"),
                            message=result.get("message", "对账单生成成功")
                        )
                    else:
                        return ToolResult(
                            success=False,
                            error=result.get("error", ""),
                            message="对账单生成失败"
                        )
                elif response.status_code == 404:
                    return await self._fallback_generate(customer_name, date_range)
                else:
                    return await self._fallback_generate(customer_name, date_range)

        except Exception as e:
            logger.warning(f"[StatementGenerateTool] API调用失败，降级处理: {e}")
            return await self._fallback_generate(customer_name, date_range)

    async def _fallback_generate(self, customer_name: str, date_range: str) -> ToolResult:
        try:
            from datetime import datetime
            from backend.routers.xcagi_compat import _load_customers_rows

            customers = _load_customers_rows()
            matched = None
            for c in customers:
                name = c.get("customer_name") or c.get("name") or c.get("unit_name") or ""
                if customer_name in name or name in customer_name:
                    matched = c
                    break

            data = {
                "customer_name": customer_name,
                "customer_info": matched,
                "date_range": date_range or f"截至 {datetime.now().strftime('%Y-%m-%d')}",
                "generated_at": datetime.now().isoformat(),
                "items": [],
                "total_amount": 0,
            }

            return ToolResult(
                success=True,
                data=data,
                message=f"客户「{customer_name}」对账单已生成（本地模式，暂无交易数据）"
            )
        except Exception as e:
            logger.exception(f"[StatementGenerateTool] 降级生成异常: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="对账单生成失败"
            )
