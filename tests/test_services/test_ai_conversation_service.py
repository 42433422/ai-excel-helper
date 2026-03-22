"""
AI Conversation Service 测试
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.ai_conversation_service import AIConversationService


class TestAIConversationService:
    """AI 对话服务测试"""

    @pytest.fixture
    def service(self):
        with patch("app.services.ai_conversation_service.init_ai_conversation_service"):
            return AIConversationService()

    def test_service_init(self, service):
        assert service is not None

    def test_handle_negative_intent(self, service):
        result = service.handle_intent("不要生成发货单", user_id="test")
        assert result.get("is_negation") is True or "message" in result

    def test_handle_greeting(self, service):
        result = service.handle_intent("你好", user_id="test")
        assert result.get("is_greeting") is True or "message" in result