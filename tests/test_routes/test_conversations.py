"""
会话路由测试
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestConversations:
    """会话路由测试"""

    def test_get_sessions_success(self, client):
        """测试获取会话列表成功"""
        with patch('app.services.conversation_service.ConversationService.get_sessions') as mock_get:
            mock_get.return_value = [
                ('1', 'session_001', 'user1', '测试会话', '', 5, '2026-03-17', '2026-03-17')
            ]
            response = client.get('/api/conversations/sessions?user_id=user1')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'sessions' in data

    def test_get_sessions_with_limit(self, client):
        """测试获取会话列表并指定limit"""
        with patch('app.services.conversation_service.ConversationService.get_sessions') as mock_get:
            mock_get.return_value = []
            response = client.get('/api/conversations/sessions?user_id=user1&limit=10')
            assert response.status_code == 200
            data = response.get_json()
            assert 'sessions' in data

    def test_get_sessions_default_user(self, client):
        """测试获取默认用户的会话列表"""
        with patch('app.services.conversation_service.ConversationService.get_sessions') as mock_get:
            mock_get.return_value = []
            response = client.get('/api/conversations/sessions')
            assert response.status_code == 200

    def test_get_sessions_error(self, client):
        """测试获取会话列表失败"""
        with patch('app.services.conversation_service.ConversationService.get_sessions') as mock_get:
            mock_get.side_effect = Exception("数据库错误")
            response = client.get('/api/conversations/sessions')
            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False

    def test_get_conversation_messages_success(self, client):
        """测试获取会话消息成功"""
        with patch('app.services.conversation_service.ConversationService.get_session_messages') as mock_get:
            mock_get.return_value = [
                (1, 'session_001', 'user1', 'user', '你好', '', '', '2026-03-17')
            ]
            response = client.get('/api/conversations/session_001')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'messages' in data

    def test_get_conversation_messages_with_limit(self, client):
        """测试获取会话消息并指定limit"""
        with patch('app.services.conversation_service.ConversationService.get_session_messages') as mock_get:
            mock_get.return_value = []
            response = client.get('/api/conversations/session_001?limit=20')
            assert response.status_code == 200
            data = response.get_json()
            assert 'messages' in data

    def test_get_conversation_messages_not_found(self, client):
        """测试获取不存在的会话消息"""
        with patch('app.services.conversation_service.ConversationService.get_session_messages') as mock_get:
            mock_get.return_value = []
            response = client.get('/api/conversations/nonexistent')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True

    def test_get_conversation_messages_error(self, client):
        """测试获取会话消息失败"""
        with patch('app.services.conversation_service.ConversationService.get_session_messages') as mock_get:
            mock_get.side_effect = Exception("查询失败")
            response = client.get('/api/conversations/session_001')
            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False

    def test_save_message_success(self, client):
        """测试保存对话消息成功"""
        with patch('app.services.conversation_service.ConversationService.save_message') as mock_save:
            mock_save.return_value = 123
            response = client.post(
                '/api/conversations/message',
                json={
                    "session_id": "session_001",
                    "user_id": "user1",
                    "role": "user",
                    "content": "你好"
                },
                content_type='application/json'
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True

    def test_save_message_with_intent_and_metadata(self, client):
        """测试保存带意图和元数据的消息"""
        with patch('app.services.conversation_service.ConversationService.save_message') as mock_save:
            mock_save.return_value = 456
            response = client.post(
                '/api/conversations/message',
                json={
                    "session_id": "session_001",
                    "user_id": "user1",
                    "role": "assistant",
                    "content": "好的，我来帮你",
                    "intent": "shipment_create",
                    "metadata": '{"order_id": "123"}'
                },
                content_type='application/json'
            )
            assert response.status_code == 200

    def test_save_message_missing_session_id(self, client):
        """测试保存消息缺少session_id"""
        response = client.post(
            '/api/conversations/message',
            json={
                "user_id": "user1",
                "role": "user",
                "content": "你好"
            },
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_save_message_missing_role(self, client):
        """测试保存消息缺少role"""
        response = client.post(
            '/api/conversations/message',
            json={
                "session_id": "session_001",
                "content": "你好"
            },
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_save_message_missing_content(self, client):
        """测试保存消息缺少content"""
        response = client.post(
            '/api/conversations/message',
            json={
                "session_id": "session_001",
                "role": "user"
            },
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_save_message_error(self, client):
        """测试保存消息失败"""
        with patch('app.services.conversation_service.ConversationService.save_message') as mock_save:
            mock_save.side_effect = Exception("保存失败")
            response = client.post(
                '/api/conversations/message',
                json={
                    "session_id": "session_001",
                    "role": "user",
                    "content": "你好"
                },
                content_type='application/json'
            )
            assert response.status_code == 500

    def test_delete_conversation_success(self, client):
        """测试删除会话成功"""
        with patch('app.services.conversation_service.ConversationService.delete_session') as mock_delete:
            mock_delete.return_value = True
            response = client.delete('/api/conversations/session_001')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True

    def test_delete_conversation_not_found(self, client):
        """测试删除不存在的会话"""
        with patch('app.services.conversation_service.ConversationService.delete_session') as mock_delete:
            mock_delete.return_value = False
            response = client.delete('/api/conversations/nonexistent')
            assert response.status_code == 200

    def test_delete_conversation_error(self, client):
        """测试删除会话失败"""
        with patch('app.services.conversation_service.ConversationService.delete_session') as mock_delete:
            mock_delete.side_effect = Exception("删除失败")
            response = client.delete('/api/conversations/session_001')
            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False

    def test_update_conversation_title_success(self, client):
        """测试更新会话标题成功"""
        with patch('app.services.conversation_service.ConversationService.update_session_title') as mock_update:
            mock_update.return_value = True
            response = client.put(
                '/api/conversations/session_001/title',
                json={"title": "新标题"},
                content_type='application/json'
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True

    def test_update_conversation_title_empty(self, client):
        """测试更新会话标题为空"""
        with patch('app.services.conversation_service.ConversationService.update_session_title') as mock_update:
            mock_update.return_value = True
            response = client.put(
                '/api/conversations/session_001/title',
                json={"title": ""},
                content_type='application/json'
            )
            assert response.status_code == 200

    def test_update_conversation_title_error(self, client):
        """测试更新会话标题失败"""
        with patch('app.services.conversation_service.ConversationService.update_session_title') as mock_update:
            mock_update.side_effect = Exception("更新失败")
            response = client.put(
                '/api/conversations/session_001/title',
                json={"title": "新标题"},
                content_type='application/json'
            )
            assert response.status_code == 500
