"""
微信联系人兼容路由测试

测试 /api/wechat_contacts 路径的兼容接口
"""

import pytest
import json
from unittest.mock import Mock, patch


class TestWechatContactsCompat:
    """微信联系人兼容路由测试"""

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_get_contacts_compat_default(self, mock_get_service, client):
        """测试获取联系人列表（兼容路径）- 默认参数"""
        mock_service = Mock()
        mock_service.get_contacts.return_value = [
            {"id": 1, "contact_name": "张三", "wechat_id": "wx123", "is_starred": True},
            {"id": 2, "contact_name": "李四", "wechat_id": "wx456", "is_starred": False}
        ]
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat_contacts')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 2
        assert data['total'] == 2

        mock_service.get_contacts.assert_called_once_with(
            contact_type="all",
            limit=100
        )

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_get_contacts_compat_with_type(self, mock_get_service, client):
        """测试获取联系人列表（兼容路径）- 带类型筛选"""
        mock_service = Mock()
        mock_service.get_contacts.return_value = [
            {"id": 1, "contact_name": "张三", "wechat_id": "wx123"}
        ]
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat_contacts?type=contact&limit=50')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        mock_service.get_contacts.assert_called_once_with(
            contact_type="contact",
            limit=50
        )

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_get_contacts_compat_service_error(self, mock_get_service, client):
        """测试获取联系人列表（兼容路径）- 服务层错误"""
        mock_service = Mock()
        mock_service.get_contacts.side_effect = Exception("数据库错误")
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat_contacts')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert "查询失败" in data['message']

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_ensure_contact_cache(self, mock_get_service, client):
        """测试确保联系人缓存"""
        response = client.post('/api/wechat_contacts/ensure_contact_cache')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert "联系人缓存已就绪" in data['message']

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_search_contacts(self, mock_get_service, client):
        """测试搜索联系人（兼容路径）"""
        mock_service = Mock()
        mock_service.get_contacts.return_value = [
            {"id": 1, "contact_name": "张三", "wechat_id": "wx123"},
            {"id": 2, "contact_name": "张四", "wechat_id": "wx456"}
        ]
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat_contacts/search?q=张&limit=20')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['results']) == 2
        assert data['results'][0]['display_name'] == "张三"
        assert data['results'][0]['username'] == "wx123"
        assert data['results'][0]['already_starred'] in [True, False]

        mock_service.get_contacts.assert_called_once_with(
            keyword="张",
            contact_type=None,
            limit=20
        )

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_search_contacts_empty(self, mock_get_service, client):
        """测试搜索联系人（兼容路径）- 无结果"""
        mock_service = Mock()
        mock_service.get_contacts.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat_contacts/search?q=不存在的联系人')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['results']) == 0

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_search_contacts_service_error(self, mock_get_service, client):
        """测试搜索联系人（兼容路径）- 服务层错误"""
        mock_service = Mock()
        mock_service.get_contacts.side_effect = Exception("搜索失败")
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat_contacts/search?q=测试')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert "搜索失败" in data['message']

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_unstar_all_success(self, mock_get_service, client):
        """测试取消所有星标（兼容路径）- 成功"""
        mock_service = Mock()
        mock_service.unstar_all.return_value = {
            "success": True,
            "message": "已取消全部星标，共 5 个联系人",
            "count": 5
        }
        mock_get_service.return_value = mock_service

        response = client.post('/api/wechat_contacts/unstar_all')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 5

        mock_service.unstar_all.assert_called_once()

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_unstar_all_service_error(self, mock_get_service, client):
        """测试取消所有星标（兼容路径）- 服务层错误"""
        mock_service = Mock()
        mock_service.unstar_all.side_effect = Exception("操作失败")
        mock_get_service.return_value = mock_service

        response = client.post('/api/wechat_contacts/unstar_all')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert "操作失败" in data['message']

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_get_contact_by_id_compat_success(self, mock_get_service, client):
        """测试获取单个联系人（兼容路径）- 成功"""
        mock_service = Mock()
        mock_service.get_contact_by_id.return_value = {
            "id": 1,
            "contact_name": "张三",
            "wechat_id": "wx123",
            "is_starred": True
        }
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat_contacts/1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['contact_name'] == "张三"

        mock_service.get_contact_by_id.assert_called_once_with(1)

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_get_contact_by_id_compat_not_found(self, mock_get_service, client):
        """测试获取单个联系人（兼容路径）- 不存在"""
        mock_service = Mock()
        mock_service.get_contact_by_id.return_value = None
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat_contacts/999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert "联系人不存在" in data['message']

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_update_contact_compat_success(self, mock_get_service, client):
        """测试更新联系人（兼容路径）- 成功"""
        mock_service = Mock()
        mock_service.update_contact.return_value = {
            "success": True,
            "message": "联系人更新成功"
        }
        mock_get_service.return_value = mock_service

        response = client.put(
            '/api/wechat_contacts/1',
            json={
                "contact_name": "张三更新",
                "remark": "新备注",
                "is_starred": False
            }
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        mock_service.update_contact.assert_called_once_with(
            contact_id=1,
            contact_name="张三更新",
            remark="新备注",
            wechat_id=None,
            contact_type=None,
            is_starred=False
        )

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_update_contact_compat_failure(self, mock_get_service, client):
        """测试更新联系人（兼容路径）- 失败"""
        mock_service = Mock()
        mock_service.update_contact.return_value = {
            "success": False,
            "message": "联系人不存在"
        }
        mock_get_service.return_value = mock_service

        response = client.put(
            '/api/wechat_contacts/999',
            json={"contact_name": "测试"}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_update_contact_compat_service_error(self, mock_get_service, client):
        """测试更新联系人（兼容路径）- 服务层错误"""
        mock_service = Mock()
        mock_service.update_contact.side_effect = Exception("更新失败")
        mock_get_service.return_value = mock_service

        response = client.put(
            '/api/wechat_contacts/1',
            json={"contact_name": "测试"}
        )
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "更新失败" in data['message']

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_delete_contact_compat_success(self, mock_get_service, client):
        """测试删除联系人（兼容路径）- 成功"""
        mock_service = Mock()
        mock_service.delete_contact.return_value = {
            "success": True,
            "message": "联系人删除成功"
        }
        mock_get_service.return_value = mock_service

        response = client.delete('/api/wechat_contacts/1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        mock_service.delete_contact.assert_called_once_with(1)

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_delete_contact_compat_failure(self, mock_get_service, client):
        """测试删除联系人（兼容路径）- 失败"""
        mock_service = Mock()
        mock_service.delete_contact.return_value = {
            "success": False,
            "message": "联系人不存在"
        }
        mock_get_service.return_value = mock_service

        response = client.delete('/api/wechat_contacts/999')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_delete_contact_compat_service_error(self, mock_get_service, client):
        """测试删除联系人（兼容路径）- 服务层错误"""
        mock_service = Mock()
        mock_service.delete_contact.side_effect = Exception("删除失败")
        mock_get_service.return_value = mock_service

        response = client.delete('/api/wechat_contacts/1')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "删除失败" in data['message']

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_get_contact_context_compat_success(self, mock_get_service, client):
        """测试获取联系人聊天上下文（兼容路径）- 成功"""
        mock_service = Mock()
        mock_service.get_contact_context.return_value = [
            {"id": 1, "content": "你好", "is_from_me": False},
            {"id": 2, "content": "你好呀", "is_from_me": True}
        ]
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat_contacts/1/context')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['messages']) == 2
        assert data['count'] == 2

        mock_service.get_contact_context.assert_called_once_with(1)

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_get_contact_context_compat_empty(self, mock_get_service, client):
        """测试获取联系人聊天上下文（兼容路径）- 空记录"""
        mock_service = Mock()
        mock_service.get_contact_context.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat_contacts/1/context')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 0

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_get_contact_context_compat_service_error(self, mock_get_service, client):
        """测试获取联系人聊天上下文（兼容路径）- 服务层错误"""
        mock_service = Mock()
        mock_service.get_contact_context.side_effect = Exception("查询失败")
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat_contacts/1/context')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "查询失败" in data['message']

    def test_refresh_contact_messages_compat_success(self, client):
        """测试刷新联系人聊天记录（兼容路径）- 成功（占位实现）"""
        response = client.post('/api/wechat_contacts/1/refresh_messages')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert "刷新功能待实现" in data['message']

    def test_refresh_contact_messages_compat_service_error(self, client):
        """测试刷新联系人聊天记录（兼容路径）- 服务层错误（占位实现）"""
        response = client.post('/api/wechat_contacts/1/refresh_messages')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True


class TestWechatContactsCompatEdgeCases:
    """微信联系人兼容路由边界条件测试"""

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_get_contacts_with_invalid_limit(self, mock_get_service, client):
        """测试获取联系人列表（兼容路径）- 无效的limit参数"""
        mock_service = Mock()
        mock_service.get_contacts.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat_contacts?limit=abc')
        assert response.status_code == 200

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_search_contacts_with_empty_query(self, mock_get_service, client):
        """测试搜索联系人（兼容路径）- 空关键词"""
        mock_service = Mock()
        mock_service.get_contacts.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat_contacts/search?q=')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['results']) == 0

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_get_contact_by_id_with_invalid_id(self, mock_get_service, client):
        """测试获取单个联系人（兼容路径）- 无效ID"""
        mock_service = Mock()
        mock_service.get_contact_by_id.return_value = None
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat_contacts/abc')
        assert response.status_code == 404

    @patch('app.routes.wechat_contacts.get_wechat_contact_service')
    def test_update_contact_with_no_json(self, mock_get_service, client):
        """测试更新联系人（兼容路径）- 无JSON数据"""
        mock_service = Mock()
        mock_service.update_contact.return_value = {
            "success": True,
            "message": "联系人更新成功"
        }
        mock_get_service.return_value = mock_service

        response = client.put('/api/wechat_contacts/1', json={})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        mock_service.update_contact.assert_called_once_with(
            contact_id=1,
            contact_name=None,
            remark=None,
            wechat_id=None,
            contact_type=None,
            is_starred=None
        )
