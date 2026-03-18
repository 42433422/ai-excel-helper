"""
提取日志服务单元测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from app.services.extract_log_service import ExtractLogService


class TestExtractLogService:
    """提取日志服务测试"""

    @pytest.fixture
    def service(self):
        """创建提取日志服务实例"""
        return ExtractLogService()

    class TestCreateLog:
        """create_log 方法测试"""

        @patch('app.services.extract_log_service.get_db')
        def test_create_log_success(self, mock_get_db, service):
            """测试成功创建日志"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.lastrowid = 1
            mock_db.execute.return_value = mock_result

            log_id = service.create_log(
                file_name="test.xlsx",
                data_type="products",
                file_path="/uploads/test.xlsx",
                total_rows=100,
                field_mapping={"code": "product_code", "name": "product_name"}
            )

            assert log_id == 1
            mock_db.commit.assert_called_once()

        @patch('app.services.extract_log_service.get_db')
        def test_create_log_failure(self, mock_get_db, service):
            """测试创建日志失败"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_db.execute.side_effect = Exception("Database error")

            log_id = service.create_log(
                file_name="test.xlsx",
                data_type="products",
                total_rows=100
            )

            assert log_id == -1

        @patch('app.services.extract_log_service.get_db')
        def test_create_log_without_optional_params(self, mock_get_db, service):
            """测试创建日志不带可选参数"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.lastrowid = 2
            mock_db.execute.return_value = mock_result

            log_id = service.create_log(
                file_name="test.xlsx",
                data_type="customers"
            )

            assert log_id == 2
            mock_db.commit.assert_called_once()

    class TestUpdateLog:
        """update_log 方法测试"""

        @patch('app.services.extract_log_service.get_db')
        def test_update_log_success(self, mock_get_db, service):
            """测试成功更新日志"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            result = service.update_log(
                log_id=1,
                status="completed",
                valid_rows=100,
                imported_rows=95,
                skipped_rows=3,
                failed_rows=2
            )

            assert result is True
            mock_db.commit.assert_called_once()

        @patch('app.services.extract_log_service.get_db')
        def test_update_log_pending_status(self, mock_get_db, service):
            """测试更新日志为 pending 状态"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            result = service.update_log(
                log_id=1,
                status="pending"
            )

            assert result is True
            mock_db.commit.assert_called_once()

        @patch('app.services.extract_log_service.get_db')
        def test_update_log_failed_status(self, mock_get_db, service):
            """测试更新日志为 failed 状态"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            result = service.update_log(
                log_id=1,
                status="failed",
                error_message="文件格式错误"
            )

            assert result is True
            mock_db.commit.assert_called_once()

        @patch('app.services.extract_log_service.get_db')
        def test_update_log_with_error_message(self, mock_get_db, service):
            """测试更新日志带错误消息"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            result = service.update_log(
                log_id=1,
                status="failed",
                error_message="数据库连接失败"
            )

            assert result is True

        @patch('app.services.extract_log_service.get_db')
        def test_update_log_failure(self, mock_get_db, service):
            """测试更新日志失败"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_db.execute.side_effect = Exception("Database error")

            result = service.update_log(
                log_id=1,
                status="completed"
            )

            assert result is False

    class TestGetLog:
        """get_log 方法测试"""

        @patch('app.services.extract_log_service.get_db')
        def test_get_log_success(self, mock_get_db, service):
            """测试成功获取日志"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_row = MagicMock()
            mock_row.id = 1
            mock_row.file_name = "test.xlsx"
            mock_row.file_path = "/uploads/test.xlsx"
            mock_row.data_type = "products"
            mock_row.total_rows = 100
            mock_row.valid_rows = 95
            mock_row.imported_rows = 90
            mock_row.skipped_rows = 3
            mock_row.failed_rows = 2
            mock_row.status = "completed"
            mock_row.error_message = None
            mock_row.field_mapping = '{"code": "product_code"}'
            mock_row.created_at = "2024-01-01 10:00:00"

            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_row
            mock_db.execute.return_value = mock_result

            log = service.get_log(log_id=1)

            assert log is not None
            assert log['id'] == 1
            assert log['file_name'] == "test.xlsx"
            assert log['data_type'] == "products"
            assert log['status'] == "completed"

        @patch('app.services.extract_log_service.get_db')
        def test_get_log_not_found(self, mock_get_db, service):
            """测试日志不存在"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.fetchone.return_value = None
            mock_db.execute.return_value = mock_result

            log = service.get_log(log_id=999)

            assert log is None

        @patch('app.services.extract_log_service.get_db')
        def test_get_log_with_null_field_mapping(self, mock_get_db, service):
            """测试获取日志 field_mapping 为空"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_row = MagicMock()
            mock_row.id = 1
            mock_row.file_name = "test.xlsx"
            mock_row.file_path = None
            mock_row.data_type = "products"
            mock_row.total_rows = 100
            mock_row.valid_rows = None
            mock_row.imported_rows = None
            mock_row.skipped_rows = None
            mock_row.failed_rows = None
            mock_row.status = "pending"
            mock_row.error_message = None
            mock_row.field_mapping = None
            mock_row.created_at = "2024-01-01 10:00:00"

            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_row
            mock_db.execute.return_value = mock_result

            log = service.get_log(log_id=1)

            assert log is not None
            assert log['field_mapping'] is None

    class TestGetLogs:
        """get_logs 方法测试"""

        @patch('app.services.extract_log_service.get_db')
        def test_get_logs_success(self, mock_get_db, service):
            """测试成功获取日志列表"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_row1 = MagicMock()
            mock_row1.id = 1
            mock_row1.file_name = "test1.xlsx"
            mock_row1.file_path = "/uploads/test1.xlsx"
            mock_row1.data_type = "products"
            mock_row1.total_rows = 100
            mock_row1.valid_rows = 95
            mock_row1.imported_rows = 90
            mock_row1.skipped_rows = 3
            mock_row1.failed_rows = 2
            mock_row1.status = "completed"
            mock_row1.created_at = "2024-01-01 10:00:00"

            mock_row2 = MagicMock()
            mock_row2.id = 2
            mock_row2.file_name = "test2.xlsx"
            mock_row2.file_path = "/uploads/test2.xlsx"
            mock_row2.data_type = "customers"
            mock_row2.total_rows = 50
            mock_row2.valid_rows = None
            mock_row2.imported_rows = None
            mock_row2.skipped_rows = None
            mock_row2.failed_rows = None
            mock_row2.status = "pending"
            mock_row2.created_at = "2024-01-02 10:00:00"

            mock_result = MagicMock()
            mock_result.fetchall.return_value = [mock_row1, mock_row2]
            mock_db.execute.return_value = mock_result

            logs = service.get_logs()

            assert len(logs) == 2
            assert logs[0]['id'] == 1
            assert logs[1]['id'] == 2

        @patch('app.services.extract_log_service.get_db')
        def test_get_logs_with_data_type_filter(self, mock_get_db, service):
            """测试带数据类型过滤"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_row = MagicMock()
            mock_row.id = 1
            mock_row.file_name = "test.xlsx"
            mock_row.file_path = "/uploads/test.xlsx"
            mock_row.data_type = "products"
            mock_row.total_rows = 100
            mock_row.valid_rows = None
            mock_row.imported_rows = None
            mock_row.skipped_rows = None
            mock_row.failed_rows = None
            mock_row.status = "pending"
            mock_row.created_at = "2024-01-01 10:00:00"

            mock_result = MagicMock()
            mock_result.fetchall.return_value = [mock_row]
            mock_db.execute.return_value = mock_result

            logs = service.get_logs(data_type="products")

            assert len(logs) == 1
            assert logs[0]['data_type'] == "products"

        @patch('app.services.extract_log_service.get_db')
        def test_get_logs_with_status_filter(self, mock_get_db, service):
            """测试带状态过滤"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_row = MagicMock()
            mock_row.id = 1
            mock_row.file_name = "test.xlsx"
            mock_row.file_path = "/uploads/test.xlsx"
            mock_row.data_type = "products"
            mock_row.total_rows = 100
            mock_row.valid_rows = 95
            mock_row.imported_rows = 90
            mock_row.skipped_rows = 3
            mock_row.failed_rows = 2
            mock_row.status = "completed"
            mock_row.created_at = "2024-01-01 10:00:00"

            mock_result = MagicMock()
            mock_result.fetchall.return_value = [mock_row]
            mock_db.execute.return_value = mock_result

            logs = service.get_logs(status="completed")

            assert len(logs) == 1
            assert logs[0]['status'] == "completed"

        @patch('app.services.extract_log_service.get_db')
        def test_get_logs_with_multiple_filters(self, mock_get_db, service):
            """测试带多个过滤条件"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_row = MagicMock()
            mock_row.id = 1
            mock_row.file_name = "test.xlsx"
            mock_row.file_path = "/uploads/test.xlsx"
            mock_row.data_type = "products"
            mock_row.total_rows = 100
            mock_row.valid_rows = 95
            mock_row.imported_rows = 90
            mock_row.skipped_rows = 3
            mock_row.failed_rows = 2
            mock_row.status = "completed"
            mock_row.created_at = "2024-01-01 10:00:00"

            mock_result = MagicMock()
            mock_result.fetchall.return_value = [mock_row]
            mock_db.execute.return_value = mock_result

            logs = service.get_logs(data_type="products", status="completed", limit=10, offset=0)

            assert len(logs) == 1

        @patch('app.services.extract_log_service.get_db')
        def test_get_logs_empty_list(self, mock_get_db, service):
            """测试获取空日志列表"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.fetchall.return_value = []
            mock_db.execute.return_value = mock_result

            logs = service.get_logs()

            assert logs == []

        @patch('app.services.extract_log_service.get_db')
        def test_get_logs_failure(self, mock_get_db, service):
            """测试获取日志列表失败"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_db.execute.side_effect = Exception("Database error")

            logs = service.get_logs()

            assert logs == []
