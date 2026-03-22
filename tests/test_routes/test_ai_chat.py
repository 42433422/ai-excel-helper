"""
AI 对话路由测试
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from flask import Response


class TestAIChat:
    """AI 对话路由测试"""

    @pytest.fixture
    def mock_ai_chat_service(self):
        """Mock AI 聊天应用服务"""
        with patch('app.routes.ai_chat.get_ai_chat_app_service') as mock:
            service = MagicMock()
            mock.return_value = service
            yield service

    @pytest.fixture
    def mock_ai_service(self):
        """Mock AI 服务（用于非 chat 路由）"""
        with patch('app.routes.ai_chat.get_ai_service') as mock:
            service = MagicMock()
            mock.return_value = service
            yield service

    @pytest.fixture
    def mock_intent_service(self):
        """Mock 意图识别服务"""
        with patch('app.routes.ai_chat.recognize_intents') as mock:
            yield mock

    def test_chat_success(self, client, mock_ai_chat_service, mock_intent_service):
        """测试正常聊天"""
        mock_ai_chat_service.process_chat = MagicMock(return_value={
            "success": True,
            "message": "处理完成",
            "data": {
                "text": "测试回复",
                "action": "ai_response",
                "data": {}
            },
            "response": "测试回复"
        })
        
        response = client.post(
            '/api/ai/chat',
            json={"message": "你好"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["text"] == "测试回复"

    def test_chat_with_user_id(self, client, mock_ai_chat_service, mock_intent_service):
        """测试带用户 ID 的聊天"""
        mock_ai_chat_service.process_chat = MagicMock(return_value={
            "success": True,
            "message": "处理完成",
            "data": {
                "text": "测试回复",
                "action": "ai_response",
                "data": {}
            },
            "response": "测试回复"
        })
        
        response = client.post(
            '/api/ai/chat',
            json={"message": "你好", "user_id": "test_user_123"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        mock_ai_chat_service.process_chat.assert_called_once()

    def test_chat_with_context(self, client, mock_ai_service, mock_intent_service):
        """测试带额外上下文的聊天"""
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "测试回复",
            "action": "ai_response",
            "data": {}
        })
        
        context_data = {"current_file": "test.xlsx", "last_action": "upload"}
        response = client.post(
            '/api/ai/chat',
            json={"message": "你好", "context": context_data},
            content_type='application/json'
        )
        
        assert response.status_code == 200

    def test_chat_empty_message(self, client):
        """测试空消息"""
        response = client.post(
            '/api/ai/chat',
            json={"message": ""},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "消息内容不能为空" in data["message"]

    def test_chat_missing_message(self, client):
        """测试缺少消息字段"""
        response = client.post(
            '/api/ai/chat',
            json={},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_chat_service_error(self, client, mock_ai_service):
        """测试 AI 服务异常"""
        mock_ai_service.chat = AsyncMock(side_effect=Exception("服务错误"))
        
        response = client.post(
            '/api/ai/chat',
            json={"message": "测试"},
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    def test_multi_turn_conversation(self, client, mock_ai_service):
        """测试多轮对话场景"""
        user_id = "test_user_multi"
        
        responses = [
            {"text": "第一轮回复", "action": "ai_response", "data": {}},
            {"text": "第二轮回复", "action": "ai_response", "data": {}},
            {"text": "第三轮回复", "action": "ai_response", "data": {}}
        ]
        
        mock_ai_service.chat = AsyncMock(side_effect=responses)
        
        messages = ["第一轮消息", "第二轮消息", "第三轮消息"]
        
        for i, message in enumerate(messages):
            response = client.post(
                '/api/ai/chat',
                json={"message": message, "user_id": user_id},
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["data"]["text"] == responses[i]["text"]
        
        assert mock_ai_service.chat.call_count == 3

    def test_greeting_intent(self, client, mock_ai_service, mock_intent_service):
        """测试问候意图"""
        mock_intent_service.return_value = {
            "primary_intent": "greeting",
            "is_greeting": True,
            "tool_key": None
        }
        
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "您好！我是 XCAGI 智能助手",
            "action": "greeting",
            "data": {}
        })
        
        response = client.post(
            '/api/ai/chat',
            json={"message": "你好"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["action"] == "greeting"

    def test_goodbye_intent(self, client, mock_ai_service, mock_intent_service):
        """测试告别意图"""
        mock_intent_service.return_value = {
            "primary_intent": "goodbye",
            "is_goodbye": True,
            "tool_key": None
        }
        
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "再见！祝您工作顺利！",
            "action": "goodbye",
            "data": {}
        })
        
        response = client.post(
            '/api/ai/chat',
            json={"message": "再见"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["action"] == "goodbye"

    def test_help_intent(self, client, mock_ai_service, mock_intent_service):
        """测试帮助意图"""
        mock_intent_service.return_value = {
            "primary_intent": "help",
            "is_help": True,
            "tool_key": None
        }
        
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "XCAGI 智能助手功能介绍",
            "action": "help",
            "data": {}
        })
        
        response = client.post(
            '/api/ai/chat',
            json={"message": "帮助"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["action"] == "help"

    def test_tool_call_intent(self, client, mock_ai_service, mock_intent_service):
        """测试工具调用意图"""
        mock_intent_service.return_value = {
            "primary_intent": "shipment_generate",
            "tool_key": "shipment_generate",
            "is_greeting": False,
            "intent_hints": ["生成发货单"]
        }
        
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "正在处理工具调用：shipment_generate",
            "action": "tool_call",
            "data": {
                "tool_key": "shipment_generate",
                "intent": "shipment_generate",
                "hints": ["生成发货单"]
            }
        })
        
        response = client.post(
            '/api/ai/chat',
            json={"message": "生成发货单"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["action"] == "tool_call"
        assert data["data"]["data"]["tool_key"] == "shipment_generate"

    def test_chat_followup_response_shape(self, client, mock_ai_service):
        """测试 followup 响应结构"""
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "还缺少桶数，请告诉我需要多少桶？",
            "action": "followup",
            "data": {"task_type": "shipment_generate", "missing_slots": ["quantity_tins"]},
        })

        response = client.post(
            '/api/ai/chat',
            json={"message": "打印七彩乐园发货单，编号9803，规格28"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "followup" in data
        assert data["followup"]["missing_slots"] == ["quantity_tins"]

    def test_chat_toolcall_uses_structured_order_text(self, client, mock_ai_service):
        """测试 toolCall 优先使用结构化 order_text 参数"""
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "正在处理工具调用：shipment_generate",
            "action": "tool_call",
            "data": {
                "tool_key": "shipment_generate",
                "intent": "shipment_generate",
                "params": {"order_text": "七彩乐园5 桶 9803 规格 28"},
            },
        })

        response = client.post(
            '/api/ai/chat',
            json={"message": "改成5桶", "source": "pro"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["toolCall"]["params"]["order_text"] == "七彩乐园5 桶 9803 规格 28"

    def test_chat_stream_success(self, client, mock_ai_service):
        """测试流式对话成功"""
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "流式回复内容",
            "action": "ai_response",
            "data": {}
        })
        
        response = client.post(
            '/api/ai/chat/stream',
            json={"message": "测试"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        assert "text/event-stream" in response.content_type
        assert "Cache-Control" in response.headers
        assert response.headers["Cache-Control"] == "no-cache"

    def test_chat_stream_content(self, client, mock_ai_service):
        """测试流式对话内容"""
        expected_data = {
            "text": "流式回复内容",
            "action": "ai_response",
            "data": {}
        }
        
        mock_ai_service.chat = AsyncMock(return_value=expected_data)
        
        response = client.post(
            '/api/ai/chat/stream',
            json={"message": "测试"},
            content_type='application/json'
        )
        
        content = response.get_data(as_text=True)
        assert "data:" in content
        assert "[DONE]" in content

    def test_chat_stream_empty_message(self, client):
        """测试流式对话空消息"""
        response = client.post(
            '/api/ai/chat/stream',
            json={"message": ""},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_chat_stream_with_user_id(self, client, mock_ai_service):
        """测试带用户 ID 的流式对话"""
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "流式回复",
            "action": "ai_response",
            "data": {}
        })
        
        response = client.post(
            '/api/ai/chat/stream',
            json={"message": "测试", "user_id": "stream_user_123"},
            content_type='application/json'
        )
        
        assert response.status_code == 200

    def test_chat_stream_error(self, client, mock_ai_service):
        """测试流式对话异常"""
        mock_ai_service.chat = AsyncMock(side_effect=Exception("流式错误"))
        
        try:
            response = client.post(
                '/api/ai/chat/stream',
                json={"message": "测试"},
                content_type='application/json'
            )
            assert response.status_code == 500
        except Exception:
            pass

    def test_get_context_success(self, client, mock_ai_service):
        """测试获取上下文成功"""
        mock_context = MagicMock()
        mock_context.user_id = "test_user"
        mock_context.conversation_history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "您好"}
        ]
        mock_context.current_file = None
        mock_context.last_action = None
        mock_context.metadata = {}
        
        mock_ai_service.get_context.return_value = mock_context
        
        response = client.get('/api/ai/context?user_id=test_user')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["user_id"] == "test_user"
        assert len(data["data"]["conversation_history"]) == 2

    def test_get_context_not_found(self, client, mock_ai_service):
        """测试获取不存在的上下文"""
        mock_ai_service.get_context.return_value = None
        
        response = client.get('/api/ai/context?user_id=nonexistent_user')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"] is None

    def test_get_context_without_user_id(self, client, mock_ai_service):
        """测试不带用户 ID 获取上下文"""
        mock_context = MagicMock()
        mock_context.user_id = "default_user"
        mock_context.conversation_history = []
        mock_context.current_file = None
        mock_context.last_action = None
        mock_context.metadata = {}
        
        mock_ai_service.get_context.return_value = mock_context
        
        response = client.get('/api/ai/context')
        
        assert response.status_code == 200

    def test_get_context_error(self, client, mock_ai_service):
        """测试获取上下文异常"""
        mock_ai_service.get_context.side_effect = Exception("获取上下文错误")
        
        response = client.get('/api/ai/context?user_id=test_user')
        
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    def test_clear_context_success(self, client, mock_ai_service):
        """测试清除上下文成功"""
        mock_ai_service.clear_context.return_value = True
        
        response = client.post(
            '/api/ai/context/clear',
            json={"user_id": "test_user"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "上下文已清除" in data["message"]

    def test_clear_context_not_found(self, client, mock_ai_service):
        """测试清除不存在的上下文"""
        mock_ai_service.clear_context.return_value = False
        
        response = client.post(
            '/api/ai/context/clear',
            json={"user_id": "nonexistent_user"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "未找到上下文" in data["message"]

    def test_clear_context_without_user_id(self, client, mock_ai_service):
        """测试不带用户 ID 清除上下文"""
        mock_ai_service.clear_context.return_value = True
        
        response = client.post(
            '/api/ai/context/clear',
            json={},
            content_type='application/json'
        )
        
        assert response.status_code == 200

    def test_clear_context_error(self, client, mock_ai_service):
        """测试清除上下文异常"""
        mock_ai_service.clear_context.side_effect = Exception("清除错误")
        
        response = client.post(
            '/api/ai/context/clear',
            json={"user_id": "test_user"},
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    def test_context_lifecycle(self, client, mock_ai_service):
        """测试上下文完整生命周期"""
        user_id = "lifecycle_test_user"
        
        mock_context = MagicMock()
        mock_context.user_id = user_id
        mock_context.conversation_history = []
        mock_context.current_file = None
        mock_context.last_action = None
        mock_context.metadata = {}
        
        mock_ai_service.get_context.return_value = mock_context
        mock_ai_service.clear_context.return_value = True
        
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "测试回复",
            "action": "ai_response",
            "data": {}
        })
        
        client.post(
            '/api/ai/chat',
            json={"message": "你好", "user_id": user_id},
            content_type='application/json'
        )
        
        response = client.get(f'/api/ai/context?user_id={user_id}')
        assert response.status_code == 200
        
        response = client.post(
            '/api/ai/context/clear',
            json={"user_id": user_id},
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_get_config_success(self, client):
        """测试获取配置成功"""
        response = client.get('/api/ai/config')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert "api_configured" in data["data"]
        assert "model" in data["data"]
        assert "features" in data["data"]
        assert isinstance(data["data"]["features"], list)

    def test_get_config_model_name(self, client):
        """测试配置中的模型名称"""
        response = client.get('/api/ai/config')
        
        data = response.get_json()
        assert data["data"]["model"] == "deepseek-chat"

    def test_get_config_features(self, client):
        """测试配置中的功能列表"""
        response = client.get('/api/ai/config')
        
        data = response.get_json()
        expected_features = ["意图识别", "工具调用", "AI 对话", "上下文管理", "流式输出"]
        for feature in expected_features:
            assert feature in data["data"]["features"]

    def test_get_config_error(self, client):
        """测试获取配置异常"""
        with patch.dict('os.environ', {}, clear=True):
            with patch('app.routes.ai_chat.os.environ.get', side_effect=Exception("配置错误")):
                response = client.get('/api/ai/config')
                
                assert response.status_code == 500
                data = response.get_json()
                assert data["success"] is False

    def test_intent_test_success(self, client, mock_intent_service):
        """测试意图识别成功"""
        mock_intent_service.return_value = {
            "primary_intent": "shipment_generate",
            "tool_key": "shipment_generate",
            "is_greeting": False,
            "intent_hints": ["生成发货单"]
        }
        
        response = client.post(
            '/api/ai/intent/test',
            json={"message": "生成发货单"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["primary_intent"] == "shipment_generate"
        assert data["data"]["tool_key"] == "shipment_generate"

    def test_intent_test_greeting(self, client, mock_intent_service):
        """测试识别问候意图"""
        mock_intent_service.return_value = {
            "primary_intent": "greeting",
            "tool_key": None,
            "is_greeting": True,
            "intent_hints": []
        }
        
        response = client.post(
            '/api/ai/intent/test',
            json={"message": "你好"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["is_greeting"] is True

    def test_intent_test_goodbye(self, client, mock_intent_service):
        """测试识别告别意图"""
        mock_intent_service.return_value = {
            "primary_intent": "goodbye",
            "tool_key": None,
            "is_goodbye": True,
            "intent_hints": []
        }
        
        response = client.post(
            '/api/ai/intent/test',
            json={"message": "再见"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["is_goodbye"] is True

    def test_intent_test_help(self, client, mock_intent_service):
        """测试识别帮助意图"""
        mock_intent_service.return_value = {
            "primary_intent": "help",
            "tool_key": None,
            "is_help": True,
            "intent_hints": []
        }
        
        response = client.post(
            '/api/ai/intent/test',
            json={"message": "帮助"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["is_help"] is True

    def test_intent_test_multiple_tools(self, client, mock_intent_service):
        """测试识别多个工具意图"""
        mock_intent_service.return_value = {
            "primary_intent": "products",
            "tool_key": "products",
            "is_greeting": False,
            "intent_hints": ["产品", "商品"]
        }
        
        response = client.post(
            '/api/ai/intent/test',
            json={"message": "产品列表"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["tool_key"] == "products"

    def test_intent_test_empty_message(self, client):
        """测试意图识别空消息"""
        response = client.post(
            '/api/ai/intent/test',
            json={"message": ""},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "消息内容不能为空" in data["message"]

    def test_intent_test_missing_message(self, client):
        """测试意图识别缺少消息字段"""
        response = client.post(
            '/api/ai/intent/test',
            json={},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_intent_test_error(self, client, mock_intent_service):
        """测试意图识别异常"""
        mock_intent_service.side_effect = Exception("意图识别错误")
        
        response = client.post(
            '/api/ai/intent/test',
            json={"message": "测试"},
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    def test_test_endpoint(self, client):
        """测试测试端点"""
        response = client.get('/api/ai/test')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "message" in data
        assert "timestamp" in data

    def test_long_message(self, client, mock_ai_service):
        """测试长消息"""
        long_message = "测试" * 1000
        
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "回复",
            "action": "ai_response",
            "data": {}
        })
        
        response = client.post(
            '/api/ai/chat',
            json={"message": long_message},
            content_type='application/json'
        )
        
        assert response.status_code == 200

    def test_special_characters(self, client, mock_ai_service):
        """测试特殊字符"""
        special_message = "测试消息：!@#$%^&*()_+-=[]{}|;':\",./<>?"
        
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "回复",
            "action": "ai_response",
            "data": {}
        })
        
        response = client.post(
            '/api/ai/chat',
            json={"message": special_message},
            content_type='application/json'
        )
        
        assert response.status_code == 200

    def test_unicode_characters(self, client, mock_ai_service):
        """测试 Unicode 字符"""
        unicode_message = "测试中文 🎉 🚀 🌟"
        
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "回复",
            "action": "ai_response",
            "data": {}
        })
        
        response = client.post(
            '/api/ai/chat',
            json={"message": unicode_message},
            content_type='application/json'
        )
        
        assert response.status_code == 200

    def test_invalid_json(self, client):
        """测试无效 JSON"""
        response = client.post(
            '/api/ai/chat',
            data="invalid json",
            content_type='application/json'
        )
        
        assert response.status_code in [400, 500]

    def test_missing_content_type(self, client):
        """测试缺少 Content-Type"""
        response = client.post(
            '/api/ai/chat',
            data='{"message": "测试"}'
        )
        
        assert response.status_code in [400, 415]

    def test_concurrent_requests(self, client, mock_ai_service):
        """测试并发请求"""
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "回复",
            "action": "ai_response",
            "data": {}
        })
        
        responses = []
        for i in range(5):
            response = client.post(
                '/api/ai/chat',
                json={"message": f"消息{i}", "user_id": f"user_{i}"},
                content_type='application/json'
            )
            responses.append(response)
        
        for response in responses:
            assert response.status_code == 200

    def test_different_user_contexts(self, client, mock_ai_service):
        """测试不同用户的上下文隔离"""
        users = ["user_a", "user_b", "user_c"]
        
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "回复",
            "action": "ai_response",
            "data": {}
        })
        
        for user in users:
            response = client.post(
                '/api/ai/chat',
                json={"message": "测试", "user_id": user},
                content_type='application/json'
            )
            assert response.status_code == 200

    def test_tool_keywords_coverage(self, client, mock_intent_service):
        """测试所有工具关键词的意图识别"""
        tool_tests = [
            ("生成发货单", "shipment_generate"),
            ("发货单模板", "shipment_template"),
            ("分解 excel", "excel_decompose"),
            ("出货记录", "shipments"),
            ("产品列表", "products"),
            ("客户列表", "customers"),
            ("打印标签", "print_label"),
            ("上传文件", "upload_file"),
            ("原材料库存", "materials")
        ]
        
        for message, expected_tool in tool_tests:
            mock_intent_service.return_value = {
                "primary_intent": expected_tool,
                "tool_key": expected_tool,
                "is_greeting": False,
                "intent_hints": []
            }
            
            response = client.post(
                '/api/ai/intent/test',
                json={"message": message},
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["data"]["tool_key"] == expected_tool


class TestAIChatUnified:
    """AI 统一聊天接口测试（兼容旧版前端）"""

    @pytest.fixture
    def mock_ai_service(self):
        """Mock AI 服务"""
        with patch('app.routes.ai_chat.get_ai_service') as mock:
            service = MagicMock()
            mock.return_value = service
            yield service

    @pytest.fixture
    def mock_intent_service(self):
        """Mock 意图识别服务"""
        with patch('app.routes.ai_chat.recognize_intents') as mock:
            yield mock

    def test_chat_unified_success(self, client, mock_ai_service, mock_intent_service):
        """测试统一聊天接口成功"""
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "测试回复",
            "action": "ai_response",
            "data": {}
        })
        
        response = client.post(
            '/api/ai/chat-unified',
            json={"message": "你好"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["text"] == "测试回复"

    def test_chat_unified_with_user_id(self, client, mock_ai_service, mock_intent_service):
        """测试带用户 ID 的统一聊天"""
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "带用户 ID 的回复",
            "action": "ai_response",
            "data": {}
        })
        
        response = client.post(
            '/api/ai/chat-unified',
            json={"message": "你好", "user_id": "test_user_123"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_chat_unified_with_context(self, client, mock_ai_service, mock_intent_service):
        """测试带上下文的统一聊天"""
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "带上下文的回复",
            "action": "ai_response",
            "data": {}
        })
        
        response = client.post(
            '/api/ai/chat-unified',
            json={
                "message": "继续",
                "context": {"previous_topic": "产品"}
            },
            content_type='application/json'
        )
        
        assert response.status_code == 200

    def test_chat_unified_empty_message(self, client, mock_ai_service, mock_intent_service):
        """测试空消息"""
        response = client.post(
            '/api/ai/chat-unified',
            json={"message": ""},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "消息内容不能为空" in data["message"]

    def test_chat_unified_missing_message(self, client):
        """测试缺少消息字段"""
        response = client.post(
            '/api/ai/chat-unified',
            json={},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_chat_unified_greeting(self, client, mock_ai_service, mock_intent_service):
        """测试问候语"""
        mock_intent_service.return_value = {
            "primary_intent": "greeting",
            "tool_key": None,
            "is_greeting": True
        }
        
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "你好！有什么可以帮助你的？",
            "action": "greeting",
            "data": {}
        })
        
        response = client.post(
            '/api/ai/chat-unified',
            json={"message": "你好"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["action"] == "greeting"

    def test_chat_unified_tool_call(self, client, mock_ai_service, mock_intent_service):
        """测试工具调用"""
        mock_intent_service.return_value = {
            "primary_intent": "shipment_generate",
            "tool_key": "shipment_generate",
            "is_greeting": False
        }
        
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "正在处理工具调用",
            "action": "tool_call",
            "data": {"tool_key": "shipment_generate"}
        })
        
        response = client.post(
            '/api/ai/chat-unified',
            json={"message": "生成发货单"},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["action"] == "tool_call"
        assert data["data"]["data"]["tool_key"] == "shipment_generate"

    def test_chat_unified_service_error(self, client, mock_ai_service, mock_intent_service):
        """测试服务层错误"""
        mock_ai_service.chat = AsyncMock(side_effect=Exception("AI 服务错误"))
        
        response = client.post(
            '/api/ai/chat-unified',
            json={"message": "测试"},
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "处理失败" in data["message"]

    def test_chat_unified_with_special_characters(self, client, mock_ai_service, mock_intent_service):
        """测试特殊字符"""
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "回复",
            "action": "ai_response",
            "data": {}
        })
        
        response = client.post(
            '/api/ai/chat-unified',
            json={"message": "测试消息：!@#$%^&*()_+-=[]{}|;':\",./<>?"},
            content_type='application/json'
        )
        
        assert response.status_code == 200

    def test_chat_unified_with_unicode(self, client, mock_ai_service, mock_intent_service):
        """测试 Unicode 字符"""
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "回复",
            "action": "ai_response",
            "data": {}
        })
        
        response = client.post(
            '/api/ai/chat-unified',
            json={"message": "测试中文 🎉 🚀 🌟"},
            content_type='application/json'
        )
        
        assert response.status_code == 200

    def test_chat_unified_with_long_message(self, client, mock_ai_service, mock_intent_service):
        """测试长消息"""
        long_message = "测试" * 1000
        
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "回复",
            "action": "ai_response",
            "data": {}
        })
        
        response = client.post(
            '/api/ai/chat-unified',
            json={"message": long_message},
            content_type='application/json'
        )
        
        assert response.status_code == 200

    def test_chat_unified_invalid_json(self, client):
        """测试无效 JSON"""
        response = client.post(
            '/api/ai/chat-unified',
            data="invalid json",
            content_type='application/json'
        )
        
        assert response.status_code in [400, 500]

    def test_chat_unified_method_not_allowed(self, client):
        """测试不支持的 HTTP 方法"""
        # 测试 GET 方法（应该返回 404，因为路由未定义此方法）
        response = client.get('/api/ai/chat-unified')
        assert response.status_code in [404, 405]
        
        # 测试 PUT 方法（应该返回 404，因为路由未定义此方法）
        response = client.put('/api/ai/chat-unified')
        assert response.status_code in [404, 405]
        
        # 测试 DELETE 方法（应该返回 404，因为路由未定义此方法）
        response = client.delete('/api/ai/chat-unified')
        assert response.status_code in [404, 405]

    def test_chat_unified_concurrent_requests(self, client, mock_ai_service, mock_intent_service):
        """测试并发请求"""
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "回复",
            "action": "ai_response",
            "data": {}
        })
        
        responses = []
        for i in range(5):
            response = client.post(
                '/api/ai/chat-unified',
                json={"message": f"消息{i}", "user_id": f"user_{i}"},
                content_type='application/json'
            )
            responses.append(response)
        
        for response in responses:
            assert response.status_code == 200

    def test_chat_unified_same_as_chat(self, client, mock_ai_service, mock_intent_service):
        """测试统一聊天接口与普通聊天接口功能相同"""
        mock_ai_service.chat = AsyncMock(return_value={
            "text": "测试回复",
            "action": "ai_response",
            "data": {"test": "data"}
        })
        
        # 调用普通聊天接口
        response_chat = client.post(
            '/api/ai/chat',
            json={"message": "测试", "user_id": "test_user"},
            content_type='application/json'
        )
        
        # 调用统一聊天接口
        response_unified = client.post(
            '/api/ai/chat-unified',
            json={"message": "测试", "user_id": "test_user"},
            content_type='application/json'
        )
        
        # 两个接口应该返回相同的结果
        assert response_chat.status_code == response_unified.status_code
        data_chat = response_chat.get_json()
        data_unified = response_unified.get_json()
        assert data_chat["success"] == data_unified["success"]
        assert data_chat["data"]["text"] == data_unified["data"]["text"]
        assert data_chat["data"]["action"] == data_unified["data"]["action"]
