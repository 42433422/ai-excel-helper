"""
采购单生成工具
"""

import logging
from typing import Any

from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class PurchaseGenerateTool(BaseTool):
    name = "purchase_generate"
    description = "生成采购单"

    async def execute(
        self,
        products: list[dict[str, Any]],
        supplier: str = "",
        **kwargs
    ) -> ToolResult:
        try:
            import httpx

            payload = {
                "products": products,
                "supplier": supplier,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://127.0.0.1:8000/api/purchase/generate",
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        return ToolResult(
                            success=True,
                            data=result.get("data"),
                            message=result.get("message", "采购单生成成功")
                        )
                    else:
                        return ToolResult(
                            success=False,
                            error=result.get("error", ""),
                            message="采购单生成失败"
                        )
                else:
                    return await self._fallback_generate(products, supplier)

        except Exception as e:
            logger.warning(f"[PurchaseGenerateTool] API调用失败，降级处理: {e}")
            return await self._fallback_generate(products, supplier)

    async def _fallback_generate(self, products: list[dict[str, Any]], supplier: str) -> ToolResult:
        try:
            from datetime import datetime
            import uuid

            purchase_id = f"PO{datetime.now().strftime('%Y%m%d%H%M%S')}"

            data = {
                "purchase_id": purchase_id,
                "supplier": supplier,
                "products": products,
                "status": "待审核",
                "created_at": datetime.now().isoformat(),
            }

            return ToolResult(
                success=True,
                data=data,
                message=f"采购单 {purchase_id} 已生成（本地模式）"
            )
        except Exception as e:
            logger.exception(f"[PurchaseGenerateTool] 降级生成异常: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="采购单生成失败"
            )
