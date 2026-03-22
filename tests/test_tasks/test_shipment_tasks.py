"""
Tasks 层测试
"""

import pytest
from unittest.mock import patch, MagicMock


class TestShipmentTasks:
    """发货单异步任务测试"""

    @patch("app.tasks.shipment_tasks.generate_shipment_order")
    def test_generate_shipment_order_task(self, mock_func):
        mock_func.return_value = {
            "success": True,
            "doc_name": "test.xlsx"
        }

        from app.tasks.shipment_tasks import generate_shipment_order
        result = generate_shipment_order(
            unit_name="测试单位",
            products=[{"product_name": "产品A", "quantity_tins": 1}]
        )

        assert result["success"] is True

    @patch("app.tasks.shipment_tasks.export_shipment_records_task")
    def test_export_shipment_records_task(self, mock_func):
        mock_func.return_value = {"success": True, "file_path": "/tmp/export.xlsx"}

        from app.tasks.shipment_tasks import export_shipment_records_task
        result = export_shipment_records_task()

        assert result["success"] is True