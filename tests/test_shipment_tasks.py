"""
发货单 Celery 任务测试
"""

import pytest
from datetime import timedelta
from unittest.mock import Mock, MagicMock, patch
import os
import sys


class TestShipmentTasksImport:
    """测试发货单任务模块导入"""

    def test_module_import(self):
        """测试模块可以成功导入"""
        from app.tasks import shipment_tasks
        assert shipment_tasks is not None

    def test_generate_shipment_order_exists(self):
        """测试 generate_shipment_order 函数存在"""
        from app.tasks.shipment_tasks import generate_shipment_order
        assert callable(generate_shipment_order)

    def test_generate_batch_shipment_orders_exists(self):
        """测试 generate_batch_shipment_orders 函数存在"""
        from app.tasks.shipment_tasks import generate_batch_shipment_orders
        assert callable(generate_batch_shipment_orders)

    def test_print_shipment_document_exists(self):
        """测试 print_shipment_document 函数存在"""
        from app.tasks.shipment_tasks import print_shipment_document
        assert callable(print_shipment_document)

    def test_cleanup_old_shipment_documents_exists(self):
        """测试 cleanup_old_shipment_documents 函数存在"""
        from app.tasks.shipment_tasks import cleanup_old_shipment_documents
        assert callable(cleanup_old_shipment_documents)


class TestGenerateShipmentOrderTask:
    """测试 generate_shipment_order 任务"""

    @patch('app.services.shipment_service.ShipmentService')
    def test_generate_shipment_order_success(self, mock_service_class):
        """测试成功生成发货单"""
        from app.tasks.shipment_tasks import generate_shipment_order

        mock_service = MagicMock()
        mock_service.generate_shipment_document.return_value = {
            "success": True,
            "doc_name": "test_doc.xlsx",
            "file_path": "/path/to/test_doc.xlsx",
            "message": "生成成功"
        }
        mock_service_class.return_value = mock_service

        result = generate_shipment_order(
            unit_name="测试公司",
            products=[{"product_name": "产品A", "quantity": 10}]
        )

        assert result["success"] is True
        assert result["doc_name"] == "test_doc.xlsx"
        mock_service.generate_shipment_document.assert_called_once()

    @patch('app.services.shipment_service.ShipmentService')
    def test_generate_shipment_order_with_date(self, mock_service_class):
        """测试带日期参数生成发货单"""
        from app.tasks.shipment_tasks import generate_shipment_order

        mock_service = MagicMock()
        mock_service.generate_shipment_document.return_value = {
            "success": True,
            "doc_name": "test_doc.xlsx",
            "file_path": "/path/to/test_doc.xlsx",
            "message": "生成成功"
        }
        mock_service_class.return_value = mock_service

        result = generate_shipment_order(
            unit_name="测试公司",
            products=[{"product_name": "产品A", "quantity": 10}],
            date="2026-03-17"
        )

        assert result["success"] is True
        mock_service.generate_shipment_document.assert_called_once()
        call_kwargs = mock_service.generate_shipment_document.call_args[1]
        assert call_kwargs["date"] == "2026-03-17"

    @patch('app.services.shipment_service.ShipmentService')
    def test_generate_shipment_order_failure(self, mock_service_class):
        """测试生成发货单失败"""
        from celery.app.task import MaxRetriesExceededError
        from app.tasks.shipment_tasks import generate_shipment_order

        mock_service = MagicMock()
        mock_service.generate_shipment_document.side_effect = Exception("生成失败")

        with patch.object(generate_shipment_order, 'retry', side_effect=MaxRetriesExceededError("max")):
            mock_service_class.return_value = mock_service

            result = generate_shipment_order(
                unit_name="测试公司",
                products=[{"product_name": "产品A", "quantity": 10}]
            )

        assert result["success"] is False
        assert "生成失败" in result["message"]


class TestGenerateBatchShipmentOrdersTask:
    """测试 generate_batch_shipment_orders 任务"""

    @patch('app.tasks.shipment_tasks.generate_shipment_order')
    @patch('app.services.shipment_service.ShipmentService')
    def test_generate_batch_shipment_orders_success(self, mock_service_class, mock_generate):
        """测试批量生成发货单成功"""
        from app.tasks.shipment_tasks import generate_batch_shipment_orders

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        mock_generate.return_value = {"success": True}

        orders = [
            {"unit_name": "公司A", "products": [{"product_name": "产品A", "quantity": 10}]},
            {"unit_name": "公司B", "products": [{"product_name": "产品B", "quantity": 5}]}
        ]

        result = generate_batch_shipment_orders(orders=orders)

        assert result["success"] is True
        assert result["total"] == 2
        assert result["succeeded"] == 2
        assert result["failed"] == 0

    @patch('app.tasks.shipment_tasks.generate_shipment_order')
    @patch('app.services.shipment_service.ShipmentService')
    def test_generate_batch_shipment_orders_partial_failure(self, mock_service_class, mock_generate):
        """测试批量生成部分失败"""
        from app.tasks.shipment_tasks import generate_batch_shipment_orders

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        mock_generate.side_effect = [
            {"success": True},
            {"success": False, "message": "生成失败"}
        ]

        orders = [
            {"unit_name": "公司A", "products": [{"product_name": "产品A", "quantity": 10}]},
            {"unit_name": "公司B", "products": [{"product_name": "产品B", "quantity": 5}]}
        ]

        result = generate_batch_shipment_orders(orders=orders)

        assert result["success"] is False
        assert result["total"] == 2
        assert result["succeeded"] == 1
        assert result["failed"] == 1


class TestPrintShipmentDocumentTask:
    """测试 print_shipment_document 任务"""

    @patch('os.path.exists')
    @patch('app.services.shipment_service.ShipmentService')
    def test_print_shipment_document_success(self, mock_service_class, mock_exists):
        """测试成功打印发货单"""
        from app.tasks.shipment_tasks import print_shipment_document

        mock_exists.return_value = True

        mock_service = MagicMock()
        mock_service.mark_as_printed.return_value = {"printed_at": "2026-03-17 10:00:00"}
        mock_service_class.return_value = mock_service

        result = print_shipment_document(
            file_path="/path/to/doc.xlsx",
            printer_name="默认打印机",
            copies=1
        )

        assert result["success"] is True
        mock_service.mark_as_printed.assert_called_once()

    @patch('os.path.exists')
    @patch('app.services.shipment_service.ShipmentService')
    def test_print_shipment_document_file_not_exists(self, mock_service_class, mock_exists):
        """测试文件不存在的情况"""
        from app.tasks.shipment_tasks import print_shipment_document

        mock_exists.return_value = False

        result = print_shipment_document(
            file_path="/nonexistent/doc.xlsx"
        )

        assert result["success"] is False
        assert "文件不存在" in result["message"]

    @patch('os.path.exists')
    @patch('app.services.shipment_service.ShipmentService')
    def test_print_shipment_document_with_copies(self, mock_service_class, mock_exists):
        """测试多份打印"""
        from app.tasks.shipment_tasks import print_shipment_document

        mock_exists.return_value = True

        mock_service = MagicMock()
        mock_service.mark_as_printed.return_value = {"printed_at": "2026-03-17 10:00:00"}
        mock_service_class.return_value = mock_service

        result = print_shipment_document(
            file_path="/path/to/doc.xlsx",
            copies=3
        )

        assert result["success"] is True


class TestCleanupOldShipmentDocumentsTask:
    """测试 cleanup_old_shipment_documents 任务"""

    @patch('os.listdir')
    @patch('os.remove')
    @patch('app.services.shipment_service.ShipmentService')
    def test_cleanup_old_documents_success(self, mock_service_class, mock_remove,
                                           mock_listdir):
        """测试成功清理旧文档"""
        from datetime import datetime
        from app.tasks.shipment_tasks import cleanup_old_shipment_documents

        mock_service = MagicMock()
        mock_service.output_dir = "/test/output"
        mock_service_class.return_value = mock_service

        mock_listdir.return_value = ["old_doc1.xlsx", "old_doc2.xlsx", "recent_doc.xlsx"]

        old_timestamp = (datetime.now() - timedelta(days=100)).timestamp()
        new_timestamp = (datetime.now() - timedelta(days=10)).timestamp()

        def mock_getmtime_side_effect(path):
            if "old" in path:
                return old_timestamp
            return new_timestamp

        with patch('os.path.exists', return_value=True), \
             patch('os.path.isfile', return_value=True), \
             patch('os.path.getmtime', side_effect=mock_getmtime_side_effect), \
             patch('datetime.datetime') as mock_datetime_cls:
            mock_datetime_cls.now.return_value = datetime.now()
            mock_datetime_cls.fromtimestamp.side_effect = lambda ts: datetime.fromtimestamp(ts)

            result = cleanup_old_shipment_documents(days=90)

        assert result == 2


class TestShipmentTasksAttributes:
    """测试任务属性"""

    def test_generate_shipment_order_has_bind(self):
        """测试 generate_shipment_order 有 bind=True"""
        from app.tasks.shipment_tasks import generate_shipment_order
        assert hasattr(generate_shipment_order, 'bind')

    def test_generate_batch_shipment_orders_has_max_retries(self):
        """测试批量生成任务有 max_retries"""
        from app.tasks.shipment_tasks import generate_batch_shipment_orders
        assert hasattr(generate_batch_shipment_orders, 'max_retries')

    def test_print_shipment_document_has_max_retries(self):
        """测试打印任务有 max_retries"""
        from app.tasks.shipment_tasks import print_shipment_document
        assert hasattr(print_shipment_document, 'max_retries')

    def test_cleanup_old_shipment_documents_no_bind(self):
        """测试清理任务不需要 bind"""
        from app.tasks.shipment_tasks import cleanup_old_shipment_documents
        assert callable(cleanup_old_shipment_documents)
