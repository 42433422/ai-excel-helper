# -*- coding: utf-8 -*-
"""
AI 对话引擎服务：处理 AI 对话、DeepSeek API 调用、上下文管理

提供完整的 AI 对话功能，包括：
- DeepSeek API 集成
- 对话上下文管理
- 工具调用协调
- 特殊场景处理（订单、表格编辑等）
"""

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.deepseek_intent_service import HybridIntentWithDeepSeek
from app.services.user_preference_service import get_user_preference_service
from app.services.user_memory_service import get_user_memory_service
from app.utils.cache_manager import get_ai_response_cache

logger = logging.getLogger(__name__)


_ai_response_cache = get_ai_response_cache()


def _make_ai_response_cache_key(message: str, context_hash: str = "") -> str:
    return hashlib.sha256(
        f"ai_response:v1:{context_hash}:{message.strip().lower()}".encode("utf-8")
    ).hexdigest()


@dataclass
class ConversationContext:
    """对话上下文数据类"""
    user_id: str
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    current_file: Optional[str] = None
    last_action: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    current_intent: Optional[str] = None
    current_tool_key: Optional[str] = None
    intent_hints: List[str] = field(default_factory=list)
    pending_confirmation: Optional[Dict[str, Any]] = None
    last_intent_result: Optional[Dict[str, Any]] = None


class AIConversationService:
    """
    AI 对话服务类
    
    负责处理 AI 对话逻辑，包括：
    - DeepSeek API 调用
    - 对话上下文管理
    - 工具调用协调
    - 特殊场景处理
    """
    
    def __init__(self):
        """初始化 AI 对话服务"""
        self.contexts: Dict[str, ConversationContext] = {}
        
        # 优先使用环境变量，否则使用项目内 resources/config 的备用 key
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            try:
                from app.utils.path_utils import get_resource_path

                config_path = get_resource_path("config", "deepseek_config.py")
                if os.path.exists(config_path):
                    import importlib.util

                    spec = importlib.util.spec_from_file_location("xcagi_deepseek_config", config_path)
                    if spec and spec.loader:
                        config_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(config_module)
                        self.api_key = getattr(config_module, "DEEPSEEK_API_KEY", "") or ""
            except Exception as e:
                logger.warning(f"无法读取 resources/config/deepseek_config.py: {e}")
        
        # 记录 API Key 状态
        if self.api_key:
            logger.info(f"DeepSeek API Key 已配置 (长度: {len(self.api_key)})")
        else:
            logger.warning("DeepSeek API Key 未配置")
        
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"

        # 导入依赖服务
        from .intent_confirmation_service import get_confirmation_service
        from .intent_service import recognize_intents
        from .task_agent import get_task_agent
        from .unified_intent_recognizer import get_unified_intent_recognizer
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
        # 离线模式强制禁用 DeepSeek，优先蒸馏模型并在缺失时回退规则。
        self.offline_intent_service = HybridIntentWithDeepSeek(
            use_deepseek=False,
            rule_priority=True,
            confidence_threshold=0.6,
            use_distilled=True,
        )
        # 兼容现有引用命名
        self.deepseek_intent_service = self.online_intent_service
        self.unified_recognizer = get_unified_intent_recognizer()
        self.confirmation_service = get_confirmation_service()
        self.task_agent = get_task_agent()
        self.user_memory = get_user_memory_service()
        self.user_preference_service = get_user_preference_service()
        # 按 asyncio 事件循环复用 httpx.AsyncClient，减少短时多次请求时的连接风暴与 TLS 失败
        self._deepseek_async_client: Any = None
        self._deepseek_async_loop: Any = None

    @staticmethod
    def _is_pro_source(source: Optional[str]) -> bool:
        """兼容多种前端 source 写法。"""
        normalized = str(source or "").strip().lower().replace("-", "_")
        return normalized in {"pro", "pro_mode", "promode"}

    @staticmethod
    def _normalize_ai_mode(mode: Optional[str]) -> str:
        raw = str(mode or "").strip().lower()
        if raw in {"offline", "local"}:
            return "offline"
        return "online"

    def _resolve_ai_mode(self, user_id: str) -> str:
        """解析用户 AI 模式，兼容旧 aiModel 偏好键。"""
        try:
            mode_value = self.user_preference_service.get_preference(user_id, "aiMode")
            if mode_value:
                return self._normalize_ai_mode(mode_value)
            # 兼容旧键：aiModel=deepseek/local
            legacy_model = self.user_preference_service.get_preference(user_id, "aiModel")
            if legacy_model:
                mode = self._normalize_ai_mode(legacy_model)
                self.user_preference_service.set_preference(user_id, "aiMode", mode)
                return mode
        except Exception as e:
            logger.warning(f"读取 aiMode 偏好失败，回退在线模式: {e}")
        return "online"

    @staticmethod
    def _env_skip_intent_llm() -> bool:
        """设为 1/true 时，非 pro 链路跳过 HybridIntent 内的 DeepSeek 意图识别（仅规则）。"""
        return os.environ.get("XCAGI_SKIP_INTENT_LLM", "").strip().lower() in {"1", "true", "yes", "on"}

    def _should_use_rule_only_intent(self, request_context: Optional[Dict[str, Any]]) -> bool:
        if self._env_skip_intent_llm():
            return True
        if isinstance(request_context, dict) and request_context.get("skip_intent_llm"):
            return True
        return False

    def _intent_rule_only_fast(self, message: str) -> Dict[str, Any]:
        """仅用规则引擎识别意图，不调用 DeepSeek（与 online_intent_service 输出形状对齐）。"""
        r = self.intent_service(message)
        if not isinstance(r, dict):
            r = {}
        return {
            "primary_intent": r.get("primary_intent"),
            "final_intent": r.get("primary_intent") or r.get("tool_key"),
            "tool_key": r.get("tool_key"),
            "intent_hints": list(r.get("intent_hints") or []),
            "is_negated": bool(r.get("is_negated")),
            "is_greeting": bool(r.get("is_greeting")),
            "is_goodbye": bool(r.get("is_goodbye")),
            "is_help": bool(r.get("is_help")),
            "is_confirmation": bool(r.get("is_confirmation")),
            "is_negation_intent": bool(r.get("is_negation_intent")),
            "is_likely_unclear": bool(r.get("is_likely_unclear")),
            "slots": {},
            "all_matched_tools": r.get("all_matched_tools", []),
            "intent_source": "rule_only_fast",
        }

    async def _get_deepseek_async_client(self):
        """同一事件循环内复用 AsyncClient；切换 loop 时关闭旧 client。"""
        import asyncio

        import httpx

        loop = asyncio.get_running_loop()
        if self._deepseek_async_loop is not loop:
            if self._deepseek_async_client is not None:
                try:
                    await self._deepseek_async_client.aclose()
                except Exception:
                    pass
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
        intent_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """离线模式下的本地回复（不调用云端）。"""
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

    def add_intent_feedback(
        self,
        user_id: str,
        message: str,
        recognized_intent: str,
        feedback: str,
        corrected_intent: Optional[str] = None,
        slots: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        添加意图识别反馈

        Args:
            user_id: 用户ID
            message: 用户消息
            recognized_intent: 系统识别的意图
            feedback: 反馈类型 (confirmed/negated/corrected)
            corrected_intent: 正确意图（当 feedback=corrected 时）
            slots: 槽位信息
        """
        try:
            self.user_memory.add_feedback(
                user_id=user_id,
                message=message,
                recognized_intent=recognized_intent,
                feedback=feedback,
                corrected_intent=corrected_intent,
                slots=slots or {}
            )
            logger.info(f"[FEEDBACK] user={user_id}, recognized={recognized_intent}, feedback={feedback}")

            # 记忆向量写入：把用户的意图校正/反馈写入向量库，用于后续 RAG 决策。
            try:
                from app.application import get_user_memory_vector_ingest_app_service

                ingest = get_user_memory_vector_ingest_app_service()
                chunk = ingest.build_feedback_chunk(
                    user_id=user_id,
                    message=message,
                    recognized_intent=recognized_intent,
                    feedback=feedback,
                    corrected_intent=corrected_intent,
                    slots=slots or {},
                )
                ingest.ingest_chunks(user_id=user_id, chunks=[chunk])
            except Exception as ve:
                logger.warning(f"[UserMemoryVector] 写入反馈向量失败: {ve}")
        except Exception as e:
            logger.error(f"添加意图反馈失败: {e}")

    def record_user_action(
        self,
        user_id: str,
        intent: str,
        slots: Dict[str, Any],
        message: str = ""
    ) -> None:
        """
        记录用户操作

        Args:
            user_id: 用户ID
            intent: 意图类型
            slots: 槽位信息
            message: 原始消息
        """
        try:
            self.user_memory.record_action(
                user_id=user_id,
                intent=intent,
                slots=slots,
                message=message
            )

            if intent == "shipment_generate" and slots.get("unit_name"):
                self.user_memory.add_preference(
                    user_id,
                    "favorite_customer",
                    slots["unit_name"]
                )

            # 记忆向量写入：把用户执行的意图/槽位/消息摘要写入向量库。
            try:
                from app.application import get_user_memory_vector_ingest_app_service

                ingest = get_user_memory_vector_ingest_app_service()
                chunk = ingest.build_action_chunk(
                    user_id=user_id,
                    intent=intent,
                    slots=slots or {},
                    message=message or "",
                )
                ingest.ingest_chunks(user_id=user_id, chunks=[chunk])
            except Exception as ve:
                logger.warning(f"[UserMemoryVector] 写入动作向量失败: {ve}")

            logger.debug(f"[ACTION] user={user_id}, intent={intent}, slots={slots}")
        except Exception as e:
            logger.error(f"记录用户操作失败: {e}")

    def apply_memory_preferences(
        self,
        user_id: str,
        intent: str,
        slots: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        应用用户记忆偏好到槽位

        Args:
            user_id: 用户ID
            intent: 当前意图
            slots: 当前槽位

        Returns:
            填充后的槽位
        """
        try:
            return self.user_memory.apply_preference_to_slots(user_id, intent, slots)
        except Exception as e:
            logger.error(f"应用用户偏好失败: {e}")
            return slots

    def get_memory_similar_action(
        self,
        user_id: str,
        intent: str,
        slots: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        获取记忆中相似的操作

        Args:
            user_id: 用户ID
            intent: 当前意图
            slots: 当前槽位

        Returns:
            相似操作或 None
        """
        try:
            return self.user_memory.get_similar_pattern(user_id, intent, slots)
        except Exception as e:
            logger.error(f"获取相似操作失败: {e}")
            return None

    def get_habit_suggestions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取操作习惯建议

        Args:
            user_id: 用户ID

        Returns:
            习惯建议列表
        """
        try:
            return self.user_memory.get_habit_suggestions(user_id)
        except Exception as e:
            logger.error(f"获取习惯建议失败: {e}")
            return []

    def get_context_for_recognition(
        self,
        user_id: str,
        conv_context: ConversationContext
    ) -> Dict[str, Any]:
        """
        构建用于意图识别的上下文

        Args:
            user_id: 用户ID
            conv_context: 会话上下文

        Returns:
            上下文字典
        """
        context = {
            "user_id": user_id,
            "current_intent": conv_context.current_intent,
            "current_tool_key": conv_context.current_tool_key,
            "last_intent": conv_context.current_intent,
            "last_tool_key": conv_context.current_tool_key,
            "last_slots": conv_context.last_intent_result.get("slots", {}) if conv_context.last_intent_result else {},
            "pending_confirmation": conv_context.pending_confirmation,
        }

        recent_actions = self.user_memory.get_recent_actions(user_id, limit=3)
        if recent_actions:
            context["recent_intents"] = [a.get("intent") for a in recent_actions]

        preferences = self.user_memory.get_all_preferences(user_id)
        if preferences:
            context["user_preferences"] = preferences

        return context
    
    def get_context(self, user_id: str) -> Optional[ConversationContext]:
        """
        获取用户对话上下文
        
        Args:
            user_id: 用户 ID
            
        Returns:
            对话上下文对象，如果不存在则返回 None
        """
        return self.contexts.get(user_id)
    
    def create_context(self, user_id: str) -> ConversationContext:
        """
        创建新的对话上下文
        
        Args:
            user_id: 用户 ID
            
        Returns:
            新创建的对话上下文
        """
        context = ConversationContext(user_id=user_id)
        self.contexts[user_id] = context
        logger.info(f"为用户 {user_id} 创建新的对话上下文")
        return context
    
    def update_context(self, user_id: str, **kwargs) -> Optional[ConversationContext]:
        """
        更新对话上下文
        
        Args:
            user_id: 用户 ID
            **kwargs: 要更新的字段
            
        Returns:
            更新后的上下文，如果不存在则返回 None
        """
        context = self.contexts.get(user_id)
        if not context:
            return None
        
        for key, value in kwargs.items():
            if hasattr(context, key):
                setattr(context, key, value)
        
        context.updated_at = time.time()
        return context

    def set_pending_confirmation(self, user_id: str, confirmation_data: Dict[str, Any]) -> bool:
        """
        设置待确认操作
        
        Args:
            user_id: 用户 ID
            confirmation_data: 待确认操作数据，包含 type, tool_key, params, description 等
            
        Returns:
            是否设置成功
        """
        context = self.contexts.get(user_id)
        if not context:
            context = self.create_context(user_id)
        
        context.pending_confirmation = confirmation_data
        context.updated_at = time.time()
        return True

    def add_to_history(self, user_id: str, role: str, content: str) -> bool:
        """
        添加消息到对话历史
        
        Args:
            user_id: 用户 ID
            role: 角色（'user' 或 'assistant'）
            content: 消息内容
            
        Returns:
            是否添加成功
        """
        context = self.contexts.get(user_id)
        if not context:
            context = self.create_context(user_id)
        
        context.conversation_history.append({
            "role": role,
            "content": content
        })
        
        # 保持历史记录在合理长度（最近 20 条）
        if len(context.conversation_history) > 20:
            context.conversation_history = context.conversation_history[-20:]
        
        context.updated_at = time.time()
        return True
    
    async def call_deepseek_api(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        调用 DeepSeek API
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            **kwargs: 其他参数
            
        Returns:
            API 响应字典，失败则返回 None
        """
        import httpx
        
        if not self.api_key:
            logger.error("DeepSeek API Key 未配置")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
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
                return result
            logger.warning(f"DeepSeek API 返回空响应：{result}")
            return None

        except httpx.HTTPError as e:
            logger.error(f"DeepSeek API 请求失败：{e}")
            return None
        except Exception as e:
            logger.error(f"调用 DeepSeek API 异常：{e}")
            return None

    async def _recognize_intent(
        self,
        message: str,
        source: Optional[str],
        user_id: str,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        识别用户消息的意图

        Args:
            message: 用户消息
            source: 来源标识
            user_id: 用户 ID
            request_context: 本次 HTTP 请求的 context（用于混合界面等策略）

        Returns:
            意图识别结果字典
        """
        ai_mode = self._resolve_ai_mode(user_id)
        is_offline_mode = ai_mode == "offline"

        if is_offline_mode:
            logger.info("[INTENT] 离线模式：使用本地蒸馏/规则识别")
            intent_result = await self.offline_intent_service.recognize(message)
        elif self._is_pro_source(source):
            logger.info("[INTENT] 使用 unified_recognizer (pro mode)")
            recognizer_result = self.unified_recognizer.recognize(
                message,
                context=None,
                context_data=request_context,
            )
            intent_result = self._convert_recognizer_result(recognizer_result)
        elif self._should_use_rule_only_intent(request_context):
            logger.info("[INTENT] rule_only_fast（跳过意图 DeepSeek，仅规则；可设 XCAGI_SKIP_INTENT_LLM=1 或 context.skip_intent_llm）")
            intent_result = self._intent_rule_only_fast(message)
        else:
            logger.info("[INTENT] 使用 deepseek_intent_service (普通模式)")
            intent_result = await self.online_intent_service.recognize(message)

        intent_result["ai_mode"] = ai_mode
        return intent_result

    def _convert_recognizer_result(self, recognizer_result) -> Dict[str, Any]:
        """
        将 unified_recognizer 的结果转换为标准格式

        Args:
            recognizer_result: unified_recognizer 的识别结果

        Returns:
            标准格式的意图结果字典
        """
        return {
            "primary_intent": recognizer_result.primary_intent,
            "final_intent": recognizer_result.primary_intent,
            "tool_key": recognizer_result.tool_key,
            "intent_hints": recognizer_result.intent_hints,
            "is_negated": recognizer_result.is_negated,
            "is_greeting": recognizer_result.is_greeting,
            "is_goodbye": recognizer_result.is_goodbye,
            "is_help": recognizer_result.is_help,
            "is_confirmation": recognizer_result.is_confirmation,
            "is_negation_intent": recognizer_result.is_negation_intent,
            "is_likely_unclear": recognizer_result.is_likely_unclear,
            "slots": recognizer_result.slots,
            "all_matched_tools": recognizer_result.all_matched_tools,
            "intent_source": "unified_recognizer",
        }

    def _enhance_intent_slots(
        self,
        message: str,
        intent_result: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        增强意图槽位信息

        Args:
            message: 用户消息
            intent_result: 意图识别结果
            user_id: 用户 ID

        Returns:
            增强后的意图结果字典
        """
        intent_result = self._enhance_with_task_agent(message, intent_result, user_id)
        intent_result = self._enhance_with_shipment_parser(message, intent_result)
        return intent_result

    def _enhance_with_task_agent(
        self,
        message: str,
        intent_result: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        使用任务代理增强槽位

        Args:
            message: 用户消息
            intent_result: 意图识别结果
            user_id: 用户 ID

        Returns:
            增强后的意图结果字典
        """
        plan = self.task_agent.parse_task(message, {"user_id": user_id})
        if not plan or not isinstance(plan, dict):
            return intent_result

        task_type = plan.get("task_type")
        task_slots = plan.get("slots") or {}
        task_to_tool = {
            "shipment_generate": "shipment_generate",
            "product_query": "products",
            "customer_query": "customers",
            "print_config": "system",
            "customer_supplement": "customers",
        }

        if task_type not in task_to_tool:
            return intent_result

        merged_slots = {}
        merged_slots.update(intent_result.get("slots") or {})
        merged_slots.update(task_slots)
        intent_result["slots"] = merged_slots

        if not intent_result.get("tool_key"):
            intent_result["tool_key"] = task_to_tool[task_type]
        if not intent_result.get("final_intent"):
            intent_result["final_intent"] = task_type
        if not intent_result.get("primary_intent"):
            intent_result["primary_intent"] = task_type

        return intent_result

    def _enhance_with_shipment_parser(
        self,
        message: str,
        intent_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用发货单解析器增强槽位

        Args:
            message: 用户消息
            intent_result: 意图识别结果

        Returns:
            增强后的意图结果字典
        """
        final_intent_name = intent_result.get("final_intent") or intent_result.get("primary_intent")
        if final_intent_name != "shipment_generate":
            return intent_result

        merged_slots = dict(intent_result.get("slots") or {})
        try:
            from app.routes.tools import _parse_order_text
            parsed_order = _parse_order_text(message)
            if not parsed_order.get("success"):
                return intent_result

            products = parsed_order.get("products") or []
            first = products[0] if products else {}

            if products:
                merged_slots["products"] = products
            if parsed_order.get("unit_name"):
                merged_slots["unit_name"] = parsed_order.get("unit_name")

            if not (merged_slots.get("model_number") or merged_slots.get("product_model")) and first.get("model_number"):
                merged_slots["model_number"] = first.get("model_number")
            if not merged_slots.get("tin_spec") and first.get("tin_spec"):
                merged_slots["tin_spec"] = first.get("tin_spec")
            if not merged_slots.get("quantity_tins") and first.get("quantity_tins"):
                merged_slots["quantity_tins"] = first.get("quantity_tins")

            intent_result["slots"] = merged_slots
        except Exception:
            pass

        return intent_result

    def _update_context_from_intent(
        self,
        conv_context: ConversationContext,
        intent_result: Dict[str, Any]
    ) -> None:
        """
        从意图结果更新对话上下文

        Args:
            conv_context: 对话上下文
            intent_result: 意图识别结果
        """
        conv_context.current_intent = intent_result.get("final_intent") or intent_result.get("primary_intent")
        conv_context.current_tool_key = intent_result.get("tool_key")
        conv_context.intent_hints = intent_result.get("intent_hints", [])
        conv_context.last_intent_result = intent_result

    def _get_or_create_context(
        self,
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> ConversationContext:
        """
        获取或创建对话上下文

        Args:
            user_id: 用户 ID
            context: 客户端附加的键值上下文

        Returns:
            对话上下文对象
        """
        conv_context = self.get_context(user_id)
        if not conv_context:
            conv_context = self.create_context(user_id)
        enriched = self._enrich_context_with_kitten_business_snapshot(context)
        self._apply_request_context(conv_context, enriched)
        return conv_context

    async def _handle_special_intents(
        self,
        message: str,
        intent_result: Dict[str, Any],
        conv_context: ConversationContext,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        处理特殊意图（确认、否定、问候、再见、帮助、硬规则）

        Args:
            message: 用户消息
            intent_result: 意图识别结果
            conv_context: 对话上下文
            user_id: 用户 ID

        Returns:
            如果处理了特殊意图返回响应字典，否则返回 None
        """
        if result := await self._handle_confirmation_intent(message, intent_result, conv_context, user_id):
            return result

        if result := await self._handle_negation_intent(message, intent_result, conv_context, user_id):
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
        intent_result: Dict[str, Any],
        conv_context: ConversationContext,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        处理确认意图（用户说"是/好的/确认"）

        Args:
            message: 用户消息
            intent_result: 意图识别结果
            conv_context: 对话上下文
            user_id: 用户 ID

        Returns:
            如果处理了确认意图返回响应字典，否则返回 None
        """
        if not intent_result.get("is_confirmation"):
            return None

        confirmation_pending = conv_context.pending_confirmation or self.confirmation_service.get_pending_intent(user_id)
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
            slots=params
        )

        self.record_user_action(
            user_id=user_id,
            intent=pending.get("intent", action_type),
            slots=params,
            message=message
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
                }
            }

        return None

    async def _handle_negation_intent(
        self,
        message: str,
        intent_result: Dict[str, Any],
        conv_context: ConversationContext,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        处理否定意图（用户说"否/不要/取消"）

        Args:
            message: 用户消息
            intent_result: 意图识别结果
            conv_context: 对话上下文
            user_id: 用户 ID

        Returns:
            如果处理了否定意图返回响应字典，否则返回 None
        """
        if intent_result.get("is_negated") and conv_context.pending_confirmation:
            pending_intent = conv_context.pending_confirmation.get("intent", "")
            self.add_intent_feedback(
                user_id=user_id,
                message=message,
                recognized_intent=pending_intent,
                feedback="negated",
                slots=conv_context.pending_confirmation.get("slots", {})
            )
            conv_context.pending_confirmation = None
            return None

        if intent_result.get("is_negation_intent") and not conv_context.pending_confirmation and len(message) < 10:
            conv_context.last_action = "user_negated"
            self.add_intent_feedback(
                user_id=user_id,
                message=message,
                recognized_intent=conv_context.current_intent or "",
                feedback="negated",
                slots=conv_context.last_intent_result.get("slots", {}) if conv_context.last_intent_result else {}
            )
            return {
                "text": "好的，已取消。有其他需要帮助的吗？",
                "action": "negated",
                "data": {}
            }

        return None

    async def _handle_pending_intent(
        self,
        message: str,
        intent_result: Dict[str, Any],
        conv_context: ConversationContext,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        处理 pending 意图（多轮对话中的槽位填充）

        Args:
            message: 用户消息
            intent_result: 意图识别结果
            conv_context: 对话上下文
            user_id: 用户 ID

        Returns:
            如果处理了 pending 意图返回响应字典，否则返回 None
        """
        pending = self.confirmation_service.get_pending_intent(user_id)
        if not pending:
            return None

        current_tool_key = intent_result.get("tool_key")

        if pending and (intent_result.get("is_greeting") or intent_result.get("is_goodbye") or intent_result.get("is_help")):
            logger.info(f"[DEBUG_PENDING] 检测到特殊意图，清除 pending")
            self.confirmation_service.clear_pending_intent(user_id)
            return None

        if current_tool_key and current_tool_key != pending.get("intent"):
            pending_intent = pending.get("intent")
            if pending_intent not in (current_tool_key, intent_result.get("primary_intent")):
                logger.info(f"[DEBUG_PENDING] 检测到新意图 {current_tool_key} 与 pending 意图 {pending_intent} 不同，清除 pending")
                self.confirmation_service.clear_pending_intent(user_id)
                return None

        return await self._fill_pending_slots(message, pending, user_id)

    async def _fill_pending_slots(
        self,
        message: str,
        pending: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        填充 pending 意图的槽位

        Args:
            message: 用户消息
            pending: 待处理的 pending 意图
            user_id: 用户 ID

        Returns:
            响应字典
        """
        logger.info("[DEBUG_PENDING] 检测到 pending 意图存在，将使用本地规则提取槽位")
        local_result = self.intent_service(message)
        new_slots = local_result.get("slots", {})
        logger.info(f"[DEBUG_PENDING] 本地提取的 slots: {new_slots}")
        merged_slots = self.confirmation_service.merge_slots(user_id, new_slots)
        logger.info(f"[DEBUG_PENDING] 合并后的 slots: {merged_slots}")

        check_result = self.confirmation_service.check_and_build_prompt({
            "final_intent": pending.get("intent"),
            "slots": merged_slots,
        })
        logger.info(f"[DEBUG_PENDING] check_result status: {check_result.get('status')}, missing: {check_result.get('missing_slots')}")

        if check_result["status"] == "complete":
            return self._build_pending_complete_response(pending, merged_slots, user_id)
        else:
            return self._build_pending_incomplete_response(pending, merged_slots, check_result, user_id)

    def _build_pending_complete_response(
        self,
        pending: Dict[str, Any],
        merged_slots: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        构建 pending 槽位完整的响应

        Args:
            pending: 待处理的 pending 意图
            merged_slots: 合并后的槽位
            user_id: 用户 ID

        Returns:
            响应字典
        """
        pending_intent = pending.get("intent", "")
        action_texts = {
            "shipment_generate": f"正在为 {merged_slots.get('unit_name', '该客户')} 生成发货单",
            "products": f"正在查询 {merged_slots.get('unit_name', merged_slots.get('keyword', '该产品'))} 的产品信息",
            "customers": f"正在查询客户信息",
            "shipments": f"正在查询发货记录",
            "print_label": f"正在处理标签打印",
            "wechat_send": f"正在发送微信消息",
            "upload_file": f"正在上传文件",
        }
        action_text = action_texts.get(pending_intent, f"正在处理 {pending_intent}")
        self.confirmation_service.set_pending_intent(user_id, {
            "intent": pending.get("intent"),
            "slots": merged_slots,
            "missing_slots": [],
        })
        return {
            "text": f"好的，已收到您的信息，{action_text}...",
            "action": "tool_call",
            "data": {
                "tool_key": pending.get("intent"),
                "intent": pending.get("intent"),
                "slots": merged_slots,
            }
        }

    def _build_pending_incomplete_response(
        self,
        pending: Dict[str, Any],
        merged_slots: Dict[str, Any],
        check_result: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        构建 pending 槽位不完整的响应

        Args:
            pending: 待处理的 pending 意图
            merged_slots: 合并后的槽位
            check_result: 槽位检查结果
            user_id: 用户 ID

        Returns:
            响应字典
        """
        self.confirmation_service.set_pending_intent(user_id, {
            "intent": pending.get("intent"),
            "slots": merged_slots,
            "missing_slots": check_result["missing_slots"],
        })
        return {
            "text": check_result["question"],
            "action": "slot_fill",
            "data": {
                "intent": pending.get("intent"),
                "slots": merged_slots,
                "missing_slots": check_result["missing_slots"],
            }
        }

    async def _execute_or_generate_response(
        self,
        message: str,
        intent_result: Dict[str, Any],
        conv_context: ConversationContext,
        user_id: str
    ) -> Dict[str, Any]:
        """
        执行工具调用或生成 AI 响应

        Args:
            message: 用户消息
            intent_result: 意图识别结果
            conv_context: 对话上下文
            user_id: 用户 ID

        Returns:
            响应字典
        """
        final_intent = intent_result.get("final_intent") or intent_result.get("primary_intent")
        slots = intent_result.get("slots", {})

        pending = self.confirmation_service.get_pending_intent(user_id)
        if pending:
            slots = self.confirmation_service.merge_slots(user_id, slots)

        check_result = self.confirmation_service.check_and_build_prompt({
            "final_intent": final_intent,
            "slots": slots,
        })

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
                }
            }

        tool_key = intent_result.get("tool_key")
        if tool_key:
            return self._build_tool_call_response(tool_key, slots, intent_result, user_id, check_result)

        if intent_result.get("ai_mode") == "offline":
            return await self._call_ai_offline(message, conv_context, intent_result)

        return await self._call_ai(message, conv_context, intent_result)

    def _build_tool_call_response(
        self,
        tool_key: str,
        slots: Dict[str, Any],
        intent_result: Dict[str, Any],
        user_id: str,
        check_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        构建工具调用响应

        Args:
            tool_key: 工具键
            slots: 槽位信息
            intent_result: 意图识别结果
            user_id: 用户 ID
            check_result: 槽位检查结果

        Returns:
            响应字典
        """
        tool_action_texts = {
            "shipment_generate": f"正在为 {slots.get('unit_name', slots.get('keyword', '该客户'))} 生成发货单",
            "products": f"正在查询 {slots.get('unit_name', slots.get('keyword', '该产品'))} 的产品信息",
            "customers": f"正在查询客户信息",
            "shipments": f"正在查询发货记录",
            "print_label": f"正在处理标签打印",
            "wechat_send": f"正在发送微信消息",
            "upload_file": f"正在上传文件",
            "materials": f"正在查询原材料库存",
            "shipment_template": f"正在查询发货单模板",
            "template_extract": f"正在提取模板结构",
            "business_docking": f"正在执行业务对接模板提取",
            "template_preview": f"正在查询模板预览",
            "shipment_records": f"正在查询出货记录",
            "wechat": f"正在处理微信联系人能力",
            "printer_list": f"正在查询打印机配置",
            "settings": f"正在读取系统设置",
            "tools_table": f"正在加载工具能力表",
            "other_tools": f"正在查询其他工具能力",
            "ai_ecosystem": f"正在查询AI生态能力",
            "excel_decompose": f"正在分解Excel模板",
            "excel_analyzer": f"正在分析Excel结构",
            "show_images": f"正在查看图片",
            "show_videos": f"正在查看视频",
        }
        action_text = tool_action_texts.get(tool_key, f"正在处理工具调用：{tool_key}")

        habit_suggestion = self._check_habit_suggestion(user_id, tool_key, slots)
        if habit_suggestion:
            action_text = f"{action_text} {habit_suggestion}"

        self.confirmation_service.set_pending_intent(user_id, {
            "intent": intent_result.get("final_intent") or intent_result.get("primary_intent"),
            "slots": slots,
            "missing_slots": check_result.get("missing_slots", []) if check_result.get("status") == "missing_slots" else [],
        })
        return {
            "text": f"好的，{action_text}...",
            "action": "tool_call",
            "data": {
                "tool_key": tool_key,
                "intent": intent_result.get("final_intent") or intent_result.get("primary_intent"),
                "slots": slots,
                "hints": intent_result.get("intent_hints", []),
                "habit_suggestion": habit_suggestion
            }
        }

    async def chat(
        self,
        user_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理用户聊天消息

        Args:
            user_id: 用户 ID
            message: 用户消息
            context: 客户端附加的键值上下文（会合并进会话 metadata.request_context，
                经 _build_context_prompt 写入 system 提示；如 kitten_dataset 表格摘要）
            source: 来源标识（pro 表示专业模式，使用 unified_recognizer）

        Returns:
            对话响应字典
        """
        try:
            conv_context = self._get_or_create_context(user_id, context)

            intent_result = await self._recognize_intent(message, source, user_id, context)
            intent_result = self._enhance_intent_slots(message, intent_result, user_id)

            logger.info(f"[INTENT_RESULT] final_intent={intent_result.get('final_intent')}, primary_intent={intent_result.get('primary_intent')}, tool_key={intent_result.get('tool_key')}, slots={intent_result.get('slots')}, intent_source={intent_result.get('intent_source')}")
            self._update_context_from_intent(conv_context, intent_result)

            if result := await self._handle_special_intents(message, intent_result, conv_context, user_id):
                return result

            if result := await self._handle_pending_intent(message, intent_result, conv_context, user_id):
                return result

            return await self._execute_or_generate_response(message, intent_result, conv_context, user_id)

        except Exception as e:
            logger.error(f"处理聊天消息失败：{e}")
            return {
                "text": f"抱歉，处理消息时出现问题：{str(e)}",
                "action": "error",
                "data": {"error": str(e)}
            }

    async def _handle_greeting(
        self,
        message: str,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """处理问候消息"""
        responses = [
            "您好！我是 XCAGI 智能助手，很高兴为您服务！😊\n\n我可以帮您：\n• 生成发货单\n• 管理产品和客户\n• 处理订单\n• 回答各种问题\n\n请问有什么可以帮您？",
            "你好呀！👋 我是您的智能助手，随时准备帮助您处理业务问题。\n\n需要我帮您做什么呢？",
            "您好！欢迎使用 XCAGI 系统！\n\n我可以协助您处理日常业务，比如开单、查询产品、管理客户等。\n\n今天需要我帮您做什么？"
        ]
        
        response_text = responses[hash(message) % len(responses)]
        
        self.add_to_history(context.user_id, "user", message)
        self.add_to_history(context.user_id, "assistant", response_text)
        
        return {
            "text": response_text,
            "action": "greeting",
            "data": {}
        }
    
    async def _handle_goodbye(
        self,
        message: str,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """处理告别消息"""
        responses = [
            "再见！祝您工作顺利！👋 如有需要，随时联系我。",
            "好的，再见！😊 期待下次为您服务！",
            "拜拜！👋 有任何问题都可以随时找我哦！"
        ]
        
        response_text = responses[hash(message) % len(responses)]
        
        self.add_to_history(context.user_id, "user", message)
        self.add_to_history(context.user_id, "assistant", response_text)
        
        return {
            "text": response_text,
            "action": "goodbye",
            "data": {}
        }
    
    async def _handle_help(
        self,
        message: str,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """处理帮助请求"""
        help_text = """🤖 XCAGI 智能助手功能介绍

📦 **发货单管理**
• 生成发货单：说"生成发货单"或"开单"
• 查看发货单模板：问"发货单模板"或"当前模板"

📊 **数据查询**
• 产品查询：问"产品列表"或"产品库"
• 客户查询：问"客户列表"或"购货单位"
• 出货记录：问"出货记录"或"订单列表"
• 库存查询：问"原材料库存"或"材料库"

📤 **文件处理**
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
        
        return {
            "text": help_text,
            "action": "help",
            "data": {}
        }

    def _enrich_context_with_kitten_business_snapshot(
        self, context: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """小猫分析：在请求进入合并逻辑前按需拉取业务库快照（原材料/产品/出货）。"""
        if not isinstance(context, dict):
            return context
        if not context.get("kitten_analyzer"):
            return context
        out = dict(context)
        if out.get("kitten_include_business_db"):
            try:
                from app.services.kitten_business_snapshot import (
                    build_kitten_business_snapshot,
                )

                out["kitten_business_snapshot"] = build_kitten_business_snapshot()
            except Exception as exc:
                logger.warning("kitten business snapshot build failed: %s", exc)
                out["kitten_business_snapshot"] = {
                    "success": False,
                    "text": f"【业务数据库快照】生成失败：{exc}",
                    "stats": {},
                }
        else:
            out.pop("kitten_business_snapshot", None)
        return out

    def _apply_request_context(
        self,
        conv_context: ConversationContext,
        ctx: Optional[Dict[str, Any]],
    ) -> None:
        """将本次 HTTP 请求中的 context 合并进 metadata.request_context，供 system 提示使用。"""
        if ctx is None:
            return
        if not ctx:
            return
        prev = (conv_context.metadata or {}).get("request_context") or {}
        merged: Dict[str, Any] = {**prev, **ctx}
        if ctx.get("kitten_analyzer") and ctx.get("has_dataset") is False:
            merged.pop("kitten_dataset", None)
        elif "kitten_dataset" in ctx:
            if ctx["kitten_dataset"]:
                merged["kitten_dataset"] = self._sanitize_kitten_dataset(ctx["kitten_dataset"])
            else:
                merged.pop("kitten_dataset", None)
        elif prev.get("kitten_dataset"):
            merged["kitten_dataset"] = prev["kitten_dataset"]

        if ctx.get("kitten_analyzer"):
            if ctx.get("kitten_include_business_db") and ctx.get("kitten_business_snapshot"):
                merged["kitten_business_snapshot"] = self._sanitize_kitten_business_snapshot(
                    ctx["kitten_business_snapshot"]
                )
            else:
                merged.pop("kitten_business_snapshot", None)
        conv_context.metadata.setdefault("request_context", {})
        conv_context.metadata["request_context"] = merged
        conv_context.updated_at = time.time()

    def _sanitize_kitten_dataset(self, kd: Any) -> Dict[str, Any]:
        """限制字段长度，避免 system 提示过大。"""
        if not isinstance(kd, dict):
            return {}
        out = dict(kd)
        pt = out.get("preview_text")
        if isinstance(pt, str) and len(pt) > 12000:
            out["preview_text"] = pt[:12000] + "\n…（已截断）"
        fields = out.get("fields") if isinstance(out.get("fields"), list) else out.get("field_names")
        if isinstance(fields, list) and len(fields) > 200:
            out["fields"] = [str(x) for x in fields[:200]]
            out["fields_truncated"] = True
        elif isinstance(fields, list):
            out["fields"] = [str(x) for x in fields]
        return out

    def _sanitize_kitten_business_snapshot(self, snap: Any) -> Dict[str, Any]:
        if not isinstance(snap, dict):
            return {}
        out = dict(snap)
        pt = out.get("text")
        if isinstance(pt, str) and len(pt) > 14000:
            out["text"] = pt[:14000] + "\n…（已截断）"
        return out

    def _format_kitten_business_snapshot_block(self, snap: Optional[Any]) -> str:
        if snap is None or (isinstance(snap, dict) and not snap):
            return ""
        if not isinstance(snap, dict):
            return ""
        preview = snap.get("text")
        if not isinstance(preview, str) or not preview.strip():
            return ""
        head = "【小猫分析 · 业务数据库快照】"
        ga = snap.get("generated_at")
        if ga:
            head += f"（生成时间 {ga}）"
        return f"{head}\n{preview.strip()}"

    def _format_kitten_dataset_block(self, kd: Optional[Any]) -> str:
        if kd is None or (isinstance(kd, dict) and not kd):
            return (
                "【小猫分析】当前未附带表格数据，请根据通用数据分析知识回答用户问题。"
            )
        if not isinstance(kd, dict):
            return ""
        lines = ["【小猫分析 · 数据上下文】"]
        fn = kd.get("file_name") or kd.get("name")
        if fn:
            lines.append(f"文件名：{fn}")
        if kd.get("rows") is not None:
            lines.append(f"行数：{kd.get('rows')}")
        if kd.get("columns") is not None:
            lines.append(f"列数：{kd.get('columns')}")
        fields = kd.get("fields") or kd.get("field_names")
        if isinstance(fields, (list, tuple)) and fields:
            lines.append(f"字段：{', '.join(str(x) for x in fields[:80])}")
            if len(fields) > 80:
                lines.append("…（字段列表已省略）")
        preview = kd.get("preview_text")
        if isinstance(preview, str) and preview.strip():
            lines.append("样本行（供理解表格结构）：")
            lines.append(preview.strip())
        lines.append("（若字段名为 __EMPTY 等占位，请结合样本行推断含义。）")
        return "\n".join(lines)

    def _format_request_context_for_system(self, req: Optional[Dict[str, Any]]) -> str:
        """将 metadata.request_context 格式化为并入 system 的文本块。"""
        if not req or not isinstance(req, dict):
            return ""
        blocks: List[str] = []
        if req.get("kitten_analyzer"):
            blocks.append(self._format_kitten_dataset_block(req.get("kitten_dataset")))
            db_block = self._format_kitten_business_snapshot_block(
                req.get("kitten_business_snapshot")
            )
            if db_block:
                blocks.append(db_block)
        excel_vector_ctx = req.get("excel_vector_context")
        if isinstance(excel_vector_ctx, dict):
            blocks.append(self._format_excel_vector_block(excel_vector_ctx))
        extra = {
            k: v
            for k, v in req.items()
            if k not in (
                "kitten_analyzer",
                "has_dataset",
                "kitten_dataset",
                "kitten_include_business_db",
                "kitten_business_snapshot",
                "excel_vector_context",
            )
        }
        if extra:
            try:
                dumped = json.dumps(extra, ensure_ascii=False, default=str)
                if len(dumped) > 4096:
                    dumped = dumped[:4096] + "…"
                blocks.append(f"【附加上下文】\n{dumped}")
            except Exception:
                pass
        merged = "\n\n".join(b for b in blocks if b)
        return merged

    def _format_excel_vector_block(self, payload: Dict[str, Any]) -> str:
        """格式化 Excel 检索结果，作为回答依据写入 system prompt。"""
        index_id = str(payload.get("index_id") or "").strip()
        query = str(payload.get("query") or "").strip()
        hits = payload.get("hits") if isinstance(payload.get("hits"), list) else []
        lines = ["【Excel语义检索上下文】"]
        if index_id:
            lines.append(f"索引ID：{index_id}")
        if query:
            lines.append(f"问题：{query}")
        if not hits:
            lines.append("未召回相关内容。")
            lines.append("若信息不足，请明确告知用户并引导其补充筛选条件。")
            return "\n".join(lines)

        lines.append("以下是最相关的表格片段（按相关度排序）：")
        for idx, hit in enumerate(hits[:8], start=1):
            score = float(hit.get("score", 0.0))
            metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
            sheet = str(metadata.get("sheet") or "-")
            row_index = metadata.get("row_index")
            content = str(hit.get("content") or "").strip()
            if len(content) > 600:
                content = content[:600] + "..."
            if row_index is not None:
                lines.append(f"{idx}. sheet={sheet}, row={row_index}, score={score:.4f}")
            else:
                lines.append(f"{idx}. sheet={sheet}, score={score:.4f}")
            lines.append(content)
        lines.append("回答时优先引用以上片段，不要编造未出现的数据。")
        return "\n".join(lines)

    def _metadata_cache_hash(self, metadata: Optional[Dict[str, Any]]) -> str:
        """metadata 可能含嵌套 dict，避免 sorted(items) 因类型不可比较而抛错。"""
        if not metadata:
            return ""
        try:
            return hashlib.md5(
                json.dumps(metadata, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
            ).hexdigest()
        except Exception:
            return str(hash(frozenset(metadata.keys())))

    def _build_context_prompt(self, context: ConversationContext) -> str:
        """构建意图上下文提示（含 HTTP request_context 并入的 system 块）"""
        blocks: List[str] = []
        req = (context.metadata or {}).get("request_context")
        req_block = self._format_request_context_for_system(req)
        if req_block:
            blocks.append(req_block)

        session_parts: List[str] = []
        if context.current_intent:
            session_parts.append(f"当前会话意图：{context.current_intent}")
        if context.current_tool_key:
            session_parts.append(f"当前工具：{context.current_tool_key}")
        if context.intent_hints:
            session_parts.append(f"意图线索：{', '.join(context.intent_hints)}")
        if context.pending_confirmation:
            action = context.pending_confirmation.get("action", "")
            desc = context.pending_confirmation.get("description", "")
            session_parts.append(f"待确认操作：{action} - {desc}")
        if context.last_action:
            session_parts.append(f"最近操作：{context.last_action}")
        if session_parts:
            blocks.append(
                "【当前会话上下文】\n"
                + "\n".join(session_parts)
                + "\n【 END会话上下文 】"
            )
        if not blocks:
            return ""
        return "\n\n".join(blocks)

    def _check_habit_suggestion(
        self,
        user_id: str,
        current_intent: str,
        slots: Dict[str, Any]
    ) -> Optional[str]:
        """
        检查操作习惯并返回主动提示

        Args:
            user_id: 用户ID
            current_intent: 当前意图
            slots: 当前槽位

        Returns:
            习惯提示文本或 None
        """
        try:
            habits = self.get_habit_suggestions(user_id)

            for habit in habits:
                actions = habit.get("actions", [])
                confidence = habit.get("confidence", 0)

                if confidence < 0.8:
                    continue

                if len(actions) >= 2 and actions[0] == current_intent:
                    next_action = actions[1]
                    if next_action == "print_label" and current_intent == "shipment_generate":
                        return "（是否需要同时打印标签？）"
                    elif next_action == "wechat_send" and current_intent == "shipment_generate":
                        return "（是否需要发送微信通知？）"

            return None
        except Exception as e:
            logger.error(f"检查习惯建议失败: {e}")
            return None

    def _check_hard_rules(self, message: str) -> Optional[Dict[str, Any]]:
        """
        检查硬规则意图（高优先级规则，直接返回特定 action）

        Args:
            message: 用户消息

        Returns:
            如果命中硬规则返回响应字典，否则返回 None
        """
        msg = message.strip()
        msg_lower = msg.lower()

        export_keywords = ["导出excel", "导出xlsx", "导出表格", "导出用户列表", "导出客户列表", "导出购买单位", "导出单位"]
        export_context_keywords = ["用户", "客户", "购买单位", "单位", "名单", "列表"]
        export_hit = any(k in msg_lower for k in export_keywords)
        export_with_context = ("导出" in msg) and any(k in msg for k in export_context_keywords)

        if export_hit or export_with_context:
            return {
                "text": "已开始导出购买单位列表为 XLSX，下载将自动开始。",
                "action": "auto_action",
                "data": {"type": "export_customers_xlsx"}
            }

        # 工作模式开关（前端 pro-mode.js 依赖 autoAction.type = set_work_mode 来切换动画/红色主题）
        if "工作模式" in msg:
            if any(k in msg for k in ["进入", "开启", "打开", "开始", "启动"]) or msg in ["工作模式", "进入工作模式", "开启工作模式"]:
                return {
                    "text": "已进入工作模式，球体已切换为红色；将开始监控列表并每 10 秒刷新。",
                    "action": "auto_action",
                    "data": {"type": "set_work_mode", "enabled": True}
                }
            if any(k in msg for k in ["退出", "关闭", "停止", "结束"]) or msg in ["退出工作模式", "关闭工作模式"]:
                return {
                    "text": "已退出工作模式，球体已恢复为青色；监控列表与每 10 秒刷新已停止。",
                    "action": "auto_action",
                    "data": {"type": "set_work_mode", "enabled": False}
                }

        customer_list_keywords = [
            "购买单位列表", "客户列表", "查看客户", "查看用户列表",
            "用户列表", "用户名单", "客户名单", "单位列表"
        ]

        if any(k in msg for k in customer_list_keywords):
            return {
                "text": "已打开客户/购买单位列表，支持右侧编辑；也可直接说「把 XX 的电话改成 138xxxx」等。",
                "action": "auto_action",
                "data": {"type": "show_customers"}
            }

        product_list_keywords = ["产品列表", "产品库", "商品列表", "查看产品"]
        if any(k in msg for k in product_list_keywords):
            return {
                "text": "已打开产品列表，支持查看和搜索。",
                "action": "auto_action",
                "data": {"type": "show_products"}
            }

        monitor_keywords = ["监控模式", "进入监控模式", "开启监控模式", "打开监控模式"]
        if any(k in msg for k in monitor_keywords):
            return {
                "text": "已进入监控模式，可以查看系统 CPU、内存、磁盘使用情况以及服务状态。",
                "action": "auto_action",
                "data": {"type": "show_monitor"}
            }

        return None

    async def _call_ai(
        self,
        message: str,
        context: ConversationContext,
        intent_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用 AI 进行回复

        Args:
            message: 用户消息
            context: 对话上下文
            intent_result: 意图识别结果

        Returns:
            AI 回复
        """
        context_hash = self._metadata_cache_hash(context.metadata)
        cache_key = _make_ai_response_cache_key(message, context_hash)
        cached_response = _ai_response_cache.get(cache_key)
        if cached_response:
            logger.debug("返回缓存的 AI 响应")
            return {
                "text": cached_response,
                "action": "ai_response",
                "data": {
                    "model": self.model,
                    "cached": True,
                    "intent": intent_result
                }
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

        logger.info(f"准备调用 DeepSeek API，API Key 长度: {len(self.api_key)}")

        response = await self.call_deepseek_api(messages)

        logger.info(f"DeepSeek API 响应: {response}")

        if response and response.get("choices"):
            ai_reply = response["choices"][0]["message"]["content"]

            self.add_to_history(context.user_id, "user", message)
            self.add_to_history(context.user_id, "assistant", ai_reply)

            _ai_response_cache.set(cache_key, ai_reply)

            return {
                "text": ai_reply,
                "action": "ai_response",
                "data": {
                    "model": self.model,
                    "usage": response.get("usage", {}),
                    "intent": intent_result
                }
            }
        else:
            fallback_reply = "抱歉，我暂时无法理解您的需求。您可以：\n• 重新描述您的问题\n• 使用更简单的语句\n• 联系人工客服获取帮助\n\n如果需要帮助，请说\"帮助\"或\"功能介绍\"。"

            self.add_to_history(context.user_id, "user", message)
            self.add_to_history(context.user_id, "assistant", fallback_reply)

            return {
                "text": fallback_reply,
                "action": "fallback",
                "data": {"intent": intent_result}
            }
    
    def clear_context(self, user_id: str) -> bool:
        """
        清除用户对话上下文
        
        Args:
            user_id: 用户 ID
            
        Returns:
            是否清除成功
        """
        if user_id in self.contexts:
            del self.contexts[user_id]
            logger.info(f"已清除用户 {user_id} 的对话上下文")
            return True
        return False
    
    def get_all_contexts(self) -> Dict[str, ConversationContext]:
        """获取所有对话上下文"""
        return self.contexts.copy()
    
    def cleanup_old_contexts(self, max_age_seconds: int = 3600) -> int:
        """
        清理过期的对话上下文
        
        Args:
            max_age_seconds: 最大保留时间（秒）
            
        Returns:
            清理的上下文数量
        """
        current_time = time.time()
        to_remove = []
        
        for user_id, context in self.contexts.items():
            if current_time - context.updated_at > max_age_seconds:
                to_remove.append(user_id)
        
        for user_id in to_remove:
            del self.contexts[user_id]
        
        if to_remove:
            logger.info(f"清理了 {len(to_remove)} 个过期的对话上下文")
        
        return len(to_remove)


# 全局服务实例
_ai_conversation_service: Optional[AIConversationService] = None


def get_ai_conversation_service() -> AIConversationService:
    """获取 AI 对话服务单例"""
    global _ai_conversation_service
    if _ai_conversation_service is None:
        _ai_conversation_service = AIConversationService()
    return _ai_conversation_service


def init_ai_conversation_service() -> AIConversationService:
    """初始化 AI 对话服务"""
    global _ai_conversation_service
    _ai_conversation_service = AIConversationService()
    logger.info("AI 对话服务已初始化")
    return _ai_conversation_service
