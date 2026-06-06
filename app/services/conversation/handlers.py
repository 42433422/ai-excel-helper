import logging
from typing import Any

from app.services.conversation.context import ConversationContext

logger = logging.getLogger(__name__)


class HandlersMixin:

    async def _handle_special_intents(
        self,
        message: str,
        intent_result: dict[str, Any],
        conv_context: ConversationContext,
        user_id: str,
    ) -> dict[str, Any] | None:
        if result := await self._handle_confirmation_intent(
            message, intent_result, conv_context, user_id
        ):
            return result

        if result := await self._handle_negation_intent(
            message, intent_result, conv_context, user_id
        ):
            return result

        if intent_result.get("is_greeting"):
            return await self._handle_greeting(message, conv_context)

        if intent_result.get("is_goodbye"):
            return await self._handle_goodbye(message, conv_context)

        if intent_result.get("is_help"):
            return await self._handle_help(message, conv_context)

        hard_rule_result = self._check_hard_rules(message)
        if hard_rule_result:
            return hard_rule_result

        return None

    async def _handle_confirmation_intent(
        self,
        message: str,
        intent_result: dict[str, Any],
        conv_context: ConversationContext,
        user_id: str,
    ) -> dict[str, Any] | None:
        if not intent_result.get("is_confirmation"):
            return None

        confirmation_pending = (
            conv_context.pending_confirmation
            or self.confirmation_service.get_pending_intent(user_id)
        )
        if not confirmation_pending:
            return None

        pending = confirmation_pending
        action_type = pending.get("type", pending.get("intent", ""))
        tool_key = pending.get("tool_key", pending.get("intent"))
        params = pending.get("params", pending.get("slots", {}))
        conv_context.last_action = f"confirmed_{action_type}"

        self.add_intent_feedback(
            user_id=user_id,
            message=message,
            recognized_intent=pending.get("intent", action_type),
            feedback="confirmed",
            slots=params,
        )

        self.record_user_action(
            user_id=user_id,
            intent=pending.get("intent", action_type),
            slots=params,
            message=message,
        )

        conv_context.pending_confirmation = None
        self.confirmation_service.clear_pending_intent(user_id)

        if tool_key:
            return {
                "text": f"好的，正在执行【{action_type}】...",
                "action": "tool_call",
                "data": {
                    "tool_key": tool_key,
                    "intent": "confirmation_executed",
                    "params": params,
                    "from_pending_confirmation": True,
                },
            }

        return None

    async def _handle_negation_intent(
        self,
        message: str,
        intent_result: dict[str, Any],
        conv_context: ConversationContext,
        user_id: str,
    ) -> dict[str, Any] | None:
        if intent_result.get("is_negated") and conv_context.pending_confirmation:
            pending_intent = conv_context.pending_confirmation.get("intent", "")
            self.add_intent_feedback(
                user_id=user_id,
                message=message,
                recognized_intent=pending_intent,
                feedback="negated",
                slots=conv_context.pending_confirmation.get("slots", {}),
            )
            conv_context.pending_confirmation = None
            return None

        if (
            intent_result.get("is_negation_intent")
            and not conv_context.pending_confirmation
            and len(message) < 10
        ):
            conv_context.last_action = "user_negated"
            self.add_intent_feedback(
                user_id=user_id,
                message=message,
                recognized_intent=conv_context.current_intent or "",
                feedback="negated",
                slots=(
                    conv_context.last_intent_result.get("slots", {})
                    if conv_context.last_intent_result
                    else {}
                ),
            )
            return {"text": "好的，已取消。有其他需要帮助的吗？", "action": "negated", "data": {}}

        return None

    async def _handle_pending_intent(
        self,
        message: str,
        intent_result: dict[str, Any],
        conv_context: ConversationContext,
        user_id: str,
    ) -> dict[str, Any] | None:
        pending = self.confirmation_service.get_pending_intent(user_id)
        if not pending:
            return None

        current_tool_key = intent_result.get("tool_key")

        if pending and (
            intent_result.get("is_greeting")
            or intent_result.get("is_goodbye")
            or intent_result.get("is_help")
        ):
            logger.info("[DEBUG_PENDING] 检测到特殊意图，清除 pending")
            self.confirmation_service.clear_pending_intent(user_id)
            return None

        if current_tool_key and current_tool_key != pending.get("intent"):
            pending_intent = pending.get("intent")
            if pending_intent not in (current_tool_key, intent_result.get("primary_intent")):
                logger.info(
                    f"[DEBUG_PENDING] 检测到新意图 {current_tool_key} 与 pending 意图 {pending_intent} 不同，清除 pending"
                )
                self.confirmation_service.clear_pending_intent(user_id)
                return None

        return await self._fill_pending_slots(message, pending, user_id)

    async def _fill_pending_slots(
        self, message: str, pending: dict[str, Any], user_id: str
    ) -> dict[str, Any]:
        logger.info("[DEBUG_PENDING] 检测到 pending 意图存在，将使用本地规则提取槽位")
        local_result = self.intent_service(message)
        new_slots = local_result.get("slots", {})
        logger.info(f"[DEBUG_PENDING] 本地提取的 slots: {new_slots}")
        merged_slots = self.confirmation_service.merge_slots(user_id, new_slots)
        logger.info(f"[DEBUG_PENDING] 合并后的 slots: {merged_slots}")

        check_result = self.confirmation_service.check_and_build_prompt(
            {
                "final_intent": pending.get("intent"),
                "slots": merged_slots,
            }
        )
        logger.info(
            f"[DEBUG_PENDING] check_result status: {check_result.get('status')}, missing: {check_result.get('missing_slots')}"
        )

        if check_result["status"] == "complete":
            return self._build_pending_complete_response(pending, merged_slots, user_id)
        else:
            return self._build_pending_incomplete_response(
                pending, merged_slots, check_result, user_id
            )

    def _build_pending_complete_response(
        self, pending: dict[str, Any], merged_slots: dict[str, Any], user_id: str
    ) -> dict[str, Any]:
        pending_intent = pending.get("intent", "")
        action_texts = {
            "shipment_generate": f"正在为 {merged_slots.get('unit_name', '该客户')} 生成发货单",
            "products": f"正在查询 {merged_slots.get('unit_name', merged_slots.get('keyword', '该产品'))} 的产品信息",
            "customers": "正在查询客户信息",
            "shipments": "正在查询发货记录",
            "print_label": "正在处理标签打印",
            "wechat_send": "正在发送微信消息",
            "upload_file": "正在上传文件",
        }
        action_text = action_texts.get(pending_intent, f"正在处理 {pending_intent}")
        self.confirmation_service.set_pending_intent(
            user_id,
            {
                "intent": pending.get("intent"),
                "slots": merged_slots,
                "missing_slots": [],
            },
        )
        return {
            "text": f"好的，已收到您的信息，{action_text}...",
            "action": "tool_call",
            "data": {
                "tool_key": pending.get("intent"),
                "intent": pending.get("intent"),
                "slots": merged_slots,
            },
        }

    def _build_pending_incomplete_response(
        self,
        pending: dict[str, Any],
        merged_slots: dict[str, Any],
        check_result: dict[str, Any],
        user_id: str,
    ) -> dict[str, Any]:
        self.confirmation_service.set_pending_intent(
            user_id,
            {
                "intent": pending.get("intent"),
                "slots": merged_slots,
                "missing_slots": check_result["missing_slots"],
            },
        )
        return {
            "text": check_result["question"],
            "action": "slot_fill",
            "data": {
                "intent": pending.get("intent"),
                "slots": merged_slots,
                "missing_slots": check_result["missing_slots"],
            },
        }

    async def _handle_greeting(self, message: str, context: ConversationContext) -> dict[str, Any]:
        responses = [
            "您好！我是 XCAGI 智能助手，很高兴为您服务！😊\n\n我可以帮您：\n• 生成发货单\n• 管理产品和客户\n• 处理订单\n• 回答各种问题\n\n请问有什么可以帮您？",
            "你好呀！😊 我是您的智能助手，随时准备帮助您处理业务问题。\n\n需要我帮您做什么呢？",
            "您好！欢迎使用 XCAGI 系统！\n\n我可以协助您处理日常业务，比如开单、查询产品、管理客户等。\n\n今天需要我帮您做什么？",
        ]

        response_text = responses[hash(message) % len(responses)]

        self.add_to_history(context.user_id, "user", message)
        self.add_to_history(context.user_id, "assistant", response_text)

        return {"text": response_text, "action": "greeting", "data": {}}

    async def _handle_goodbye(self, message: str, context: ConversationContext) -> dict[str, Any]:
        responses = [
            "再见！祝您工作顺利！👋 如有需要，随时联系我。",
            "好的，再见！😊 期待下次为您服务！",
            "拜拜！😄 有任何问题都可以随时找我哦！",
        ]

        response_text = responses[hash(message) % len(responses)]

        self.add_to_history(context.user_id, "user", message)
        self.add_to_history(context.user_id, "assistant", response_text)

        return {"text": response_text, "action": "goodbye", "data": {}}

    async def _handle_help(self, message: str, context: ConversationContext) -> dict[str, Any]:
        help_text = """🆘 XCAGI 智能助手功能介绍

📦 **发货单管理**
• 生成发货单：说"生成发货单"或"开单"
• 查看发货单模板：问"发货单模板"或"当前模板"

📊 **数据查询**
• 产品查询：问"产品列表"或"产品库"
• 客户查询：问"客户列表"或"购买单位"
• 出货记录：问"出货记录"或"订单列表"
• 库存查询：问"原材料库存"或"材料库"

📁 **文件处理**
• 上传文件：说"上传 excel"或"导入文件"
• 分解模板：说"分解 excel"或"提取词条"
• 打印标签：说"打印标签"或"标签导出"

💡 **使用提示**
• 直接说出您的需求，我会智能识别
• 可以说"不要..."来取消某个操作
• 支持自然语言对话，无需记忆命令

需要我详细介绍某个功能吗？"""

        self.add_to_history(context.user_id, "user", message)
        self.add_to_history(context.user_id, "assistant", help_text)

        return {"text": help_text, "action": "help", "data": {}}

    def _check_hard_rules(self, message: str) -> dict[str, Any] | None:
        msg = message.strip()
        msg_lower = msg.lower()

        export_keywords = [
            "导出excel",
            "导出xlsx",
            "导出表格",
            "导出用户列表",
            "导出客户列表",
            "导出购买单位",
            "导出单位",
        ]
        export_context_keywords = ["用户", "客户", "购买单位", "单位", "名单", "列表"]
        export_hit = any(k in msg_lower for k in export_keywords)
        export_with_context = ("导出" in msg) and any(k in msg for k in export_context_keywords)

        if export_hit or export_with_context:
            return {
                "text": "已开始导出购买单位列表为 XLSX，下载将自动开始。",
                "action": "auto_action",
                "data": {"type": "export_customers_xlsx"},
            }

        if "工作模式" in msg:
            if any(k in msg for k in ["进入", "开启", "打开", "开始", "启动"]) or msg in [
                "工作模式",
                "进入工作模式",
                "开启工作模式",
            ]:
                return {
                    "text": "已进入工作模式，球体已切换为红色；将开始监控列表并每 10 秒刷新。",
                    "action": "auto_action",
                    "data": {"type": "set_work_mode", "enabled": True},
                }
            if any(k in msg for k in ["退出", "关闭", "停止", "结束"]) or msg in [
                "退出工作模式",
                "关闭工作模式",
            ]:
                return {
                    "text": "已退出工作模式，球体已恢复为青色；监控列表与每 10 秒刷新已停止。",
                    "action": "auto_action",
                    "data": {"type": "set_work_mode", "enabled": False},
                }

        customer_list_keywords = [
            "购买单位列表",
            "客户列表",
            "查看客户",
            "查看用户列表",
            "用户列表",
            "用户名单",
            "客户名单",
            "单位列表",
        ]

        if any(k in msg for k in customer_list_keywords):
            return {
                "text": "已打开客户/购买单位列表，支持右侧编辑；也可直接说「把 XX 的电话改成 138xxxx」等。",
                "action": "auto_action",
                "data": {"type": "show_customers"},
            }

        product_list_keywords = ["产品列表", "产品库", "商品列表", "查看产品"]
        if any(k in msg for k in product_list_keywords):
            return {
                "text": "已打开产品列表，支持查看和搜索。",
                "action": "auto_action",
                "data": {"type": "show_products"},
            }

        monitor_keywords = ["监控模式", "进入监控模式", "开启监控模式", "打开监控模式"]
        if any(k in msg for k in monitor_keywords):
            return {
                "text": "已进入监控模式，可以查看系统 CPU、内存、磁盘使用情况以及服务状态。",
                "action": "auto_action",
                "data": {"type": "show_monitor"},
            }

        return None
