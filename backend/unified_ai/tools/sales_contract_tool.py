"""
销售合同生成工具 - 集成到统一 AI 架构
"""

import logging
from typing import Any

from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class SalesContractGenerateTool(BaseTool):
    name = "sales_contract_generate"
    description = "生成销售合同 Excel（.xlsx，送货单版式；与 /api/sales-contract/generate 一致）"

    async def execute(
        self,
        customer_name: str,
        products: list[dict[str, Any]],
        contract_date: str = "",
        customer_phone: str = "",
        template_id: str = "",
        **kwargs
    ) -> ToolResult:
        """
        执行销售合同生成
        
        Args:
            customer_name: 客户名称
            products: 产品列表，每项包含 model_number, quantity 等
            contract_date: 合同日期（可选）
            customer_phone: 客户电话（可选）
        """
        try:
            import httpx

            um = str(kwargs.get("_user_message") or "").strip()
            if um:
                from backend.sales_contract_intent_bridge import merge_planner_sales_contract_args

                merged = merge_planner_sales_contract_args(
                    {"customer_name": customer_name, "products": list(products or [])},
                    um,
                )
                customer_name = str(merged.get("customer_name") or customer_name)
                products = merged.get("products", products)

            payload: dict[str, Any] = {
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "contract_date": contract_date,
                "products": products,
            }
            tid = (template_id or "").strip()
            if tid:
                payload["template_id"] = tid
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://127.0.0.1:8000/api/sales-contract/generate",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        data = result.get("data", {})
                        products = data.get("products", [])
                        display_customer = (
                            str(data.get("customer_name") or "").strip() or customer_name
                        )

                        table_html = self._generate_products_table(products)

                        message = f"客户：{display_customer}\n{table_html}"
                        
                        return ToolResult(
                            success=True,
                            data=data,
                            message=message
                        )
                    else:
                        return ToolResult(
                            success=False,
                            error=result.get("error", ""),
                            message="销售合同生成失败"
                        )
                else:
                    return ToolResult(
                        success=False,
                        error=f"HTTP {response.status_code}: {response.text}",
                        message="销售合同生成失败"
                    )
                    
        except Exception as e:
            logger.exception(f"[SalesContractGenerateTool] 生成异常：{e}")
            return ToolResult(
                success=False,
                error=str(e),
                message="销售合同生成失败"
            )

    def validate_input(self, **kwargs) -> tuple[bool, str]:
        if not kwargs.get("customer_name"):
            return False, "客户名称不能为空"
        if not kwargs.get("products"):
            return False, "产品列表不能为空"
        return True, ""

    def _generate_products_table(self, products: list[dict[str, Any]]) -> str:
        """生成产品表格 HTML"""
        if not products:
            return "产品：无"
        
        total_amount = 0.0
        rows = []
        for p in products:
            model = p.get("model_number", "")
            name = p.get("name", "")
            spec = p.get("specification", "")
            qty = float(p.get("quantity", 0))
            price = float(p.get("unit_price", 0))
            amount = float(p.get("amount", 0)) or (qty * price)
            total_amount += amount
            
            rows.append(
                f'<tr><td>{model}</td><td>{name}</td><td>{spec}</td>'
                f'<td>{int(qty)}</td><td>{price:.2f}</td><td>{amount:.2f}</td></tr>'
            )
        
        table_html = (
            '<table style="border-collapse: collapse; width: 100%; margin: 8px 0;">'
            '<thead><tr style="background: #f5f5f5;">'
            '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">型号</th>'
            '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">名称</th>'
            '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">规格</th>'
            '<th style="border: 1px solid #ddd; padding: 8px; text-align: center;">数量</th>'
            '<th style="border: 1px solid #ddd; padding: 8px; text-align: right;">单价</th>'
            '<th style="border: 1px solid #ddd; padding: 8px; text-align: right;">金额</th>'
            '</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody>'
            f'<tfoot><tr style="background: #f9f9f9; font-weight: bold;">'
            f'<td colspan="5" style="border: 1px solid #ddd; padding: 8px; text-align: right;">合计：</td>'
            f'<td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{total_amount:.2f}元</td>'
            f'</tr></tfoot>'
            '</table>'
        )
        
        return table_html
