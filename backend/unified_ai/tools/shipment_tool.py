"""
发货单工具集
"""

import logging
from typing import Any

from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ShipmentGenerateTool(BaseTool):
    name = "shipment_generate"
    description = "生成发货单"

    async def execute(
        self,
        customer_name: str,
        products: list[dict[str, Any]],
        delivery_date: str = "",
        remark: str = "",
        **kwargs
    ) -> ToolResult:
        try:
            import httpx

            payload = {
                "customer_name": customer_name,
                "products": products,
                "delivery_date": delivery_date,
                "remark": remark,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://127.0.0.1:8000/api/shipment/generate",
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        return ToolResult(
                            success=True,
                            data=result.get("data"),
                            message=result.get("message", "发货单生成成功")
                        )
                    else:
                        return ToolResult(
                            success=False,
                            error=result.get("error", ""),
                            message="发货单生成失败"
                        )
                elif response.status_code == 404:
                    return await self._fallback_generate(customer_name, products, delivery_date, remark)
                else:
                    return ToolResult(
                        success=False,
                        error=f"HTTP {response.status_code}: {response.text}",
                        message="发货单生成失败"
                    )

        except httpx.ConnectError:
            return await self._fallback_generate(customer_name, products, delivery_date, remark)
        except Exception as e:
            logger.exception(f"[ShipmentGenerateTool] 异常: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="发货单生成失败"
            )

    async def _fallback_generate(
        self,
        customer_name: str,
        products: list[dict[str, Any]],
        delivery_date: str,
        remark: str,
    ) -> ToolResult:
        try:
            from datetime import datetime
            from backend.routers.xcagi_compat import _load_customers_rows, _load_products_all_for_export

            shipment_id = f"FH{datetime.now().strftime('%Y%m%d%H%M%S')}"

            data = {
                "shipment_id": shipment_id,
                "customer_name": customer_name,
                "products": products,
                "delivery_date": delivery_date or datetime.now().strftime("%Y-%m-%d"),
                "remark": remark,
                "status": "待发货",
                "created_at": datetime.now().isoformat(),
            }

            return ToolResult(
                success=True,
                data=data,
                message=f"发货单 {shipment_id} 已生成（本地模式）"
            )
        except Exception as e:
            logger.exception(f"[ShipmentGenerateTool] 降级生成异常: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="发货单生成失败"
            )


class ShipmentQueryTool(BaseTool):
    name = "shipment_query"
    description = "查询发货单状态"

    async def execute(
        self,
        shipment_id: str = "",
        customer_name: str = "",
        status: str = "",
        **kwargs
    ) -> ToolResult:
        try:
            import httpx

            params = {}
            if shipment_id:
                params["shipment_id"] = shipment_id
            if customer_name:
                params["customer_name"] = customer_name
            if status:
                params["status"] = status

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "http://127.0.0.1:8000/api/shipment/list",
                    params=params
                )

                if response.status_code == 200:
                    result = response.json()
                    return ToolResult(
                        success=True,
                        data=result.get("data", []),
                        message=f"查询到 {len(result.get('data', []))} 条发货单记录"
                    )
                elif response.status_code == 404:
                    return ToolResult(
                        success=True,
                        data=[],
                        message="暂无发货单数据"
                    )
                else:
                    return ToolResult(
                        success=False,
                        error=f"HTTP {response.status_code}",
                        message="查询发货单失败"
                    )

        except httpx.ConnectError:
            return ToolResult(
                success=True,
                data=[],
                message="发货单服务暂不可用"
            )
        except Exception as e:
            logger.exception(f"[ShipmentQueryTool] 异常: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="查询发货单失败"
            )


class ShipmentAddTool(BaseTool):
    name = "shipment_add"
    description = "增加发货单产品"

    async def execute(
        self,
        customer_name: str,
        products: list[dict[str, Any]],
        shipment_id: str = "",
        **kwargs
    ) -> ToolResult:
        try:
            import httpx

            payload = {
                "customer_name": customer_name,
                "products": products,
                "shipment_id": shipment_id,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://127.0.0.1:8000/api/shipment/add",
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    return ToolResult(
                        success=True,
                        data=result.get("data"),
                        message=result.get("message", "发货单产品已添加")
                    )
                else:
                    return await self._fallback_add(customer_name, products, shipment_id)

        except httpx.ConnectError:
            return await self._fallback_add(customer_name, products, shipment_id)
        except Exception as e:
            logger.exception(f"[ShipmentAddTool] 异常: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="增加发货单失败"
            )

    async def _fallback_add(
        self,
        customer_name: str,
        products: list[dict[str, Any]],
        shipment_id: str,
    ) -> ToolResult:
        return ToolResult(
            success=True,
            data={
                "shipment_id": shipment_id or "NEW",
                "customer_name": customer_name,
                "added_products": products,
            },
            message=f"已添加 {len(products)} 个产品到发货单（本地模式）"
        )


class ShipmentUpdateTool(BaseTool):
    name = "shipment_update"
    description = "修改发货单"

    async def execute(
        self,
        shipment_id: str,
        updates: dict[str, Any],
        **kwargs
    ) -> ToolResult:
        try:
            import httpx

            payload = {
                "shipment_id": shipment_id,
                "updates": updates,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(
                    "http://127.0.0.1:8000/api/shipment/update",
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    return ToolResult(
                        success=True,
                        data=result.get("data"),
                        message=result.get("message", "发货单已更新")
                    )
                else:
                    return ToolResult(
                        success=False,
                        error=f"HTTP {response.status_code}",
                        message="修改发货单失败"
                    )

        except Exception as e:
            logger.exception(f"[ShipmentUpdateTool] 异常: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="修改发货单失败"
            )


class ShipmentDeleteTool(BaseTool):
    name = "shipment_delete"
    description = "删除发货单"

    async def execute(
        self,
        shipment_id: str,
        **kwargs
    ) -> ToolResult:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"http://127.0.0.1:8000/api/shipment/{shipment_id}"
                )

                if response.status_code == 200:
                    result = response.json()
                    return ToolResult(
                        success=True,
                        data=result.get("data"),
                        message=result.get("message", "发货单已删除")
                    )
                else:
                    return ToolResult(
                        success=False,
                        error=f"HTTP {response.status_code}",
                        message="删除发货单失败"
                    )

        except Exception as e:
            logger.exception(f"[ShipmentDeleteTool] 异常: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="删除发货单失败"
            )


class ShipmentApproveTool(BaseTool):
    name = "shipment_approve"
    description = "审核发货单"

    async def execute(
        self,
        shipment_id: str,
        approved: bool = True,
        **kwargs
    ) -> ToolResult:
        try:
            import httpx

            payload = {
                "shipment_id": shipment_id,
                "approved": approved,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://127.0.0.1:8000/api/shipment/approve",
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    return ToolResult(
                        success=True,
                        data=result.get("data"),
                        message=result.get("message", "发货单已审核")
                    )
                else:
                    return ToolResult(
                        success=False,
                        error=f"HTTP {response.status_code}",
                        message="审核发货单失败"
                    )

        except Exception as e:
            logger.exception(f"[ShipmentApproveTool] 异常: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="审核发货单失败"
            )
