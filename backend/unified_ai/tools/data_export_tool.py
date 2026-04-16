"""
数据导出工具
"""

import logging
from typing import Any

from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class DataExportTool(BaseTool):
    name = "data_export"
    description = "导出数据（客户、产品、发货单等）"

    async def execute(
        self,
        data_type: str,
        format: str = "xlsx",
        date_range: str = "",
        **kwargs
    ) -> ToolResult:
        try:
            if data_type in ("customers", "customer"):
                return await self._export_customers(format)
            elif data_type in ("products", "product"):
                return await self._export_products(format)
            elif data_type in ("shipment", "shipments", "发货单"):
                return await self._export_shipments(format, date_range)
            elif data_type in ("materials", "material", "原材料"):
                return await self._export_materials(format)
            else:
                return ToolResult(
                    success=False,
                    error=f"不支持的数据类型: {data_type}",
                    message="数据导出失败"
                )
        except Exception as e:
            logger.exception(f"[DataExportTool] 异常: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="数据导出失败"
            )

    async def _export_customers(self, format: str) -> ToolResult:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "http://127.0.0.1:8000/api/customers/export",
                    params={"format": format}
                )

                if response.status_code == 200:
                    result = response.json()
                    return ToolResult(
                        success=True,
                        data=result.get("data", {}),
                        message="客户数据导出成功"
                    )
                else:
                    return await self._fallback_export_customers()
        except Exception:
            return await self._fallback_export_customers()

    async def _fallback_export_customers(self) -> ToolResult:
        try:
            from backend.routers.xcagi_compat import _load_customers_rows

            customers = _load_customers_rows()
            return ToolResult(
                success=True,
                data={"customers": customers, "total": len(customers)},
                message=f"已导出 {len(customers)} 个客户数据（本地模式）"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), message="客户数据导出失败")

    async def _export_products(self, format: str) -> ToolResult:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "http://127.0.0.1:8000/api/products/export.docx",
                    params={"format": format}
                )

                if response.status_code == 200:
                    return ToolResult(
                        success=True,
                        data={"format": format},
                        message="产品数据导出成功"
                    )
                else:
                    return await self._fallback_export_products()
        except Exception:
            return await self._fallback_export_products()

    async def _fallback_export_products(self) -> ToolResult:
        try:
            from backend.routers.xcagi_compat import _load_products_all_for_export

            products = _load_products_all_for_export()
            return ToolResult(
                success=True,
                data={"products": products, "total": len(products)},
                message=f"已导出 {len(products)} 个产品数据（本地模式）"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), message="产品数据导出失败")

    async def _export_shipments(self, format: str, date_range: str) -> ToolResult:
        return ToolResult(
            success=True,
            data={"format": format, "date_range": date_range},
            message="发货单数据导出功能开发中"
        )

    async def _export_materials(self, format: str) -> ToolResult:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "http://127.0.0.1:8000/api/materials",
                )

                if response.status_code == 200:
                    result = response.json()
                    materials = result.get("data", [])
                    return ToolResult(
                        success=True,
                        data={"materials": materials, "total": len(materials)},
                        message=f"已导出 {len(materials)} 条原材料数据"
                    )
                else:
                    return ToolResult(
                        success=False,
                        error=f"HTTP {response.status_code}",
                        message="原材料数据导出失败"
                    )
        except Exception as e:
            return ToolResult(success=False, error=str(e), message="原材料数据导出失败")
