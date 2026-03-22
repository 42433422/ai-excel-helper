"""
DeepSeek 意图识别服务测试
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.deepseek_intent_service import DeepSeekIntentRecognizer


class TestDeepSeekIntentRecognizer:
    """DeepSeek 意图识别器测试"""

    @pytest.fixture
    def recognizer(self):
        return DeepSeekIntentRecognizer(api_key="test-key", confidence_threshold=0.5)

    def test_recognizer_init(self, recognizer):
        assert recognizer.api_key == "test-key"
        assert recognizer.confidence_threshold == 0.5

    def test_recognizer_has_required_methods(self, recognizer):
        assert hasattr(recognizer, "recognize")
        assert callable(getattr(recognizer, "recognize", None))