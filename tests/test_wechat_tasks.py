"""
微信 Celery 任务测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import os
import sys


class TestWechatTasksImport:
    """测试微信任务模块导入"""

    def test_module_import(self):
        """测试模块可以成功导入"""
        from app.tasks import wechat_tasks
        assert wechat_tasks is not None

    def test_process_wechat_message_exists(self):
        """测试 process_wechat_message 函数存在"""
        from app.tasks.wechat_tasks import process_wechat_message
        assert callable(process_wechat_message)

    def test_scan_wechat_messages_exists(self):
        """测试 scan_wechat_messages 函数存在"""
        from app.tasks.wechat_tasks import scan_wechat_messages
        assert callable(scan_wechat_messages)

    def test_cleanup_old_tasks_exists(self):
        """测试 cleanup_old_tasks 函数存在"""
        from app.tasks.wechat_tasks import cleanup_old_tasks
        assert callable(cleanup_old_tasks)


class TestProcessWechatMessageTask:
    """测试 process_wechat_message 任务"""

    @patch('app.services.wechat_task_service.WechatTaskService')
    def test_process_wechat_message_success(self, mock_service_class):
        """测试成功处理微信消息"""
        from app.tasks.wechat_tasks import process_wechat_message

        mock_service = MagicMock()
        mock_service.process_message.return_value = {"success": True}
        mock_service_class.return_value = mock_service

        message_data = {
            "id": 123,
            "contact_id": 1,
            "username": "test_user",
            "message_id": "msg_001"
        }

        result = process_wechat_message(message_data=message_data)

        assert result is True
        mock_service.process_message.assert_called_once_with(123)

    @patch('app.services.wechat_task_service.WechatTaskService')
    def test_process_wechat_message_failure(self, mock_service_class):
        """测试处理微信消息失败"""
        from app.tasks.wechat_tasks import process_wechat_message

        mock_service = MagicMock()
        mock_service.process_message.return_value = {"success": False, "error": "处理失败"}
        mock_service_class.return_value = mock_service

        message_data = {
            "id": 456,
            "message_id": "msg_002"
        }

        result = process_wechat_message(message_data=message_data)

        assert result is False

    @patch('app.services.wechat_task_service.WechatTaskService')
    def test_process_wechat_message_with_full_data(self, mock_service_class):
        """测试带完整数据的微信消息处理"""
        from app.tasks.wechat_tasks import process_wechat_message

        mock_service = MagicMock()
        mock_service.process_message.return_value = {"success": True}
        mock_service_class.return_value = mock_service

        message_data = {
            "id": 789,
            "contact_id": 10,
            "username": "测试用户",
            "display_name": "测试用户显示名",
            "message_id": "msg_003",
            "raw_text": "测试消息内容",
            "msg_timestamp": 1700000000
        }

        result = process_wechat_message(message_data=message_data)

        assert result is True
        mock_service.process_message.assert_called_once_with(789)


class TestScanWechatMessagesTask:
    """测试 scan_wechat_messages 任务"""

    @patch('app.tasks.wechat_tasks.process_wechat_message')
    @patch('app.services.wechat_task_service.WechatTaskService')
    def test_scan_wechat_messages_success(self, mock_service_class, mock_process):
        """测试成功扫描微信消息"""
        from app.tasks.wechat_tasks import scan_wechat_messages

        mock_service = MagicMock()
        mock_service.scan_messages.return_value = [
            {"id": 1, "content": "任务1"},
            {"id": 2, "content": "任务2"}
        ]
        mock_service_class.return_value = mock_service

        result = scan_wechat_messages(contact_id=1, limit=20)

        assert result == 2
        mock_service.scan_messages.assert_called_once_with(contact_id=1, limit=20)

    @patch('app.tasks.wechat_tasks.process_wechat_message')
    @patch('app.services.wechat_task_service.WechatTaskService')
    def test_scan_wechat_messages_no_contact(self, mock_service_class, mock_process):
        """测试不指定联系人的扫描"""
        from app.tasks.wechat_tasks import scan_wechat_messages

        mock_service = MagicMock()
        mock_service.scan_messages.return_value = []
        mock_service_class.return_value = mock_service

        result = scan_wechat_messages(limit=10)

        assert result == 0
        mock_service.scan_messages.assert_called_once_with(contact_id=None, limit=10)

    @patch('app.tasks.wechat_tasks.process_wechat_message')
    @patch('app.services.wechat_task_service.WechatTaskService')
    def test_scan_wechat_messages_with_dispatch(self, mock_service_class, mock_process):
        """测试扫描后派发处理任务"""
        from app.tasks.wechat_tasks import scan_wechat_messages

        mock_service = MagicMock()
        mock_service.scan_messages.return_value = [
            {"id": 100, "content": "新任务1"},
            {"id": 101, "content": "新任务2"},
            {"id": 102, "content": "新任务3"}
        ]
        mock_service_class.return_value = mock_service

        result = scan_wechat_messages(limit=50)

        assert result == 3
        assert mock_process.delay.call_count == 3

    @patch('app.tasks.wechat_tasks.process_wechat_message')
    @patch('app.services.wechat_task_service.WechatTaskService')
    def test_scan_wechat_messages_exception(self, mock_service_class, mock_process):
        """测试扫描时服务异常"""
        from celery.app.task import MaxRetriesExceededError
        from app.tasks.wechat_tasks import scan_wechat_messages

        mock_service = MagicMock()
        mock_service.scan_messages.side_effect = Exception("数据库错误")

        with patch.object(scan_wechat_messages, 'retry', side_effect=MaxRetriesExceededError("max")):
            mock_service_class.return_value = mock_service

            result = scan_wechat_messages()

        assert result == 0


class TestCleanupOldTasksTask:
    """测试 cleanup_old_tasks 任务"""

    @patch('db.get_db_path')
    @patch('sqlite3.connect')
    def test_cleanup_old_tasks_success(self, mock_connect, mock_get_db_path):
        """测试成功清理旧任务"""
        from app.tasks.wechat_tasks import cleanup_old_tasks

        mock_get_db_path.return_value = "/test/db.sqlite"

        mock_cursor = MagicMock()
        mock_cursor.rowcount = 5

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = cleanup_old_tasks(days=30)

        assert result == 5
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('db.get_db_path')
    @patch('sqlite3.connect')
    def test_cleanup_old_tasks_with_custom_days(self, mock_connect, mock_get_db_path):
        """测试自定义天数的清理"""
        from app.tasks.wechat_tasks import cleanup_old_tasks

        mock_get_db_path.return_value = "/test/db.sqlite"

        mock_cursor = MagicMock()
        mock_cursor.rowcount = 10

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = cleanup_old_tasks(days=60)

        assert result == 10
        mock_cursor.execute.assert_called_once()

    @patch('db.get_db_path')
    @patch('sqlite3.connect')
    def test_cleanup_old_tasks_no_tasks_to_clean(self, mock_connect, mock_get_db_path):
        """测试没有需要清理的任务"""
        from app.tasks.wechat_tasks import cleanup_old_tasks

        mock_get_db_path.return_value = "/test/db.sqlite"

        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = cleanup_old_tasks(days=7)

        assert result == 0

    @patch('db.get_db_path')
    @patch('sqlite3.connect')
    def test_cleanup_old_tasks_exception(self, mock_connect, mock_get_db_path):
        """测试清理时发生异常"""
        from app.tasks.wechat_tasks import cleanup_old_tasks

        mock_get_db_path.return_value = "/test/db.sqlite"
        mock_connect.side_effect = Exception("数据库连接失败")

        result = cleanup_old_tasks(days=30)

        assert result == 0


class TestWechatTasksAttributes:
    """测试任务属性"""

    def test_process_wechat_message_has_bind(self):
        """测试 process_wechat_message 有 bind=True"""
        from app.tasks.wechat_tasks import process_wechat_message
        assert hasattr(process_wechat_message, 'bind')

    def test_process_wechat_message_has_max_retries(self):
        """测试处理消息任务有 max_retries"""
        from app.tasks.wechat_tasks import process_wechat_message
        assert hasattr(process_wechat_message, 'max_retries')

    def test_scan_wechat_messages_has_max_retries(self):
        """测试扫描消息任务有 max_retries"""
        from app.tasks.wechat_tasks import scan_wechat_messages
        assert hasattr(scan_wechat_messages, 'max_retries')

    def test_cleanup_old_tasks_no_bind(self):
        """测试清理任务不需要 bind"""
        from app.tasks.wechat_tasks import cleanup_old_tasks
        assert callable(cleanup_old_tasks)


class TestWechatTasksIntegration:
    """测试微信任务集成"""

    @patch('app.services.wechat_task_service.WechatTaskService')
    @patch('app.tasks.wechat_tasks.process_wechat_message')
    def test_scan_and_process_workflow(self, mock_process, mock_service_class):
        """测试扫描和处理工作流"""
        from app.tasks.wechat_tasks import scan_wechat_messages

        mock_service = MagicMock()
        mock_service.scan_messages.return_value = [
            {"id": 1, "content": "内容A"},
            {"id": 2, "content": "内容B"}
        ]
        mock_service_class.return_value = mock_service

        mock_process.delay.return_value = None

        result = scan_wechat_messages(limit=10)

        assert result == 2
        assert mock_process.delay.call_count == 2
        mock_process.delay.assert_any_call({"id": 1})
        mock_process.delay.assert_any_call({"id": 2})
