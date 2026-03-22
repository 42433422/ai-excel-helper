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
import logging
import os
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.user_memory_service import get_user_memory_service
from app.utils.cache_manager import get_ai_response_cache

logger = logging.getLogger(__name__)


class _AIResponseCache:
    def __init__(self, max_size: int = 500, ttl_seconds: int = 300):
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds

    def _make_key(self, message: str, context_hash: str = "") -> str:
        key_str = f"{context_hash}:{message.strip().lower()}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, message: str, context_hash: str = "") -> Optional[str]:
        key = self._make_key(message, context_hash)
        if key not in self._cache:
            return None
        if time.time() - self._timestamps.get(key, 0) > self._ttl:
            del self._cache[key]
            del self._timestamps[key]
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, message: str, response: str, context_hash: str = "") -> None:
        key = self._make_key(message, context_hash)
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
        self._cache[key] = response
        self._timestamps[key] = time.time()

    def clear(self) -> None:
        self._cache.clear()
        self._timestamps.clear()


_ai_response_cache = get_ai_response_cache()


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
        from .deepseek_intent_service import get_hybrid_intent_with_deepseek
        from .intent_confirmation_service import get_confirmation_service
        from .intent_service import recognize_intents
        from .task_agent import get_task_agent
        from .unified_intent_recognizer import get_unified_intent_recognizer
        self.intent_service = recognize_intents
        self.deepseek_intent_service = get_hybrid_intent_with_deepseek(
            use_deepseek=True,
            rule_priority=True,
            confidence_threshold=0.6
        )
        self.unified_recognizer = get_unified_intent_recognizer()
        self.confirmation_service = get_confirmation_service()
        self.task_agent = get_task_agent()
        self.user_memory = get_user_memory_service()

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
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get("choices") and len(result["choices"]) > 0:
                    return result
                else:
                    logger.warning(f"DeepSeek API 返回空响应：{result}")
                    return None
                    
        except httpx.HTTPError as e:
            logger.error(f"DeepSeek API 请求失败：{e}")
            return None
        except Exception as e:
            logger.error(f"调用 DeepSeek API 异常：{e}")
            return None
    
    async def chat(
        self,
        user_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户聊天消息
        
        Args:
            user_id: 用户 ID
            message: 用户消息
            context: 额外上下文信息
            
        Returns:
            对话响应字典
        """
        try:
            # 获取或创建对话上下文
            conv_context = self.get_context(user_id)
            if not conv_context:
                conv_context = self.create_context(user_id)

            # 意图识别（提前，用于确认检查）
            intent_result = await self.deepseek_intent_service.recognize(message)
            logger.info(f"[INTENT_RESULT] final_intent={intent_result.get('final_intent')}, primary_intent={intent_result.get('primary_intent')}, tool_key={intent_result.get('tool_key')}, slots={intent_result.get('slots')}, intent_source={intent_result.get('intent_source')}")
            conv_context.current_intent = intent_result.get("final_intent") or intent_result.get("primary_intent")
            conv_context.current_tool_key = intent_result.get("tool_key")
            conv_context.intent_hints = intent_result.get("intent_hints", [])
            conv_context.last_intent_result = intent_result

            # 优先处理确认意图（用户说"是/好的/确认"）
            confirmation_pending = conv_context.pending_confirmation or self.confirmation_service.get_pending_intent(user_id)
            if intent_result.get("is_confirmation") and confirmation_pending:
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

            # 清除 pending 意图（当用户说问候/再见/帮助时）
            pending = self.confirmation_service.get_pending_intent(user_id)
            current_tool_key = intent_result.get("tool_key")

            if pending and (intent_result.get("is_greeting") or intent_result.get("is_goodbye") or intent_result.get("is_help")):
                logger.info(f"[DEBUG_PENDING] 检测到特殊意图，清除 pending")
                self.confirmation_service.clear_pending_intent(user_id)
                pending = None

            # 关键修复：如果新消息有明确的工具意图，且与 pending 意图不同，清除 pending
            if pending and current_tool_key and current_tool_key != pending.get("intent"):
                pending_intent = pending.get("intent")
                if pending_intent not in (current_tool_key, intent_result.get("primary_intent")):
                    logger.info(f"[DEBUG_PENDING] 检测到新意图 {current_tool_key} 与 pending 意图 {pending_intent} 不同，清除 pending")
                    self.confirmation_service.clear_pending_intent(user_id)
                    pending = None

            if pending:
                logger.info(f"[DEBUG_PENDING] 检测到 pending 意图存在，将使用本地规则提取槽位")
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
                else:
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

            # 检查是否有待确认的操作
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

            # 否定意图识别：当用户说"否/不要/取消"且无待确认时，可能是否定上一轮AI建议
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

            # 特殊意图处理
            if intent_result.get("is_greeting"):
                return await self._handle_greeting(message, conv_context)

            if intent_result.get("is_goodbye"):
                return await self._handle_goodbye(message, conv_context)

            if intent_result.get("is_help"):
                return await self._handle_help(message, conv_context)

            hard_rule_result = self._check_hard_rules(message)
            if hard_rule_result:
                return hard_rule_result

            # 检查意图槽位是否完整，缺失时反向询问
            final_intent = intent_result.get("final_intent") or intent_result.get("primary_intent")
            slots = intent_result.get("slots", {})
            logger.info(f"[DEBUG_SLOTS] intent_result.keys()={list(intent_result.keys())}, slots={slots}, tool_key={intent_result.get('tool_key')}, deepseek_intent={intent_result.get('deepseek_intent')}")

            # 如果有待确认的意图，尝试合并槽位
            pending = self.confirmation_service.get_pending_intent(user_id)
            if pending:
                slots = self.confirmation_service.merge_slots(user_id, slots)

            check_result = self.confirmation_service.check_and_build_prompt({
                "final_intent": final_intent,
                "slots": slots,
            })
            logger.info(f"[CHECK_RESULT] final_intent={final_intent}, slots={slots}, check_result={check_result}")

            # 槽位缺失，需要追问
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

            # 意图完整，保留待确认状态让用户可补充可选信息

            # 如果有明确的工具意图且未被否定，优先使用工具
            tool_key = intent_result.get("tool_key")
            if tool_key:
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
            
            # 调用 DeepSeek AI 进行回复
            return await self._call_ai(message, conv_context, intent_result)
            
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

    def _build_context_prompt(self, context: ConversationContext) -> str:
        """构建意图上下文提示"""
        parts = []
        if context.current_intent:
            parts.append(f"当前会话意图：{context.current_intent}")
        if context.current_tool_key:
            parts.append(f"当前工具：{context.current_tool_key}")
        if context.intent_hints:
            parts.append(f"意图线索：{', '.join(context.intent_hints)}")
        if context.pending_confirmation:
            action = context.pending_confirmation.get("action", "")
            desc = context.pending_confirmation.get("description", "")
            parts.append(f"待确认操作：{action} - {desc}")
        if context.last_action:
            parts.append(f"最近操作：{context.last_action}")
        if parts:
            return "【当前会话上下文】\n" + "\n".join(parts) + "\n【 END上下文 】"
        return ""

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
        context_hash = str(sorted(context.metadata.items())) if context.metadata else ""
        cached_response = _ai_response_cache.get(message, context_hash)
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

            _ai_response_cache.set(message, ai_reply, context_hash)

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
