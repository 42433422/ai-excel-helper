# -*- coding: utf-8 -*-
"""
AI 对话引擎服务：处理 AI 对话、DeepSeek API 调用、上下文管理

提供完整的 AI 对话功能，包括：
- DeepSeek API 集成
- 对话上下文管理
- 工具调用协调
- 特殊场景处理（订单、表格编辑等）
"""

import os
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


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
        
        # 优先使用环境变量，否则使用配置文件中的备用 key
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            # 从 312助手 配置中读取备用 API Key
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "312助手", "config", "deepseek_config.py")
            if os.path.exists(config_path):
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("deepseek_config", config_path)
                    config_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(config_module)
                    self.api_key = getattr(config_module, 'DEEPSEEK_API_KEY', '')
                except Exception as e:
                    logger.warning(f"无法读取备用 API Key 配置: {e}")
        
        # 记录 API Key 状态
        if self.api_key:
            logger.info(f"DeepSeek API Key 已配置 (长度: {len(self.api_key)})")
        else:
            logger.warning("DeepSeek API Key 未配置")
        
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"
        
        # 导入依赖服务
        from .intent_service import recognize_intents
        self.intent_service = recognize_intents
    
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
            
            # 意图识别
            intent_result = self.intent_service(message)
            
            # 特殊意图处理
            if intent_result["is_greeting"]:
                return await self._handle_greeting(message, conv_context)
            
            if intent_result["is_goodbye"]:
                return await self._handle_goodbye(message, conv_context)
            
            if intent_result["is_help"]:
                return await self._handle_help(message, conv_context)

            hard_rule_result = self._check_hard_rules(message)
            if hard_rule_result:
                return hard_rule_result

            # 如果有明确的工具意图且未被否定，优先使用工具
            if intent_result["tool_key"]:
                return {
                    "text": f"正在处理工具调用：{intent_result['tool_key']}",
                    "action": "tool_call",
                    "data": {
                        "tool_key": intent_result["tool_key"],
                        "intent": intent_result["primary_intent"],
                        "hints": intent_result["intent_hints"]
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
        # 构建系统提示
        system_prompt = """你是一个专业的业务助手，服务于使用 XCAGI 系统的用户。
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

        # 构建消息历史
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加最近的对话历史（最多 10 条）
        if context.conversation_history:
            messages.extend(context.conversation_history[-10:])
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": message})
        
        logger.info(f"准备调用 DeepSeek API，API Key 长度: {len(self.api_key)}")
        
        # 调用 DeepSeek API
        response = await self.call_deepseek_api(messages)
        
        logger.info(f"DeepSeek API 响应: {response}")
        
        if response and response.get("choices"):
            ai_reply = response["choices"][0]["message"]["content"]
            
            # 添加到历史记录
            self.add_to_history(context.user_id, "user", message)
            self.add_to_history(context.user_id, "assistant", ai_reply)
            
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
            # AI 调用失败，使用兜底回复
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
