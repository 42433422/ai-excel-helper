"""
AI Conversation Service 测试
"""

from unittest.mock import MagicMock, patch

import pytest

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
        from app.services.intent_service import recognize_intents

        result = recognize_intents("不要生成发货单")
        assert result.get("is_negation_intent") or result.get("is_negated")

    def test_handle_greeting(self, service):
        from app.services.intent_service import recognize_intents

        result = recognize_intents("你好")
        assert result.get("is_greeting") is True
