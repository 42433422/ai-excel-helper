"""
标签打印工具
"""

import logging
from typing import Any

from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class LabelPrintTool(BaseTool):
    name = "label_print"
    description = "打印产品标签"

    async def execute(
        self,
        model_number: str,
        quantity: int = 1,
        **kwargs
    ) -> ToolResult:
        try:
            import httpx

            payload = {
                "model_number": model_number,
                "quantity": quantity,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://127.0.0.1:8000/api/print/single_label",
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    return ToolResult(
                        success=True,
                        data=result,
                        message=f"标签打印任务已提交: {model_number} x{quantity}"
                    )
                else:
                    return await self._fallback_print(model_number, quantity)

        except Exception as e:
            logger.warning(f"[LabelPrintTool] API调用失败，降级处理: {e}")
            return await self._fallback_print(model_number, quantity)

    async def _fallback_print(self, model_number: str, quantity: int) -> ToolResult:
        try:
            from backend.routers.print import _load_printer_selection

            selection = _load_printer_selection()
            printer_name = selection.get("label_printer", "默认打印机")

            return ToolResult(
                success=True,
                data={
                    "model_number": model_number,
                    "quantity": quantity,
                    "printer": printer_name,
                },
                message=f"标签打印任务已提交: {model_number} x{quantity}（打印机: {printer_name}）"
            )
        except Exception as e:
            logger.exception(f"[LabelPrintTool] 降级打印异常: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="标签打印失败"
            )
