"""
AI 聊天应用服务测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestAIChatApplicationService:
    """测试 AI 聊天应用服务"""

    def test_process_chat_empty_message(self):
        """测试空消息处理"""
        with patch('app.application.ai_chat_app_service.get_ai_conversation_service'):
            from app.application.ai_chat_app_service import AIChatApplicationService

            service = AIChatApplicationService()
            result = service.process_chat(
                user_id="test_user",
                message=""
            )

            assert result["success"] is False
            assert "不能为空" in result["message"]

    def test_process_chat_normal_message(self):
        """测试正常消息处理"""
        async def mock_chat(*args, **kwargs):
            return {
                "success": True,
                "text": "你好，有什么可以帮助你的？",
                "action": "followup",
                "data": {}
            }

        mock_ai_service = Mock()
        mock_ai_service.chat = mock_chat

        with patch('app.application.ai_chat_app_service.get_ai_conversation_service', return_value=mock_ai_service):
            from app.application.ai_chat_app_service import AIChatApplicationService

            service = AIChatApplicationService()
            result = service.process_chat(
                user_id="test_user",
                message="你好"
            )

            assert result["success"] is True
            assert result["response"] == "你好，有什么可以帮助你的？"
            assert result["data"]["action"] == "followup"

    def test_confirmation_flow_yes(self):
        """测试确认流程 - 肯定回复"""
        mock_ai_service = Mock()
        mock_ai_service.set_pending_confirmation = Mock()

        with patch('app.application.ai_chat_app_service.get_ai_conversation_service', return_value=mock_ai_service):
            from app.application.ai_chat_app_service import AIChatApplicationService

            service = AIChatApplicationService()
            service.ai_service = mock_ai_service

            file_context = {
                "saved_name": "test_file.xlsx",
                "unit_name_guess": "测试公司",
                "suggested_use": "unit_products_db"
            }

            service._handle_confirmation_flow("test_user", "是", file_context)

            mock_ai_service.set_pending_confirmation.assert_called_once()

    def test_confirmation_flow_no(self):
        """测试确认流程 - 否定回复"""
        mock_ai_service = Mock()

        with patch('app.application.ai_chat_app_service.get_ai_conversation_service', return_value=mock_ai_service):
            from app.application.ai_chat_app_service import AIChatApplicationService

            service = AIChatApplicationService()
            service.ai_service = mock_ai_service

            file_context = {
                "saved_name": "test_file.xlsx",
                "unit_name_guess": "测试公司",
                "suggested_use": "unit_products_db"
            }

            service._handle_confirmation_flow("test_user", "否", file_context)

            mock_ai_service.set_pending_confirmation.assert_not_called()

    def test_build_response_followup(self):
        """测试构建 followup 响应"""
        with patch('app.application.ai_chat_app_service.get_ai_conversation_service'):
            from app.application.ai_chat_app_service import AIChatApplicationService

            service = AIChatApplicationService()

            ai_result = {
                "text": "请提供更多信息",
                "action": "followup",
                "data": {"key": "value"}
            }

            result = service._build_response(ai_result, None, "")

            assert result["success"] is True
            assert result["followup"] == {"key": "value"}

    def test_build_response_auto_action(self):
        """测试构建 auto_action 响应"""
        with patch('app.application.ai_chat_app_service.get_ai_conversation_service'):
            from app.application.ai_chat_app_service import AIChatApplicationService

            service = AIChatApplicationService()

            ai_result = {
                "text": "正在执行...",
                "action": "auto_action",
                "data": {"type": "print", "doc_id": 123}
            }

            result = service._build_response(ai_result, None, "")

            assert result["success"] is True
            assert result["autoAction"] == {"type": "print", "doc_id": 123}

    def test_execute_customers_query_success(self):
        """测试执行客户查询成功"""
        mock_customer_app_service = Mock()
        mock_customer_app_service.get_all.return_value = {
            "success": True,
            "data": [
                {"unit_name": "公司A"},
                {"unit_name": "公司B"}
            ]
        }

        with patch('app.application.ai_chat_app_service.get_ai_conversation_service'):
            with patch('app.bootstrap.get_customer_app_service', return_value=mock_customer_app_service):
                from app.application.ai_chat_app_service import AIChatApplicationService

                service = AIChatApplicationService()
                response_data = {"success": True, "data": {}}

                result = service._execute_customers_query(response_data)

                assert "customers" in result["data"]["data"]
                assert "公司A" in result["response"] or "2" in result["response"]

    def test_execute_customers_query_failure(self):
        """测试执行客户查询失败"""
        with patch('app.application.ai_chat_app_service.get_ai_conversation_service'):
            with patch('app.bootstrap.get_customer_app_service', side_effect=Exception("查询失败")):
                from app.application.ai_chat_app_service import AIChatApplicationService

                service = AIChatApplicationService()
                response_data = {"success": True, "data": {}}

                result = service._execute_customers_query(response_data)

                assert "失败" in result["response"]

    def test_build_order_text_from_products(self):
        """测试根据产品列表构建订单文本"""
        with patch('app.application.ai_chat_app_service.get_ai_conversation_service'):
            from app.application.ai_chat_app_service import AIChatApplicationService

            service = AIChatApplicationService()

            products = [
                {"model": "5003", "quantity_tins": 10, "spec": 25},
                {"model": "5004", "quantity_tins": 5, "spec": 25}
            ]

            result = service._build_order_text_from_products("测试公司", products)

            assert "测试公司" in result
            assert "10桶5003规格25" in result
            assert "5桶5004规格25" in result

    def test_build_order_text_empty_products(self):
        """测试空产品列表"""
        with patch('app.application.ai_chat_app_service.get_ai_conversation_service'):
            from app.application.ai_chat_app_service import AIChatApplicationService

            service = AIChatApplicationService()

            result = service._build_order_text_from_products("测试公司", [])

            assert result == ""

    def test_build_order_text_empty_unit(self):
        """测试空单位名称"""
        with patch('app.application.ai_chat_app_service.get_ai_conversation_service'):
            from app.application.ai_chat_app_service import AIChatApplicationService

            service = AIChatApplicationService()

            products = [{"model": "5003", "quantity_tins": 10, "spec": 25}]

            result = service._build_order_text_from_products("", products)

            assert result == ""

    def test_execute_pro_mode_products_query(self):
        """测试专业模式产品查询"""
        mock_products_service = Mock()
        mock_products_service.get_products.return_value = {
            "success": True,
            "data": [{"name": "产品A"}]
        }

        with patch('app.application.ai_chat_app_service.get_ai_conversation_service'):
            with patch('app.bootstrap.get_products_service', return_value=mock_products_service):
                with patch('app.infrastructure.lookups.purchase_unit_resolver.resolve_purchase_unit', return_value=None):
                    from app.application.ai_chat_app_service import AIChatApplicationService

                    service = AIChatApplicationService()

                    slots = {"model_number": "5003", "unit_name": "测试公司"}
                    parsed_params = {}
                    ai_result = {"text": "查询结果"}
                    response_data = {"success": True, "data": {}}

                    result = service._execute_pro_mode_tools(
                        response_data, "products", slots, parsed_params, ai_result
                    )

                    assert result["success"] is True
                    assert "toolCall" in result or "data" in result

    def test_handle_confirmation_flow_no_context(self):
        """测试无文件上下文时不处理确认"""
        with patch('app.application.ai_chat_app_service.get_ai_conversation_service'):
            from app.application.ai_chat_app_service import AIChatApplicationService

            service = AIChatApplicationService()
            service.ai_service = Mock()

            service._handle_confirmation_flow("test_user", "是", None)

            service.ai_service.set_pending_confirmation.assert_not_called()

    def test_build_response_with_tool_call_no_tool_key(self):
        """测试工具调用但无 tool_key"""
        with patch('app.application.ai_chat_app_service.get_ai_conversation_service'):
            from app.application.ai_chat_app_service import AIChatApplicationService

            service = AIChatApplicationService()

            ai_result = {
                "text": "正在处理",
                "action": "tool_call",
                "data": {"params": {}, "slots": {}}
            }

            result = service._build_response(ai_result, None, "")

            assert result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
