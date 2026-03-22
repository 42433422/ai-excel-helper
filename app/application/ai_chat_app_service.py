# -*- coding: utf-8 -*-
"""
AI 聊天应用服务

编排 AI 聊天业务逻辑：
- 处理即时工具执行（products/customers/shipments/shipment_generate）
- 构建统一响应格式
- 处理确认流程
"""

import asyncio
import logging
import re
from typing import Any, Dict, Optional

from app.services import get_ai_conversation_service

logger = logging.getLogger(__name__)


class AIChatApplicationService:
    """
    AI 聊天应用服务

    编排 AI 对话和即时工具执行，负责：
    - 聊天主流程处理
    - 即时工具执行（source=pro 和普通模式）
    - 响应格式构建
    """

    def __init__(self):
        self.ai_service = get_ai_conversation_service()

    def process_chat(
        self,
        user_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        file_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理聊天请求

        Args:
            user_id: 用户 ID
            message: 用户消息
            context: 额外上下文
            source: 来源标识（pro 表示专业模式）
            file_context: 文件上下文（用于确认流程）

        Returns:
            处理结果字典
        """
        if not message:
            return {
                "success": False,
                "message": "消息内容不能为空",
            }

        self._handle_confirmation_flow(user_id, message, file_context)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            ai_result = loop.run_until_complete(
                self.ai_service.chat(user_id, message, context or {})
            )
        finally:
            loop.close()

        logger.info(f"用户 {user_id} 消息：{message[:50]}... -> {ai_result.get('action', 'unknown')}")

        response_data = self._build_response(ai_result, source, message)

        return response_data

    def _handle_confirmation_flow(
        self,
        user_id: str,
        message: str,
        file_context: Optional[Dict[str, Any]]
    ) -> None:
        """处理确认流程"""
        if not file_context:
            return

        if message not in ("是", "好的", "确认", "yes", "ok", "好"):
            return

        saved_name = file_context.get("saved_name")
        unit_name = file_context.get("unit_name_guess") or file_context.get("unit_name", "")
        suggested_use = file_context.get("suggested_use", "")

        if saved_name and suggested_use == "unit_products_db" and unit_name:
            self.ai_service.set_pending_confirmation(user_id, {
                "type": "import_unit_products",
                "tool_key": "sqlite_import_unit_products",
                "params": {
                    "saved_name": saved_name,
                    "unit_name": unit_name,
                },
                "description": f"导入 {unit_name} 的产品"
            })
            logger.info(f"用户 {user_id} 确认导入文件：{saved_name} -> {unit_name}")

    def _build_response(
        self,
        ai_result: Dict[str, Any],
        source: Optional[str],
        original_message: str = ""
    ) -> Dict[str, Any]:
        """构建响应数据"""
        response_data = {
            "success": True,
            "message": "处理完成",
            "data": {
                "text": ai_result.get("text", ""),
                "action": ai_result.get("action", ""),
                "data": ai_result.get("data", {}) or {},
            },
        }
        response_data["response"] = ai_result.get("text", "")

        action = ai_result.get("action")
        result_data = ai_result.get("data") or {}

        if action == "tool_call" and result_data:
            response_data = self._handle_tool_call(
                response_data, ai_result, result_data, source, original_message
            )
        else:
            if action == "followup":
                response_data["followup"] = result_data
            if action == "auto_action" and result_data:
                response_data["autoAction"] = result_data

        return response_data

    def _handle_tool_call(
        self,
        response_data: Dict[str, Any],
        ai_result: Dict[str, Any],
        result_data: Dict[str, Any],
        source: Optional[str],
        original_message: str = ""
    ) -> Dict[str, Any]:
        """处理工具调用响应"""
        tool_key = result_data.get("tool_key")
        parsed_params = result_data.get("params") or {}
        slots = result_data.get("slots", {})

        if not tool_key:
            response_data["response"] = ai_result.get("text", "")
            response_data["data"]["data"] = result_data.get("data", {}) or {}
            return response_data

        if source == "pro":
            response_data = self._execute_pro_mode_tools(
                response_data, tool_key, slots, parsed_params, ai_result, original_message
            )
        else:
            response_data = self._execute_normal_mode_tools(
                response_data, tool_key, parsed_params, ai_result, result_data
            )

        return response_data

    def _execute_pro_mode_tools(
        self,
        response_data: Dict[str, Any],
        tool_key: str,
        slots: Dict[str, Any],
        parsed_params: Dict[str, Any],
        ai_result: Dict[str, Any],
        original_message: str = ""
    ) -> Dict[str, Any]:
        """执行专业模式工具"""
        if tool_key == "products":
            return self._execute_products_query(
                response_data, slots, parsed_params
            )
        elif tool_key == "customers":
            return self._execute_customers_query(response_data)
        elif tool_key == "shipment_generate":
            unit_name = slots.get("unit_name") or parsed_params.get("unit_name", "")
            quantity_tins = slots.get("quantity_tins") or parsed_params.get("quantity_tins", "")
            model_number = slots.get("model_number") or slots.get("product_model") or parsed_params.get("model_number", "")
            tin_spec = slots.get("tin_spec") or parsed_params.get("tin_spec", "")
            products_list = slots.get("products") or []

            if original_message and len(original_message) > 5:
                order_text = original_message
            elif unit_name and quantity_tins and model_number and tin_spec:
                order_text = f"{unit_name}{int(quantity_tins)} 桶 {model_number} 规格 {int(float(tin_spec))}"
            elif unit_name and products_list:
                order_text = self._build_order_text_from_products(unit_name, products_list, original_message, quantity_tins, tin_spec)
            else:
                order_text = ai_result.get("text", "")
            response_data["toolCall"] = {
                "tool_id": tool_key,
                "action": "执行",
                "params": {
                    "order_text": order_text,
                    **parsed_params,
                    **ai_result.get("data", {})
                }
            }
            response_data["response"] = ai_result.get("text", "")
            return response_data
        else:
            response_data["toolCall"] = {
                "tool_id": tool_key,
                "action": "执行",
                "params": {
                    "order_text": ai_result.get("text", ""),
                    **parsed_params,
                    **ai_result.get("data", {})
                }
            }
            response_data["response"] = ai_result.get("text", "")
            return response_data

    def _execute_normal_mode_tools(
        self,
        response_data: Dict[str, Any],
        tool_key: str,
        parsed_params: Dict[str, Any],
        ai_result: Dict[str, Any],
        result_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行普通模式工具"""
        if tool_key == "shipment_generate":
            return self._execute_shipment_generate(
                response_data, parsed_params, ai_result
            )
        elif tool_key == "shipments":
            return self._execute_shipments_query(response_data)
        else:
            response_data["toolCall"] = {
                "tool_id": tool_key,
                "action": "执行",
                "params": {
                    "order_text": ai_result.get("text", ""),
                    **parsed_params,
                    **result_data
                }
            }
            response_data["response"] = ai_result.get("text", "")
            return response_data

    def _execute_products_query(
        self,
        response_data: Dict[str, Any],
        slots: Dict[str, Any],
        parsed_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行产品查询"""
        try:
            from app.bootstrap import get_products_service
            from app.infrastructure.lookups.purchase_unit_resolver import resolve_purchase_unit

            unit_name = slots.get("unit_name") or parsed_params.get("unit_name", "")
            model_number = slots.get("model_number") or parsed_params.get("model_number", "")
            keyword = slots.get("keyword") or parsed_params.get("keyword", "")

            if not unit_name and not model_number and keyword and "的" in keyword:
                match = re.search(r'([\u4e00-\u9fa5]{2,6})的(\d+[A-Z]?)', keyword)
                if match:
                    potential_unit = match.group(1)
                    model_candidate = match.group(2)
                    resolved = resolve_purchase_unit(potential_unit)
                    if resolved:
                        unit_name = resolved.unit_name
                    else:
                        unit_name = potential_unit
                    model_number = model_candidate
                    keyword = None

            app_service = get_products_service()

            if model_number and unit_name:
                products_result = app_service.get_products(model_number=model_number, unit_name=unit_name)
            elif model_number:
                products_result = app_service.get_products(model_number=model_number)
            elif unit_name:
                products_result = app_service.get_products(unit_name=unit_name)
            elif keyword:
                products_result = app_service.get_products(keyword=keyword)
            else:
                products_result = app_service.get_products()

            products_list = products_result.get("data", []) if products_result else []

            response_data["data"]["unit_name"] = unit_name
            response_data["data"]["model_number"] = model_number
            response_data["data"]["data"] = {"products": products_list}
            response_data["response"] = f"查询到 {len(products_list)} 个产品" if products_list else "未找到产品"
            response_data["toolCall"] = {
                "tool_id": "products",
                "action": "执行",
                "params": {
                    "unit_name": unit_name,
                    "model_number": model_number,
                    "keyword": keyword
                }
            }
            response_data["autoAction"] = {
                "type": "tool_call",
                "tool_key": "products",
                "params": {
                    "unit_name": unit_name,
                    "model_number": model_number,
                    "keyword": keyword
                },
                "products": products_list,
                "unit_name": unit_name,
                "query": model_number or keyword or ""
            }
        except Exception as prod_err:
            logger.error("即时执行 products 查询失败: %s", prod_err, exc_info=True)
            response_data["response"] = f"查询产品失败：{str(prod_err)}"

        return response_data

    def _execute_customers_query(
        self,
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行客户查询"""
        try:
            from app.bootstrap import get_customer_app_service

            app_service = get_customer_app_service()
            customers_result = app_service.get_all()
            customers = customers_result.get("data", []) if customers_result else []

            response_data["data"]["data"] = {"customers": customers}
            response_data["response"] = f"查询到 {len(customers)} 个购买单位" if customers else "未找到购买单位"
        except Exception as cust_err:
            logger.error("即时执行 customers 查询失败: %s", cust_err, exc_info=True)
            response_data["response"] = f"查询购买单位失败：{str(cust_err)}"

        return response_data

    def _build_order_text_from_products(self, unit_name: str, products: list, original_message: str = "", default_qty: int = None, default_spec: int = None) -> str:
        """根据产品列表构建订单文本"""
        import re
        if not products:
            return ""
        if not unit_name:
            return ""

        if original_message and len(products) >= 1:
            normalized_msg = original_message.replace('，', ',').replace('。', '').replace(' ', '')
            order_pattern = re.compile(r'帮?打\s*(.+?)\s*的?\s*货单?[,，]?\s*(\d+)\s*桶\s*(\d+[A-Z]?(?:-\d+[A-Z]?)?)\s*规格\s*(\d+)\s*[,，]?\s*(\d+)\s*桶\s*(\d+[A-Z]?(?:-\d+[A-Z]?)?)\s*规格\s*(\d+)')
            matches = list(order_pattern.finditer(normalized_msg))

            if len(matches) >= 1:
                m = matches[0]
                found_unit = m.group(1)
                if len(m.groups()) >= 7:
                    order_parts = []
                    for i in range(1, len(m.groups()), 4):
                        if i + 3 <= len(m.groups()):
                            qty = int(m.group(i + 1))
                            model = m.group(i + 2)
                            spec = int(m.group(i + 3))
                            order_parts.append(f"{qty}桶{model}规格{spec}")
                    if order_parts and found_unit:
                        return found_unit + "，" + "，".join(order_parts)
                else:
                    order_parts = []
                    for m in matches:
                        qty = int(m.group(2))
                        model = m.group(3)
                        spec = int(m.group(4))
                        order_parts.append(f"{qty}桶{model}规格{spec}")
                    if order_parts and found_unit:
                        return found_unit + "，" + "，".join(order_parts)

        parts = []
        total_qty = default_qty or 0
        for p in products:
            model = p.get("model") or p.get("model_number") or p.get("name") or ""
            qty = p.get("quantity_tins") or p.get("quantity") or p.get("qty") or 1
            spec = p.get("spec") or p.get("tin_spec") or p.get("规格") or default_spec or 25
            if model:
                parts.append(f"{int(qty)}桶{model}规格{int(float(spec))}")
            else:
                parts.append(f"{int(qty)}桶规格{int(float(spec))}")
        return unit_name + "，" + "，".join(parts)

    def _try_merge_split_model(self, text: str, product_template: dict) -> str:
        """尝试合并被拆分的型号（如 5003-2737B 被拆成 5003 和 2737B）"""
        import re
        qty = product_template.get("quantity_tins") or 1
        spec = product_template.get("spec") or product_template.get("tin_spec") or 25

        number_pattern = r'(\d+)([A-Z]?)\s*规格\s*(\d+)'
        m = re.search(number_pattern, text)
        if m:
            model = m.group(1) + m.group(2)
            spec_val = int(m.group(3))
            return f"{int(qty)}桶{model}规格{spec_val}"

        number_pattern2 = r'(\d+)\s*桶\s*(\d+)([A-Z]?)\s*规格\s*(\d+)'
        m2 = re.search(number_pattern2, text)
        if m2:
            qty_val = int(m2.group(1))
            model = m2.group(2) + m2.group(3)
            spec_val = int(m2.group(4))
            return f"{qty_val}桶{model}规格{spec_val}"

        return ""

    def _execute_shipment_generate(
        self,
        response_data: Dict[str, Any],
        parsed_params: Dict[str, Any],
        ai_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行发货单生成"""
        try:
            from app.bootstrap import get_shipment_app_service
            from app.routes.tools import _parse_order_text

            order_text = parsed_params.get("order_text") or ai_result.get("text", "")
            parsed = _parse_order_text(order_text)

            if parsed.get("success"):
                app_service = get_shipment_app_service()
                doc_result = app_service.generate_shipment_document(
                    unit_name=parsed.get("unit_name", ""),
                    products=parsed.get("products") or [],
                    template_name=None,
                )
                response_data["data"]["data"] = {"document": doc_result}

                if doc_result.get("success"):
                    doc_name = doc_result.get("doc_name") or ""
                    response_data["response"] = f"已生成发货单：{doc_name}" if doc_name else "已生成发货单。"
                else:
                    response_data["response"] = doc_result.get("message", "生成发货单失败")
            else:
                response_data["response"] = parsed.get("message", "订单解析失败")
        except Exception as tool_err:
            logger.error("自动执行 shipment_generate 失败: %s", tool_err, exc_info=True)
            response_data["response"] = f"生成发货单失败：{str(tool_err)}"

        return response_data

    def _execute_shipments_query(
        self,
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行发货记录查询"""
        try:
            from app.bootstrap import get_shipment_app_service

            app_service = get_shipment_app_service()
            orders = app_service.get_orders(10) or []

            lines = ["最新出货/订单记录（最近 10 条）："]
            if not orders:
                lines.append("暂无订单记录。")
            else:
                for o in orders[:10]:
                    order_no = o.get("order_number") or o.get("order_no") or o.get("id") or ""
                    customer = o.get("customer_name") or o.get("unit_name") or o.get("purchase_unit") or ""
                    date = o.get("date") or o.get("created_at") or ""
                    amount = o.get("total_amount") or o.get("total_amount_yuan") or o.get("amount") or 0
                    status = o.get("status") or "已完成"
                    lines.append(f"- {order_no} | {customer} | {date} | ¥{amount} | {status}")

            response_data["response"] = "\n".join(lines)
            response_data["data"]["data"] = {"orders": orders}
            response_data.pop("toolCall", None)
        except Exception as tool_err:
            logger.error("即时执行 shipments 失败：%s", tool_err, exc_info=True)

        return response_data


_ai_chat_app_service_instance = None


def get_ai_chat_app_service() -> AIChatApplicationService:
    """获取 AI 聊天应用服务单例"""
    global _ai_chat_app_service_instance
    if _ai_chat_app_service_instance is None:
        _ai_chat_app_service_instance = AIChatApplicationService()
    return _ai_chat_app_service_instance
