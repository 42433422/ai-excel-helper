"""
报表生成工具
"""

import logging
from typing import Any

from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ReportGenerateTool(BaseTool):
    name = "report_generate"
    description = "生成业务报表（销售报表、库存报表等）"

    async def execute(
        self,
        report_type: str = "sales",
        date_range: str = "",
        **kwargs
    ) -> ToolResult:
        try:
            import httpx

            payload = {
                "report_type": report_type,
                "date_range": date_range,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://127.0.0.1:8000/api/report/generate",
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        return ToolResult(
                            success=True,
                            data=result.get("data"),
                            message=result.get("message", "报表生成成功")
                        )
                    else:
                        return ToolResult(
                            success=False,
                            error=result.get("error", ""),
                            message="报表生成失败"
                        )
                else:
                    return await self._fallback_generate(report_type, date_range)

        except Exception as e:
            logger.warning(f"[ReportGenerateTool] API调用失败，降级处理: {e}")
            return await self._fallback_generate(report_type, date_range)

    async def _fallback_generate(self, report_type: str, date_range: str) -> ToolResult:
        try:
            from datetime import datetime

            type_labels = {
                "sales": "销售报表",
                "stock": "库存报表",
                "shipment": "发货报表",
                "purchase": "采购报表",
            }

            label = type_labels.get(report_type, f"{report_type}报表")

            data = {
                "report_type": report_type,
                "report_label": label,
                "date_range": date_range or f"截至 {datetime.now().strftime('%Y-%m-%d')}",
                "generated_at": datetime.now().isoformat(),
                "summary": {},
                "items": [],
            }

            if report_type == "stock":
                data["summary"] = await self._get_stock_summary()

            return ToolResult(
                success=True,
                data=data,
                message=f"{label}已生成（本地模式）"
            )
        except Exception as e:
            logger.exception(f"[ReportGenerateTool] 降级生成异常: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="报表生成失败"
            )

    async def _get_stock_summary(self) -> dict:
        try:
            from backend.routers.xcagi_compat import _load_products_all_for_export

            products = _load_products_all_for_export()
            return {
                "total_products": len(products),
                "active_products": len([p for p in products if p.get("is_active", True)]),
            }
        except Exception:
            return {}
