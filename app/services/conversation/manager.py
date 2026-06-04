import logging
import os
import time
from typing import Any

from app.services.conversation.api import ApiMixin
from app.services.conversation.context import ConversationContext, ContextMixin
from app.services.conversation.handlers import HandlersMixin
from app.services.conversation.intent import IntentMixin
from app.services.conversation.prompts import PromptsMixin

logger = logging.getLogger(__name__)


class AIConversationService(
    ContextMixin,
    IntentMixin,
    HandlersMixin,
    PromptsMixin,
    ApiMixin,
):

    def __init__(self):
        self.contexts: dict[str, ConversationContext] = {}

        # ========== LLM调用架构初始化（三级优先级）==========
        self.llm_adapter = None
        self.modstore_adapter = None
        llm_init_mode = "none"

        try:
            # 优先级1: 平台代理模式（修茈市场统一接口）
            from app.services.conversation.modstore_adapter import (
                ModstorePlatformAdapter,
                create_modstore_adapter_from_env
            )

            modstore = create_modstore_adapter_from_env()
            if modstore and modstore.is_configured:
                self.modstore_adapter = modstore
                llm_init_mode = "platform"
                logger.info(
                    f"🌐 [优先级1] 启用修茈市场平台代理模式\n"
                    f"   平台地址: {modstore.platform_url}\n"
                    f"   默认模型: {modstore.default_provider}/{modstore.default_model}\n"
                    f"   用户ID: {modstore.user_id}\n"
                    f"   ✅ 所有LLM请求将通过平台统一路由"
                )
            else:
                logger.debug("未检测到修茈市场平台配置，尝试直连模式...")

            # 优先级2: 直连模式（OpenAI兼容适配器）
            if not self.modstore_adapter:
                from app.services.conversation.llm_adapter import OpenAICompatibleAdapter

                llm_provider = os.environ.get("LLM_PROVIDER", "xiaomi").lower().strip()
                llm_model = os.environ.get("LLM_MODEL", None)
                llm_api_key = os.environ.get(f"{llm_provider.upper()}_API_KEY", None)
                llm_base_url = os.environ.get(f"{llm_provider.upper()}_BASE_URL", None)

                self.llm_adapter = OpenAICompatibleAdapter(
                    provider=llm_provider,
                    model=llm_model,
                    api_key=llm_api_key,
                    base_url=llm_base_url
                )

                if self.llm_adapter.is_configured:
                    llm_init_mode = "direct"
                    logger.info(
                        f"⚡ [优先级2] 启用直连模式: {self.llm_adapter.provider_name}/"
                        f"{self.llm_adapter.model_name} (Key已配置)"
                    )
                else:
                    logger.warning(
                        f"⚠️ 直连适配器已创建但 [{llm_provider}] API Key未配置"
                    )

        except Exception as adapter_err:
            logger.error(f"❌ LLM适配器初始化失败: {adapter_err}")
            self.llm_adapter = None
            self.modstore_adapter = None

        # ========== 保留原有DeepSeek配置（向后兼容降级 - 优先级3）==========
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            try:
                from app.utils.path_utils import get_resource_path

                config_path = get_resource_path("config", "deepseek_config.py")
                if os.path.exists(config_path):
                    import importlib.util

                    spec = importlib.util.spec_from_file_location(
                        "xcagi_deepseek_config", config_path
                    )
                    if spec and spec.loader:
                        config_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(config_module)
                        self.api_key = getattr(config_module, "DEEPSEEK_API_KEY", "") or ""
            except Exception as e:
                logger.warning(f"无法读取 resources/config/deepseek_config.py: {e}")

        if self.api_key and llm_init_mode == "none":
            llm_init_mode = "legacy"
            logger.info(
                f"📦 [优先级3/降级] 使用旧版DeepSeek直连模式 "
                f"(Key长度: {len(self.api_key)})"
            )
        elif self.api_key:
            logger.info(
                f"DeepSeek API Key 已配置（长度: {len(self.api_key)}）(作为降级备选)"
            )
        else:
            logger.warning("DeepSeek API Key 未配置（降级路径不可用）")

        from app.infrastructure.llm.providers.credentials import default_chat_completions_url

        self.api_url = default_chat_completions_url()
        self.model = "deepseek-chat"

        # 记录最终使用的模式
        self._llm_mode = llm_init_mode
        logger.info(f"🎯 LLM初始化完成，运行模式: {llm_init_mode}")

        from app.services.intent_confirmation_service import get_confirmation_service
        from app.services.intent_service import recognize_intents
        from app.services.task_agent import get_task_agent
        from app.services.unified_intent_recognizer import get_unified_intent_recognizer

        from app.services.deepseek_intent_service import HybridIntentWithDeepSeek
        from app.services.user_memory_service import get_user_memory_service
        from app.services.user_preference_service import get_user_preference_service

        use_distilled = os.environ.get("USE_DISTILLED_MODEL", "0") == "1"
        if use_distilled:
            logger.info("已启用蒸馏意图识别开关：USE_DISTILLED_MODEL=1")

        self.intent_service = recognize_intents
        self.online_intent_service = HybridIntentWithDeepSeek(
            use_deepseek=True,
            rule_priority=True,
            confidence_threshold=0.6,
            use_distilled=use_distilled,
        )
        self.offline_intent_service = HybridIntentWithDeepSeek(
            use_deepseek=False,
            rule_priority=True,
            confidence_threshold=0.6,
            use_distilled=True,
        )
        self.deepseek_intent_service = self.online_intent_service
        self.unified_recognizer = get_unified_intent_recognizer()
        self.confirmation_service = get_confirmation_service()
        self.task_agent = get_task_agent()
        self.user_memory = get_user_memory_service()
        self.user_preference_service = get_user_preference_service()
        self._deepseek_async_client: Any = None
        self._deepseek_async_loop: Any = None

    def add_to_history(self, user_id: str, role: str, content: str) -> bool:
        context = self.contexts.get(user_id)
        if not context:
            context = self.create_context(user_id)

        context.conversation_history.append({"role": role, "content": content})

        if len(context.conversation_history) > 20:
            context.conversation_history = context.conversation_history[-20:]

        context.updated_at = time.time()
        return True

    def add_intent_feedback(
        self,
        user_id: str,
        message: str,
        recognized_intent: str,
        feedback: str,
        corrected_intent: str | None = None,
        slots: dict[str, Any] | None = None,
    ) -> None:
        try:
            self.user_memory.add_feedback(
                user_id=user_id,
                message=message,
                recognized_intent=recognized_intent,
                feedback=feedback,
                corrected_intent=corrected_intent,
                slots=slots or {},
            )
        except Exception as e:
            logger.error(f"添加意图反馈失败: {e}")

    def record_user_action(
        self,
        user_id: str,
        intent: str,
        slots: dict[str, Any],
        message: str,
    ) -> None:
        try:
            self.user_memory.record_action(
                user_id=user_id,
                intent=intent,
                slots=slots,
                message=message,
            )
        except Exception as e:
            logger.error(f"记录用户操作失败: {e}")

    def apply_memory_preferences(
        self, user_id: str, intent: str, slots: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            return self.user_memory.apply_preference_to_slots(user_id, intent, slots)
        except Exception as e:
            logger.error(f"应用用户偏好失败: {e}")
            return slots

    def get_memory_similar_action(
        self, user_id: str, intent: str, slots: dict[str, Any]
    ) -> dict[str, Any] | None:
        try:
            return self.user_memory.get_similar_pattern(user_id, intent, slots)
        except Exception as e:
            logger.error(f"获取相似操作失败: {e}")
            return None

    def get_habit_suggestions(self, user_id: str) -> list[dict[str, Any]]:
        try:
            return self.user_memory.get_habit_suggestions(user_id)
        except Exception as e:
            logger.error(f"获取习惯建议失败: {e}")
            return []

    def get_context_for_recognition(
        self, user_id: str, conv_context: ConversationContext
    ) -> dict[str, Any]:
        context = {
            "user_id": user_id,
            "current_intent": conv_context.current_intent,
            "current_tool_key": conv_context.current_tool_key,
            "last_intent": conv_context.current_intent,
            "last_tool_key": conv_context.current_tool_key,
            "last_slots": (
                conv_context.last_intent_result.get("slots", {})
                if conv_context.last_intent_result
                else {}
            ),
            "pending_confirmation": conv_context.pending_confirmation,
        }

        recent_actions = self.user_memory.get_recent_actions(user_id, limit=3)
        if recent_actions:
            context["recent_intents"] = [a.get("intent") for a in recent_actions]

        preferences = self.user_memory.get_all_preferences(user_id)
        if preferences:
            context["user_preferences"] = preferences

        return context

    def _check_habit_suggestion(
        self, user_id: str, current_intent: str, slots: dict[str, Any]
    ) -> str | None:
        try:
            habits = self.get_habit_suggestions(user_id)

            for habit in habits:
                actions = habit.get("actions", [])
                confidence = habit.get("confidence", 0)

                if confidence < 0.8:
                    continue

                for action in actions:
                    if action.get("intent") == current_intent:
                        return f"💡 根据您的习惯，您可能还需要：{action.get('description', '')}"
        except Exception as e:
            logger.error(f"检查习惯建议失败: {e}")

        return None

    async def chat(
        self,
        user_id: str,
        message: str,
        context: dict[str, Any] | None = None,
        source: str | None = None,
    ) -> dict[str, Any]:
        try:
            conv_context = await self._get_or_create_context_async(user_id, context, message)

            intent_result = await self._recognize_intent(message, source, user_id, context)
            intent_result = self._enhance_intent_slots(message, intent_result, user_id)

            logger.info(
                f"[INTENT_RESULT] final_intent={intent_result.get('final_intent')}, primary_intent={intent_result.get('primary_intent')}, tool_key={intent_result.get('tool_key')}, slots={intent_result.get('slots')}, intent_source={intent_result.get('intent_source')}"
            )
            self._update_context_from_intent(conv_context, intent_result)

            if result := await self._handle_special_intents(
                message, intent_result, conv_context, user_id
            ):
                return self._maybe_attach_kitten_web(conv_context, result)

            if result := await self._handle_pending_intent(
                message, intent_result, conv_context, user_id
            ):
                return self._maybe_attach_kitten_web(conv_context, result)

            out = await self._execute_or_generate_response(
                message, intent_result, conv_context, user_id
            )
            return self._maybe_attach_kitten_web(conv_context, out)

        except Exception as e:
            logger.error(f"处理聊天消息失败：{e}")
            return {
                "text": f"抱歉，处理消息时出现问题：{str(e)}",
                "action": "error",
                "data": {"message": str(e)},
            }


_ai_conversation_service: AIConversationService | None = None


def get_ai_conversation_service() -> AIConversationService:
    global _ai_conversation_service
    if _ai_conversation_service is None:
        _ai_conversation_service = AIConversationService()
    return _ai_conversation_service


def init_ai_conversation_service() -> AIConversationService:
    global _ai_conversation_service
    _ai_conversation_service = AIConversationService()
    logger.info("AI 对话服务已初始化")
    return _ai_conversation_service


from app.neuro_bus.neuro_service_instrumentation import instrument_service_layer_class

instrument_service_layer_class(AIConversationService, "app.services.ai_conversation_service")
