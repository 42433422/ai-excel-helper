"""
微信任务路由测试
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock


class TestWechatTasks:
    """微信任务路由测试"""

    @patch('app.routes.wechat.get_wechat_task_service')
    def test_get_tasks_default_params(self, mock_get_service, client):
        """测试获取任务列表 - 默认参数"""
        mock_service = Mock()
        mock_service.get_tasks.return_value = [
            {"id": 1, "content": "任务1", "status": "pending"},
            {"id": 2, "content": "任务2", "status": "pending"}
        ]
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/tasks')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 2
        assert data['total'] == 2

        mock_service.get_tasks.assert_called_once_with(
            contact_id=None,
            status="pending",
            limit=20
        )

    @patch('app.routes.wechat.get_wechat_task_service')
    def test_get_tasks_with_filters(self, mock_get_service, client):
        """测试获取任务列表 - 带筛选参数"""
        mock_service = Mock()
        mock_service.get_tasks.return_value = [
            {"id": 1, "content": "任务1", "status": "confirmed"}
        ]
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/tasks?status=confirmed&contact_id=123&limit=10')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        mock_service.get_tasks.assert_called_once_with(
            contact_id=123,
            status="confirmed",
            limit=10
        )

    @patch('app.routes.wechat.get_wechat_task_service')
    def test_get_tasks_service_error(self, mock_get_service, client):
        """测试获取任务列表 - 服务层错误"""
        mock_service = Mock()
        mock_service.get_tasks.side_effect = Exception("数据库连接失败")
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/tasks')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert "查询失败" in data['message']

    @patch('app.routes.wechat.get_wechat_task_service')
    def test_confirm_task_success(self, mock_get_service, client):
        """测试确认任务 - 成功"""
        mock_service = Mock()
        mock_service.confirm_task.return_value = {
            "success": True,
            "message": "任务已确认"
        }
        mock_get_service.return_value = mock_service

        response = client.post('/api/wechat/task/1/confirm')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        mock_service.confirm_task.assert_called_once_with(1)

    @patch('app.routes.wechat.get_wechat_task_service')
    def test_confirm_task_failure(self, mock_get_service, client):
        """测试确认任务 - 失败"""
        mock_service = Mock()
        mock_service.confirm_task.return_value = {
            "success": False,
            "message": "任务不存在"
        }
        mock_get_service.return_value = mock_service

        response = client.post('/api/wechat/task/999/confirm')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    @patch('app.routes.wechat.get_wechat_task_service')
    def test_confirm_task_service_error(self, mock_get_service, client):
        """测试确认任务 - 服务层错误"""
        mock_service = Mock()
        mock_service.confirm_task.side_effect = Exception("服务异常")
        mock_get_service.return_value = mock_service

        response = client.post('/api/wechat/task/1/confirm')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "确认失败" in data['message']

    @patch('app.routes.wechat.get_wechat_task_service')
    def test_ignore_task_success(self, mock_get_service, client):
        """测试忽略任务 - 成功"""
        mock_service = Mock()
        mock_service.ignore_task.return_value = {
            "success": True,
            "message": "任务已忽略"
        }
        mock_get_service.return_value = mock_service

        response = client.post('/api/wechat/task/1/ignore')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        mock_service.ignore_task.assert_called_once_with(1)

    @patch('app.routes.wechat.get_wechat_task_service')
    def test_ignore_task_failure(self, mock_get_service, client):
        """测试忽略任务 - 失败"""
        mock_service = Mock()
        mock_service.ignore_task.return_value = {
            "success": False,
            "message": "任务不存在"
        }
        mock_get_service.return_value = mock_service

        response = client.post('/api/wechat/task/999/ignore')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    @patch('app.routes.wechat.get_wechat_task_service')
    def test_ignore_task_service_error(self, mock_get_service, client):
        """测试忽略任务 - 服务层错误"""
        mock_service = Mock()
        mock_service.ignore_task.side_effect = Exception("服务异常")
        mock_get_service.return_value = mock_service

        response = client.post('/api/wechat/task/1/ignore')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "忽略失败" in data['message']


class TestWechatContacts:
    """微信联系人路由测试"""

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_get_contacts_default(self, mock_get_service, client):
        """测试获取联系人列表 - 默认参数"""
        mock_service = Mock()
        mock_service.get_contacts.return_value = [
            {"id": 1, "name": "张三", "wechat_id": "wx123"},
            {"id": 2, "name": "李四", "wechat_id": "wx456"}
        ]
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/contacts')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 2

        mock_service.get_contacts.assert_called_once_with(
            keyword=None,
            contact_type=None,
            starred_only=False,
            limit=100
        )

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_get_contacts_with_filters(self, mock_get_service, client):
        """测试获取联系人列表 - 带筛选参数"""
        mock_service = Mock()
        mock_service.get_contacts.return_value = [
            {"id": 1, "name": "张三", "wechat_id": "wx123", "is_starred": True}
        ]
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/contacts?keyword=张&type=contact&starred=true&limit=50')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        mock_service.get_contacts.assert_called_once_with(
            keyword="张",
            contact_type="contact",
            starred_only=True,
            limit=50
        )

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_get_contacts_service_error(self, mock_get_service, client):
        """测试获取联系人列表 - 服务层错误"""
        mock_service = Mock()
        mock_service.get_contacts.side_effect = Exception("数据库错误")
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/contacts')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_add_contact_success(self, mock_get_service, client):
        """测试添加联系人 - 成功"""
        mock_service = Mock()
        mock_service.add_contact.return_value = {
            "success": True,
            "message": "联系人添加成功",
            "contact_id": 100
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/wechat/contacts',
            json={
                "contact_name": "王五",
                "remark": "测试备注",
                "wechat_id": "wx789",
                "contact_type": "contact",
                "is_starred": True
            }
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        mock_service.add_contact.assert_called_once_with(
            contact_name="王五",
            remark="测试备注",
            wechat_id="wx789",
            contact_type="contact",
            is_starred=True
        )

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_add_contact_missing_name(self, mock_get_service, client):
        """测试添加联系人 - 缺少名称"""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/wechat/contacts',
            json={"remark": "测试"}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert "联系人名称不能为空" in data['message']

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_add_contact_empty_name(self, mock_get_service, client):
        """测试添加联系人 - 空名称"""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/wechat/contacts',
            json={"contact_name": "   "}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_add_contact_service_error(self, mock_get_service, client):
        """测试添加联系人 - 服务层错误"""
        mock_service = Mock()
        mock_service.add_contact.side_effect = Exception("添加失败")
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/wechat/contacts',
            json={"contact_name": "测试"}
        )
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "添加失败" in data['message']

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_get_contact_by_id_success(self, mock_get_service, client):
        """测试获取单个联系人 - 成功"""
        mock_service = Mock()
        mock_service.get_contact_by_id.return_value = {
            "id": 1,
            "name": "张三",
            "wechat_id": "wx123",
            "is_starred": True
        }
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/contacts/1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['name'] == "张三"

        mock_service.get_contact_by_id.assert_called_once_with(1)

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_get_contact_by_id_not_found(self, mock_get_service, client):
        """测试获取单个联系人 - 不存在"""
        mock_service = Mock()
        mock_service.get_contact_by_id.return_value = None
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/contacts/999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert "联系人不存在" in data['message']

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_get_contact_by_id_service_error(self, mock_get_service, client):
        """测试获取单个联系人 - 服务层错误"""
        mock_service = Mock()
        mock_service.get_contact_by_id.side_effect = Exception("查询失败")
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/contacts/1')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "查询失败" in data['message']

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_update_contact_success(self, mock_get_service, client):
        """测试更新联系人 - 成功"""
        mock_service = Mock()
        mock_service.update_contact.return_value = {
            "success": True,
            "message": "联系人更新成功"
        }
        mock_get_service.return_value = mock_service

        response = client.put(
            '/api/wechat/contacts/1',
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

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_update_contact_partial(self, mock_get_service, client):
        """测试更新联系人 - 部分更新"""
        mock_service = Mock()
        mock_service.update_contact.return_value = {
            "success": True,
            "message": "联系人更新成功"
        }
        mock_get_service.return_value = mock_service

        response = client.put(
            '/api/wechat/contacts/1',
            json={"is_starred": True}
        )
        assert response.status_code == 200

        mock_service.update_contact.assert_called_once_with(
            contact_id=1,
            contact_name=None,
            remark=None,
            wechat_id=None,
            contact_type=None,
            is_starred=True
        )

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_update_contact_failure(self, mock_get_service, client):
        """测试更新联系人 - 失败"""
        mock_service = Mock()
        mock_service.update_contact.return_value = {
            "success": False,
            "message": "联系人不存在"
        }
        mock_get_service.return_value = mock_service

        response = client.put(
            '/api/wechat/contacts/999',
            json={"contact_name": "测试"}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_update_contact_service_error(self, mock_get_service, client):
        """测试更新联系人 - 服务层错误"""
        mock_service = Mock()
        mock_service.update_contact.side_effect = Exception("更新失败")
        mock_get_service.return_value = mock_service

        response = client.put(
            '/api/wechat/contacts/1',
            json={"contact_name": "测试"}
        )
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "更新失败" in data['message']

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_delete_contact_success(self, mock_get_service, client):
        """测试删除联系人 - 成功"""
        mock_service = Mock()
        mock_service.delete_contact.return_value = {
            "success": True,
            "message": "联系人删除成功"
        }
        mock_get_service.return_value = mock_service

        response = client.delete('/api/wechat/contacts/1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        mock_service.delete_contact.assert_called_once_with(1)

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_delete_contact_failure(self, mock_get_service, client):
        """测试删除联系人 - 失败"""
        mock_service = Mock()
        mock_service.delete_contact.return_value = {
            "success": False,
            "message": "联系人不存在"
        }
        mock_get_service.return_value = mock_service

        response = client.delete('/api/wechat/contacts/999')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_delete_contact_service_error(self, mock_get_service, client):
        """测试删除联系人 - 服务层错误"""
        mock_service = Mock()
        mock_service.delete_contact.side_effect = Exception("删除失败")
        mock_get_service.return_value = mock_service

        response = client.delete('/api/wechat/contacts/1')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "删除失败" in data['message']

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_star_contact_add(self, mock_get_service, client):
        """测试设置联系人星标 - 添加星标"""
        mock_service = Mock()
        mock_service.star_contact.return_value = {
            "success": True,
            "message": "已添加星标"
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/wechat/contacts/1/star',
            json={"starred": True}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        mock_service.star_contact.assert_called_once_with(1, True)

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_star_contact_remove(self, mock_get_service, client):
        """测试设置联系人星标 - 取消星标"""
        mock_service = Mock()
        mock_service.star_contact.return_value = {
            "success": True,
            "message": "已取消星标"
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/wechat/contacts/1/star',
            json={"starred": False}
        )
        assert response.status_code == 200

        mock_service.star_contact.assert_called_once_with(1, False)

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_star_contact_default(self, mock_get_service, client):
        """测试设置联系人星标 - 默认添加星标"""
        mock_service = Mock()
        mock_service.star_contact.return_value = {
            "success": True,
            "message": "已添加星标"
        }
        mock_get_service.return_value = mock_service

        response = client.post('/api/wechat/contacts/1/star', json={})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        mock_service.star_contact.assert_called_once_with(1, True)

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_star_contact_failure(self, mock_get_service, client):
        """测试设置联系人星标 - 失败"""
        mock_service = Mock()
        mock_service.star_contact.return_value = {
            "success": False,
            "message": "联系人不存在"
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/wechat/contacts/999/star',
            json={"starred": True}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_star_contact_service_error(self, mock_get_service, client):
        """测试设置联系人星标 - 服务层错误"""
        mock_service = Mock()
        mock_service.star_contact.side_effect = Exception("操作失败")
        mock_get_service.return_value = mock_service

        response = client.post('/api/wechat/contacts/1/star')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "操作失败" in data['message']

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_unstar_all_success(self, mock_get_service, client):
        """测试取消所有联系人星标 - 成功"""
        mock_service = Mock()
        mock_service.unstar_all.return_value = {
            "success": True,
            "message": "已取消所有星标",
            "count": 5
        }
        mock_get_service.return_value = mock_service

        response = client.post('/api/wechat/contacts/unstar-all')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        mock_service.unstar_all.assert_called_once()

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_unstar_all_service_error(self, mock_get_service, client):
        """测试取消所有联系人星标 - 服务层错误"""
        mock_service = Mock()
        mock_service.unstar_all.side_effect = Exception("操作失败")
        mock_get_service.return_value = mock_service

        response = client.post('/api/wechat/contacts/unstar-all')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "操作失败" in data['message']

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_get_contact_context_success(self, mock_get_service, client):
        """测试获取联系人聊天上下文 - 成功"""
        mock_service = Mock()
        mock_service.get_contact_context.return_value = [
            {"id": 1, "content": "你好", "is_from_me": False},
            {"id": 2, "content": "你好呀", "is_from_me": True}
        ]
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/contacts/1/context')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['messages']) == 2
        assert data['count'] == 2

        mock_service.get_contact_context.assert_called_once_with(1)

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_get_contact_context_empty(self, mock_get_service, client):
        """测试获取联系人聊天上下文 - 空记录"""
        mock_service = Mock()
        mock_service.get_contact_context.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/contacts/1/context')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 0

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_get_contact_context_service_error(self, mock_get_service, client):
        """测试获取联系人聊天上下文 - 服务层错误"""
        mock_service = Mock()
        mock_service.get_contact_context.side_effect = Exception("查询失败")
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/contacts/1/context')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "查询失败" in data['message']


class TestWechatScan:
    """微信消息扫描路由测试"""

    @patch('app.tasks.wechat_tasks.scan_wechat_messages')
    def test_scan_messages_default(self, mock_scan_task, client):
        """测试扫描消息 - 默认参数"""
        mock_task = Mock()
        mock_task.id = "task-123"
        mock_scan_task.delay.return_value = mock_task

        response = client.post('/api/wechat/scan', json={})
        assert response.status_code == 202
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['task_id'] == "task-123"
        assert data['count'] == 0

        mock_scan_task.delay.assert_called_once_with(contact_id=None, limit=20)

    @patch('app.tasks.wechat_tasks.scan_wechat_messages')
    def test_scan_messages_with_params(self, mock_scan_task, client):
        """测试扫描消息 - 带参数"""
        mock_task = Mock()
        mock_task.id = "task-456"
        mock_scan_task.delay.return_value = mock_task

        response = client.post(
            '/api/wechat/scan',
            json={"contact_id": 10, "limit": 50}
        )
        assert response.status_code == 202

        mock_scan_task.delay.assert_called_once_with(contact_id=10, limit=50)

    @patch('app.tasks.wechat_tasks.scan_wechat_messages')
    def test_scan_messages_service_error(self, mock_scan_task, client):
        """测试扫描消息 - 服务层错误"""
        mock_scan_task.delay.side_effect = Exception("任务创建失败")

        response = client.post('/api/wechat/scan')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert "扫描失败" in data['message']


class TestWechatTest:
    """微信测试接口测试"""

    def test_wechat_test_endpoint(self, client):
        """测试微信接口"""
        response = client.get('/api/wechat/test')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == "微信服务运行正常"


class TestWechatEdgeCases:
    """微信路由边界条件测试"""

    @patch('app.routes.wechat.get_wechat_task_service')
    def test_get_tasks_with_invalid_limit(self, mock_get_service, client):
        """测试获取任务列表 - 无效的limit参数"""
        mock_service = Mock()
        mock_service.get_tasks.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/tasks?limit=abc')
        assert response.status_code == 200

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_add_contact_with_no_json(self, mock_get_service, client):
        """测试添加联系人 - 无JSON数据"""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        response = client.post('/api/wechat/contacts', json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert "联系人名称不能为空" in data['message']

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_update_contact_with_no_json(self, mock_get_service, client):
        """测试更新联系人 - 无JSON数据"""
        mock_service = Mock()
        mock_service.update_contact.return_value = {
            "success": True,
            "message": "联系人更新成功"
        }
        mock_get_service.return_value = mock_service

        response = client.put('/api/wechat/contacts/1', json={})
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

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_star_contact_with_no_json(self, mock_get_service, client):
        """测试设置星标 - 无JSON数据"""
        mock_service = Mock()
        mock_service.star_contact.return_value = {
            "success": True,
            "message": "已添加星标"
        }
        mock_get_service.return_value = mock_service

        response = client.post('/api/wechat/contacts/1/star', json={})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        mock_service.star_contact.assert_called_once_with(1, True)

    @patch('app.tasks.wechat_tasks.scan_wechat_messages')
    def test_scan_messages_with_no_json(self, mock_scan_task, client):
        """测试扫描消息 - 无JSON数据"""
        mock_task = Mock()
        mock_task.id = "task-789"
        mock_scan_task.delay.return_value = mock_task

        response = client.post('/api/wechat/scan', json={})
        assert response.status_code == 202
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['task_id'] == "task-789"

        mock_scan_task.delay.assert_called_once_with(contact_id=None, limit=20)

    @patch('app.routes.wechat.get_wechat_task_service')
    def test_get_tasks_with_zero_limit(self, mock_get_service, client):
        """测试获取任务列表 - limit为0"""
        mock_service = Mock()
        mock_service.get_tasks.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/tasks?limit=0')
        assert response.status_code == 200

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_get_contacts_with_zero_limit(self, mock_get_service, client):
        """测试获取联系人列表 - limit为0"""
        mock_service = Mock()
        mock_service.get_contacts.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/contacts?limit=0')
        assert response.status_code == 200

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_add_contact_with_whitespace_name(self, mock_get_service, client):
        """测试添加联系人 - 名称只有空格"""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/wechat/contacts',
            json={"contact_name": "  \t  "}
        )
        assert response.status_code == 400

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_get_contacts_with_empty_keyword(self, mock_get_service, client):
        """测试获取联系人列表 - 空关键词"""
        mock_service = Mock()
        mock_service.get_contacts.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/contacts?keyword=')
        assert response.status_code == 200

    @patch('app.routes.wechat.get_wechat_contact_service')
    def test_get_contacts_with_invalid_starred_param(self, mock_get_service, client):
        """测试获取联系人列表 - 无效的starred参数"""
        mock_service = Mock()
        mock_service.get_contacts.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get('/api/wechat/contacts?starred=invalid')
        assert response.status_code == 200
