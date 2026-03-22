"""
DeepSeek 聊天服务

使用 DeepSeek 模型进行对话生成
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str
    content: str


class DeepSeekChatService:
    """
    DeepSeek 聊天服务

    负责：
    - 与 DeepSeek API 交互
    - 管理对话上下文
    - 生成回复
    """

    def __init__(self, api_key: str = None, model: str = "deepseek-chat"):
        self._api_key = api_key
        self._model = model
        self._messages: List[ChatMessage] = []
        self._initialized = False

    def initialize(self):
        """初始化服务"""
        if not self._initialized:
            self._initialized = True

    def chat(self, message: str, system_prompt: str = None) -> str:
        """
        聊天

        Args:
            message: 用户消息
            system_prompt: 系统提示

        Returns:
            助手回复
        """
        self.initialize()

        if system_prompt:
            self._messages.append(ChatMessage(role="system", content=system_prompt))

        self._messages.append(ChatMessage(role="user", content=message))

        response = "这是模拟的 DeepSeek 回复"

        self._messages.append(ChatMessage(role="assistant", content=response))

        return response

    def clear_history(self):
        """清空对话历史"""
        self._messages = []

    def get_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return [
            {"role": m.role, "content": m.content}
            for m in self._messages
        ]


def get_deepseek_chat_service(api_key: str = None) -> DeepSeekChatService:
    """获取 DeepSeek 聊天服务"""
    return DeepSeekChatService(api_key=api_key)
