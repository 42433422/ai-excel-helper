"""
库存查询工具
"""

import logging
from typing import Any

from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class StockQueryTool(BaseTool):
    name = "stock_query"
    description = "查询库存信息（产品库存和原材料库存）"

    async def execute(
        self,
        query: str = "",
        product_name: str = "",
        **kwargs
    ) -> ToolResult:
        search = query or product_name

        product_result = await self._query_product_stock(search)
        material_result = await self._query_material_stock(search)

        results = []
        if product_result.get("data"):
            results.extend(product_result["data"].get("products", []))
        if material_result.get("data"):
            results.extend(material_result["data"].get("materials", []))

        return ToolResult(
            success=True,
            data={
                "results": results,
                "product_count": len(product_result.get("data", {}).get("products", [])),
                "material_count": len(material_result.get("data", {}).get("materials", [])),
            },
            message=f"查询到 {len(results)} 条库存记录"
        )

    async def _query_product_stock(self, search: str) -> dict:
        try:
            from backend.routers.xcagi_compat import _load_products_all_for_export

            products = _load_products_all_for_export(keyword=search if search else None)

            stock_items = []
            for p in products:
                stock_items.append({
                    "type": "product",
                    "name": p.get("name", ""),
                    "model_number": p.get("model_number", ""),
                    "specification": p.get("specification", ""),
                    "unit": p.get("unit", ""),
                    "price": p.get("price"),
                })

            return {"data": {"products": stock_items}}
        except Exception as e:
            logger.warning(f"[StockQueryTool] 产品库存查询异常: {e}")
            return {"data": {"products": []}}

    async def _query_material_stock(self, search: str) -> dict:
        try:
            import httpx

            params = {}
            if search:
                params["search"] = search

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "http://127.0.0.1:8000/api/materials",
                    params=params
                )

                if response.status_code == 200:
                    result = response.json()
                    materials = result.get("data", [])

                    stock_items = []
                    for m in materials:
                        stock_items.append({
                            "type": "material",
                            "name": m.get("name", ""),
                            "code": m.get("code", ""),
                            "category": m.get("category", ""),
                            "spec": m.get("spec", ""),
                            "quantity": m.get("quantity", 0),
                            "unit": m.get("unit", ""),
                            "min_stock": m.get("min_stock"),
                            "max_stock": m.get("max_stock"),
                        })

                    return {"data": {"materials": stock_items}}
                else:
                    return {"data": {"materials": []}}

        except Exception as e:
            logger.warning(f"[StockQueryTool] 原材料库存查询异常: {e}")
            return {"data": {"materials": []}}
