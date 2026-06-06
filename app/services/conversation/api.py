import logging
import time
from typing import Any

from app.neuro_bus.event_publisher_mixin import NeuroEventPublisherMixin
from app.services.conversation.context import ConversationContext
from app.utils.cache_manager import get_ai_response_cache

logger = logging.getLogger(__name__)

_ai_response_cache = get_ai_response_cache()


def _make_ai_response_cache_key(message: str, context_hash: str = "") -> str:
    import hashlib

    return hashlib.sha256(
        f"ai_response:v1:{context_hash}:{message.strip().lower()}".encode()
    ).hexdigest()


class ApiMixin(NeuroEventPublisherMixin):

    async def _get_deepseek_async_client(self):
        import asyncio

        import httpx

        loop = asyncio.get_running_loop()
        if self._deepseek_async_loop is not loop:
            if self._deepseek_async_client is not None:
                try:
                    await self._deepseek_async_client.aclose()
                except Exception:
                    logger.debug("suppressed exception", exc_info=True)
                self._deepseek_async_client = None
            self._deepseek_async_loop = loop
            self._deepseek_async_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=30),
            )
        return self._deepseek_async_client

    async def _call_ai_offline(
        self,
        message: str,
        context: ConversationContext,
        intent_result: dict[str, Any],
    ) -> dict[str, Any]:
        final_intent = intent_result.get("final_intent") or intent_result.get("primary_intent")
        if final_intent and final_intent != "unk":
            reply = (
                f"当前为离线模式，已识别意图：{final_intent}。"
                "如需更强的开放问答能力，可在系统设置切换到在线模式。"
            )
        else:
            reply = (
                "当前为离线模式，我可以继续处理开单、查询、打印等本地可执行流程。"
                "如果你希望进行复杂问答，请在系统设置切换到在线模式。"
            )

        self.add_to_history(context.user_id, "user", message)
        self.add_to_history(context.user_id, "assistant", reply)
        return {
            "text": reply,
            "action": "offline_response",
            "data": {
                "intent": intent_result,
                "mode": "offline",
            },
        }

    async def call_llm_api(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> dict[str, Any] | None:
        """
        通用LLM API调用 - 三级自动路由

        优先级：
        1. 平台代理模式 (modstore_adapter) - 通过修茈市场统一接口
        2. 直连模式 (llm_adapter) - 直接调用厂商API
        3. 降级模式 (legacy DeepSeek) - 向后兼容
        """
        t0 = time.perf_counter()

        try:
            from app.infrastructure.llm.providers.registry import get_active_provider

            provider = get_active_provider(conversation_service=self)
            if provider is None:
                logger.error("❌ 无可用的 LLM Provider（检查 LLM_ROUTING_ORDER / 密钥）")
                return None

            logger.info("🤖 [LLM] provider=%s", provider.provider_id)
            result = await provider.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            if result:
                try:
                    from app.neuro_bus.application_neuro_bridge import (
                        neuro_notify_ai_model_roundtrip,
                    )

                    usage = result.get("usage") or {}
                    neuro_notify_ai_model_roundtrip(
                        model=provider.provider_id,
                        latency_ms=(time.perf_counter() - t0) * 1000.0,
                        token_count=int(usage.get("total_tokens") or 0),
                        user_id=str(
                            getattr(getattr(self, "modstore_adapter", None), "user_id", "") or ""
                        ),
                    )
                except Exception:
                    pass
            return result

        except Exception as e:
            logger.error("❌ LLM API调用异常: %s", e, exc_info=True)
            return None

    async def _call_deepseek_legacy(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> dict[str, Any] | None:
        """保留原有DeepSeek逻辑作为降级方案"""
        import httpx

        if not self.api_key:
            logger.error("DeepSeek API Key 未配置")
            return None

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        t0 = time.perf_counter()
        try:
            client = await self._get_deepseek_async_client()
            response = await client.post(
                self.api_url,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

            if result.get("choices") and len(result["choices"]) > 0:
                try:
                    from app.neuro_bus.application_neuro_bridge import (
                        neuro_notify_ai_model_roundtrip,
                    )

                    neuro_notify_ai_model_roundtrip(
                        model=self.model,
                        latency_ms=(time.perf_counter() - t0) * 1000.0,
                        token_count=0,
                        user_id="",
                    )
                except Exception:
                    logger.debug("neuro_notify_ai_model_roundtrip skipped", exc_info=True)
                return result
            logger.warning(f"DeepSeek API 返回空响应：{result}")
            return None

        except httpx.HTTPError as e:
            logger.error(f"DeepSeek API 请求失败：{e}")
            return None
        except Exception as e:
            logger.error(f"调用 DeepSeek API 异常：{e}")
            return None

    # 向后兼容别名
    call_deepseek_api = call_llm_api

    def _maybe_attach_kitten_web(
        self,
        conv_context: ConversationContext,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        req = (conv_context.metadata or {}).get("request_context") or {}
        if not req.get("kitten_analyzer") or not req.get("kitten_web_search"):
            return result
        payload = result.get("data")
        if not isinstance(payload, dict):
            payload = {}
            result["data"] = payload
        payload["web_search_results"] = list(req.get("web_search_results") or [])
        meta = req.get("web_search_meta")
        if meta:
            payload["web_search_meta"] = meta
        err = req.get("web_search_error")
        if err:
            payload["web_search_error"] = err
        return result

    async def _execute_or_generate_response(
        self,
        message: str,
        intent_result: dict[str, Any],
        conv_context: ConversationContext,
        user_id: str,
    ) -> dict[str, Any]:
        final_intent = intent_result.get("final_intent") or intent_result.get("primary_intent")
        slots = intent_result.get("slots", {})

        pending = self.confirmation_service.get_pending_intent(user_id)
        if pending:
            slots = self.confirmation_service.merge_slots(user_id, slots)

        check_result = self.confirmation_service.check_and_build_prompt(
            {
                "final_intent": final_intent,
                "slots": slots,
            }
        )

        if check_result["status"] == "missing_slots":
            self.confirmation_service.set_pending_intent(user_id, check_result["pending_data"])
            return {
                "text": check_result["question"],
                "action": "slot_fill",
                "data": {
                    "intent": final_intent,
                    "slots": slots,
                    "missing_slots": check_result["missing_slots"],
                    "pending_data": check_result["pending_data"],
                },
            }

        tool_key = intent_result.get("tool_key")
        if tool_key:
            return self._build_tool_call_response(
                tool_key, slots, intent_result, user_id, check_result
            )

        if intent_result.get("ai_mode") == "offline":
            return await self._call_ai_offline(message, conv_context, intent_result)

        return await self._call_ai(message, conv_context, intent_result)

    def _build_tool_call_response(
        self,
        tool_key: str,
        slots: dict[str, Any],
        intent_result: dict[str, Any],
        user_id: str,
        check_result: dict[str, Any],
    ) -> dict[str, Any]:
        tool_action_texts = {
            "shipment_generate": f"正在为 {slots.get('unit_name', slots.get('keyword', '该客户'))} 生成发货单",
            "products": f"正在查询 {slots.get('unit_name', slots.get('keyword', '该产品'))} 的产品信息",
            "customers": "正在查询客户信息",
            "shipments": "正在查询发货记录",
            "print_label": "正在处理标签打印",
            "wechat_send": "正在发送微信消息",
            "upload_file": "正在上传文件",
            "materials": "正在查询原材料库存",
            "shipment_template": "正在查询发货单模板",
            "template_extract": "正在提取模板结构",
            "business_docking": "正在执行业务对接模板提取",
            "template_preview": "正在查询模板预览",
            "shipment_records": "正在查询出货记录",
            "wechat": "正在处理微信联系人能力",
            "printer_list": "正在查询打印机配置",
            "settings": "正在读取系统设置",
            "tools_table": "正在加载工具能力表",
            "other_tools": "正在查询其他工具能力",
            "ai_ecosystem": "正在查询AI生态能力",
            "excel_decompose": "正在分解Excel模板",
            "excel_analyzer": "正在分析Excel结构",
            "show_images": "正在查看图片",
            "show_videos": "正在查看视频",
        }
        action_text = tool_action_texts.get(tool_key, f"正在处理工具调用：{tool_key}")

        habit_suggestion = self._check_habit_suggestion(user_id, tool_key, slots)
        if habit_suggestion:
            action_text = f"{action_text} {habit_suggestion}"

        self.confirmation_service.set_pending_intent(
            user_id,
            {
                "intent": intent_result.get("final_intent") or intent_result.get("primary_intent"),
                "slots": slots,
                "missing_slots": (
                    check_result.get("missing_slots", [])
                    if check_result.get("status") == "missing_slots"
                    else []
                ),
            },
        )
        return {
            "text": f"好的，{action_text}...",
            "action": "tool_call",
            "data": {
                "tool_key": tool_key,
                "intent": intent_result.get("final_intent") or intent_result.get("primary_intent"),
                "slots": slots,
                "hints": intent_result.get("intent_hints", []),
                "habit_suggestion": habit_suggestion,
            },
        }

    async def _call_ai(
        self, message: str, context: ConversationContext, intent_result: dict[str, Any]
    ) -> dict[str, Any]:
        context_hash = self._metadata_cache_hash(context.metadata)
        cache_key = _make_ai_response_cache_key(message, context_hash)
        cached_response = _ai_response_cache.get(cache_key)
        if cached_response:
            logger.debug("返回缓存的 AI 响应")
            # 获取当前使用的模型信息
            current_model = (
                getattr(self.llm_adapter, "model_name", None)
                if hasattr(self, "llm_adapter") and self.llm_adapter
                else self.model
            )
            return {
                "text": cached_response,
                "action": "ai_response",
                "data": {"model": current_model, "cached": True, "intent": intent_result},
            }

        base_prompt = """你是一个专业的业务助手，服务于使用 XCAGI 系统的用户。
你的职责：
1. 友好、专业地回答用户问题
2. 协助用户处理发货单、产品、客户等业务
3. 提供清晰、简洁的回答
4. 如果不确定，请诚实地告知用户

XCAGI 系统主要功能：
- 发货单生成和管理
- 产品和客户管理
- 订单处理
- 文件上传和导出
- 数据查询和统计"""

        context_prompt = self._build_context_prompt(context)
        system_prompt = base_prompt + ("\n\n" + context_prompt if context_prompt else "")

        messages = [{"role": "system", "content": system_prompt}]

        if context.conversation_history:
            messages.extend(context.conversation_history[-10:])

        messages.append({"role": "user", "content": message})

        # 获取当前LLM模式和信息（用于日志）
        if hasattr(self, "modstore_adapter") and self.modstore_adapter:
            mode_tag = "🌐平台"
            provider_info = (
                f"modstore:{self.modstore_adapter.default_provider}/"
                f"{self.modstore_adapter.default_model}"
            )
        elif hasattr(self, "llm_adapter") and self.llm_adapter and self.llm_adapter.is_configured:
            mode_tag = "⚡直连"
            provider_info = f"{self.llm_adapter.provider_name}/{self.llm_adapter.model_name}"
        else:
            mode_tag = "📦降级"
            provider_info = f"DeepSeek/{self.model}"

        logger.info(f"准备调用 LLM API [{mode_tag}]: {provider_info}")

        response = await self.call_llm_api(messages)  # 使用三级路由方法

        logger.info(
            f"LLM API 响应 [{mode_tag} {provider_info}]: "
            f"{str(response)[:150] if response else 'None'}..."
        )

        if response and response.get("choices"):
            ai_reply = response["choices"][0]["message"]["content"]

            self.add_to_history(context.user_id, "user", message)
            self.add_to_history(context.user_id, "assistant", ai_reply)

            _ai_response_cache.set(cache_key, ai_reply)

            # 获取当前使用的模型和供应商信息
            if hasattr(self, "modstore_adapter") and self.modstore_adapter:
                current_model = f"modstore:{self.modstore_adapter.default_model}"
                current_provider = "modstore-platform"
            elif (
                hasattr(self, "llm_adapter") and self.llm_adapter and self.llm_adapter.is_configured
            ):
                current_model = self.llm_adapter.model_name
                current_provider = self.llm_adapter.provider_name
            else:
                current_model = self.model
                current_provider = "deepseek-legacy"

            return {
                "text": ai_reply,
                "action": "ai_response",
                "data": {
                    "model": current_model,
                    "provider": current_provider,
                    "usage": response.get("usage", {}),
                    "intent": intent_result,
                },
            }
        else:
            fallback_reply = '抱歉，我暂时无法理解您的需求。您可以：\n• 重新描述您的问题\n• 使用更简单的语句\n• 联系人工客服获取帮助\n\n如果需要帮助，请说"帮助"或"功能介绍"。'

            self.add_to_history(context.user_id, "user", message)
            self.add_to_history(context.user_id, "assistant", fallback_reply)

            return {"text": fallback_reply, "action": "fallback", "data": {"intent": intent_result}}
