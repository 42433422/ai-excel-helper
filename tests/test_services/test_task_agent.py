"""
Task Agent 服务测试
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.task_agent import TaskAgent, _cn_number, SLOT_LABELS


class TestCnNumber:
    """中文数字解析测试"""

    def test_cn_number_arabic(self):
        assert _cn_number("123") == 123
        assert _cn_number("0") == 0

    def test_cn_number_single_digit(self):
        assert _cn_number("一") == 1
        assert _cn_number("二") == 2
        assert _cn_number("三") == 3

    def test_cn_number_ten(self):
        assert _cn_number("十") == 10

    def test_cn_number_teen(self):
        assert _cn_number("十一") == 11
        assert _cn_number("二十") == 20
        assert _cn_number("二十三") == 23

    def test_cn_number_invalid(self):
        assert _cn_number("") is None
        assert _cn_number("abc") is None

    def test_cn_number_two_variant(self):
        assert _cn_number("两") == 2


class TestSlotLabels:
    """槽位标签测试"""

    def test_slot_labels_contains_expected_keys(self):
        assert "unit_name" in SLOT_LABELS
        assert "model_number" in SLOT_LABELS
        assert "tin_spec" in SLOT_LABELS
        assert "quantity_tins" in SLOT_LABELS


class TestTaskAgent:
    """TaskAgent 测试"""

    @pytest.fixture
    def agent(self):
        with patch("app.services.task_agent.get_task_context_service"):
            return TaskAgent()

    def test_agent_init(self, agent):
        assert agent.ctx is not None

    def test_parse_task_with_greeting(self, agent):
        result = agent.parse_task("你好")
        assert result is None or "task_type" not in result

    def test_extract_query_keyword(self, agent):
        keyword = agent._extract_query_keyword("帮我查一下9803这个产品")
        assert "9803" in keyword or keyword == ""

    def test_extract_product_query_slots(self, agent):
        result = agent._extract_product_query_slots("查一下9803规格的产品")
        assert isinstance(result, dict)

    def test_extract_customer_query_slots(self, agent):
        result = agent._extract_customer_query_slots("查一下七彩乐园这个客户")
        assert isinstance(result, dict)

    def test_parse_qty_token(self, agent):
        assert agent._parse_qty_token("3") == 3
        assert agent._parse_qty_token("三") == 3
        assert agent._parse_qty_token("abc") is None