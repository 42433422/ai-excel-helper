"""
发货单路由测试
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestShipmentGenerate:
    """发货单生成测试"""

    @patch('app.routes.shipment.ShipmentService')
    def test_generate_shipment_success(self, mock_service_class, client):
        """测试成功生成发货单"""
        mock_service = Mock()
        mock_service.generate_shipment_document.return_value = {
            "success": True,
            "doc_name": "发货单_测试公司.xlsx",
            "file_path": "/path/to/file.xlsx"
        }
        mock_service_class.return_value = mock_service

        response = client.post(
            '/api/shipment/generate',
            json={
                "unit_name": "测试公司",
                "products": [
                    {"name": "产品A", "quantity": 10, "unit": "个", "price": 100},
                    {"name": "产品B", "quantity": 5, "unit": "个", "price": 50}
                ],
                "date": "2026-03-17"
            },
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "doc_name" in data
        assert "file_path" in data
        mock_service.generate_shipment_document.assert_called_once()

    def test_generate_shipment_missing_unit_name(self, client):
        """测试缺少单位名称"""
        response = client.post(
            '/api/shipment/generate',
            json={
                "products": [{"name": "产品A", "quantity": 10, "unit": "个", "price": 100}]
            },
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "单位名称不能为空" in data["message"]

    def test_generate_shipment_empty_unit_name(self, client):
        """测试空单位名称"""
        response = client.post(
            '/api/shipment/generate',
            json={
                "unit_name": "",
                "products": [{"name": "产品A", "quantity": 10, "unit": "个", "price": 100}]
            },
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "单位名称不能为空" in data["message"]

    def test_generate_shipment_missing_products(self, client):
        """测试缺少产品列表"""
        response = client.post(
            '/api/shipment/generate',
            json={
                "unit_name": "测试公司"
            },
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "产品列表不能为空" in data["message"]

    def test_generate_shipment_empty_products(self, client):
        """测试空产品列表"""
        response = client.post(
            '/api/shipment/generate',
            json={
                "unit_name": "测试公司",
                "products": []
            },
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "产品列表不能为空" in data["message"]

    @patch('app.routes.shipment.ShipmentService')
    def test_generate_shipment_service_error(self, mock_service_class, client):
        """测试服务层错误"""
        mock_service = Mock()
        mock_service.generate_shipment_document.return_value = {
            "success": False,
            "message": "生成文档失败"
        }
        mock_service_class.return_value = mock_service

        response = client.post(
            '/api/shipment/generate',
            json={
                "unit_name": "测试公司",
                "products": [{"name": "产品A", "quantity": 10, "unit": "个", "price": 100}]
            },
            content_type='application/json'
        )

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    def test_generate_shipment_exception(self, client):
        """测试异常情况"""
        with patch('app.routes.shipment.ShipmentService') as mock_service_class:
            mock_service_class.side_effect = Exception("数据库连接失败")

            response = client.post(
                '/api/shipment/generate',
                json={
                    "unit_name": "测试公司",
                    "products": [{"name": "产品A", "quantity": 10, "unit": "个", "price": 100}]
                },
                content_type='application/json'
            )

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False
            assert "生成失败" in data["message"]

    @patch('app.routes.shipment.ShipmentService')
    def test_generate_shipment_with_date(self, mock_service_class, client):
        """测试带日期生成发货单"""
        mock_service = Mock()
        mock_service.generate_shipment_document.return_value = {
            "success": True,
            "doc_name": "发货单_测试公司.xlsx",
            "file_path": "/path/to/file.xlsx"
        }
        mock_service_class.return_value = mock_service

        response = client.post(
            '/api/shipment/generate',
            json={
                "unit_name": "测试公司",
                "products": [{"name": "产品A", "quantity": 10, "unit": "个", "price": 100}],
                "date": "2026-03-17"
            },
            content_type='application/json'
        )

        assert response.status_code == 200
        mock_service.generate_shipment_document.assert_called_once_with(
            unit_name="测试公司",
            products=[{"name": "产品A", "quantity": 10, "unit": "个", "price": 100}],
            date="2026-03-17"
        )


class TestShipmentPrint:
    """发货单打印测试"""

    @patch('app.routes.shipment.os.path.exists')
    @patch('app.routes.shipment.ShipmentService')
    def test_print_shipment_success(self, mock_service_class, mock_exists, client):
        """测试成功打印发货单"""
        mock_exists.return_value = True
        mock_service = Mock()
        mock_service.mark_as_printed.return_value = {
            "success": True,
            "message": "打印成功",
            "printed_at": "2026-03-17 10:00:00"
        }
        mock_service_class.return_value = mock_service

        response = client.post(
            '/api/shipment/print',
            json={
                "file_path": "/path/to/file.xlsx",
                "order_id": "ORD001",
                "printer_name": "HP Printer"
            },
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_service.mark_as_printed.assert_called_once()

    def test_print_shipment_missing_file_path(self, client):
        """测试缺少文件路径"""
        response = client.post(
            '/api/shipment/print',
            json={},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "文件路径不能为空" in data["message"]

    def test_print_shipment_empty_file_path(self, client):
        """测试空文件路径"""
        response = client.post(
            '/api/shipment/print',
            json={"file_path": ""},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "文件路径不能为空" in data["message"]

    @patch('app.routes.shipment.os.path.exists')
    def test_print_shipment_file_not_found(self, mock_exists, client):
        """测试文件不存在"""
        mock_exists.return_value = False

        response = client.post(
            '/api/shipment/print',
            json={"file_path": "/path/to/nonexistent.xlsx"},
            content_type='application/json'
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "文件不存在" in data["message"]

    @patch('app.routes.shipment.os.path.exists')
    @patch('app.routes.shipment.ShipmentService')
    def test_print_shipment_without_optional_params(self, mock_service_class, mock_exists, client):
        """测试不带可选参数打印"""
        mock_exists.return_value = True
        mock_service = Mock()
        mock_service.mark_as_printed.return_value = {
            "success": True,
            "message": "打印成功"
        }
        mock_service_class.return_value = mock_service

        response = client.post(
            '/api/shipment/print',
            json={"file_path": "/path/to/file.xlsx"},
            content_type='application/json'
        )

        assert response.status_code == 200
        mock_service.mark_as_printed.assert_called_once_with(
            file_path="/path/to/file.xlsx",
            order_id=None,
            printer_name=None
        )

    @patch('app.routes.shipment.os.path.exists')
    @patch('app.routes.shipment.ShipmentService')
    def test_print_shipment_service_error(self, mock_service_class, mock_exists, client):
        """测试服务层错误"""
        mock_exists.return_value = True
        mock_service = Mock()
        mock_service.mark_as_printed.return_value = {
            "success": False,
            "message": "更新打印状态失败"
        }
        mock_service_class.return_value = mock_service

        response = client.post(
            '/api/shipment/print',
            json={"file_path": "/path/to/file.xlsx"},
            content_type='application/json'
        )

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    def test_print_shipment_exception(self, client):
        """测试异常情况"""
        with patch('app.routes.shipment.os.path.exists', side_effect=Exception("文件系统错误")):
            response = client.post(
                '/api/shipment/print',
                json={"file_path": "/path/to/file.xlsx"},
                content_type='application/json'
            )

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False
            assert "打印失败" in data["message"]


class TestShipmentList:
    """发货单列表测试"""

    @patch('app.routes.shipment.ShipmentService')
    def test_list_shipments_success(self, mock_service_class, client):
        """测试成功获取发货单列表"""
        mock_service = Mock()
        mock_service.query_shipment_orders.return_value = {
            "success": True,
            "data": [
                {"order_number": "ORD001", "unit_name": "公司A", "date": "2026-03-17"},
                {"order_number": "ORD002", "unit_name": "公司B", "date": "2026-03-16"}
            ],
            "total": 2
        }
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/list')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert "total" in data
        mock_service.query_shipment_orders.assert_called_once()

    @patch('app.routes.shipment.ShipmentService')
    def test_list_shipments_with_unit_filter(self, mock_service_class, client):
        """测试按单位筛选"""
        mock_service = Mock()
        mock_service.query_shipment_orders.return_value = {
            "success": True,
            "data": [],
            "total": 0
        }
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/list?unit=测试公司')

        assert response.status_code == 200
        mock_service.query_shipment_orders.assert_called_once_with(
            unit_name="测试公司",
            start_date=None,
            end_date=None,
            page=1,
            per_page=20
        )

    @patch('app.routes.shipment.ShipmentService')
    def test_list_shipments_with_date_range(self, mock_service_class, client):
        """测试按日期范围筛选"""
        mock_service = Mock()
        mock_service.query_shipment_orders.return_value = {
            "success": True,
            "data": [],
            "total": 0
        }
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/list?start_date=2026-03-01&end_date=2026-03-31')

        assert response.status_code == 200
        mock_service.query_shipment_orders.assert_called_once_with(
            unit_name=None,
            start_date="2026-03-01",
            end_date="2026-03-31",
            page=1,
            per_page=20
        )

    @patch('app.routes.shipment.ShipmentService')
    def test_list_shipments_with_pagination(self, mock_service_class, client):
        """测试分页"""
        mock_service = Mock()
        mock_service.query_shipment_orders.return_value = {
            "success": True,
            "data": [],
            "total": 0
        }
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/list?page=2&per_page=50')

        assert response.status_code == 200
        mock_service.query_shipment_orders.assert_called_once_with(
            unit_name=None,
            start_date=None,
            end_date=None,
            page=2,
            per_page=50
        )

    @patch('app.routes.shipment.ShipmentService')
    def test_list_shipments_with_all_filters(self, mock_service_class, client):
        """测试所有筛选条件"""
        mock_service = Mock()
        mock_service.query_shipment_orders.return_value = {
            "success": True,
            "data": [],
            "total": 0
        }
        mock_service_class.return_value = mock_service

        response = client.get(
            '/api/shipment/list?unit=测试公司&start_date=2026-03-01&end_date=2026-03-31&page=1&per_page=10'
        )

        assert response.status_code == 200
        mock_service.query_shipment_orders.assert_called_once_with(
            unit_name="测试公司",
            start_date="2026-03-01",
            end_date="2026-03-31",
            page=1,
            per_page=10
        )

    @patch('app.routes.shipment.ShipmentService')
    def test_list_shipments_invalid_page(self, mock_service_class, client):
        """测试无效页码"""
        mock_service = Mock()
        mock_service.query_shipment_orders.side_effect = ValueError("无效的页码")
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/list?page=abc')

        assert response.status_code == 500

    @patch('app.routes.shipment.ShipmentService')
    def test_list_shipments_exception(self, mock_service_class, client):
        """测试异常情况"""
        mock_service_class.side_effect = Exception("数据库连接失败")

        response = client.get('/api/shipment/list')

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "查询失败" in data["message"]


class TestShipmentDownload:
    """发货单下载测试"""

    @patch('app.routes.shipment.os.path.exists')
    @patch('app.routes.shipment.send_file')
    @patch('app.routes.shipment.ShipmentService')
    def test_download_shipment_success(self, mock_service_class, mock_send_file, mock_exists, client):
        """测试成功下载发货单"""
        mock_service = Mock()
        mock_service.download_shipment_order.return_value = {
            "success": True,
            "file_path": "/path/to/file.xlsx"
        }
        mock_service_class.return_value = mock_service
        mock_exists.return_value = True
        mock_send_file.return_value = "file content"

        response = client.get('/api/shipment/download/file.xlsx')

        assert response.status_code == 200
        mock_service.download_shipment_order.assert_called_once_with("file.xlsx")
        mock_send_file.assert_called_once()

    @patch('app.routes.shipment.ShipmentService')
    def test_download_shipment_not_found(self, mock_service_class, client):
        """测试文件不存在"""
        mock_service = Mock()
        mock_service.download_shipment_order.return_value = {
            "success": False,
            "message": "文件不存在"
        }
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/download/nonexistent.xlsx')

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False

    @patch('app.routes.shipment.os.path.exists')
    @patch('app.routes.shipment.ShipmentService')
    def test_download_shipment_file_missing(self, mock_service_class, mock_exists, client):
        """测试文件路径存在但文件不存在"""
        mock_service = Mock()
        mock_service.download_shipment_order.return_value = {
            "success": True,
            "file_path": "/path/to/file.xlsx"
        }
        mock_service_class.return_value = mock_service
        mock_exists.return_value = False

        response = client.get('/api/shipment/download/file.xlsx')

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "文件不存在" in data["message"]

    @patch('app.routes.shipment.ShipmentService')
    def test_download_shipment_exception(self, mock_service_class, client):
        """测试异常情况"""
        mock_service_class.side_effect = Exception("文件系统错误")

        response = client.get('/api/shipment/download/file.xlsx')

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "下载失败" in data["message"]


class TestOrderNumber:
    """订单编号测试"""

    def test_get_next_order_number_default(self, client):
        """测试获取默认订单编号"""
        response = client.get('/api/shipment/orders/next_number')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert "order_number" in data["data"]
        assert "sequence" in data["data"]
        assert "year_month" in data["data"]
        assert data["data"]["sequence"] == 1

    def test_get_next_order_number_with_suffix(self, client):
        """测试带后缀的订单编号"""
        response = client.get('/api/shipment/orders/next_number?suffix=B')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["order_number"].endswith("B")


class TestPurchaseUnits:
    """购买单位测试"""

    @patch('app.routes.shipment.ShipmentService')
    def test_get_purchase_units_success(self, mock_service_class, client):
        """测试成功获取购买单位"""
        mock_service = Mock()
        mock_service.get_purchase_units.return_value = [
            "公司A", "公司B", "公司C"
        ]
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/orders/purchase-units')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert "count" in data
        assert data["count"] == 3
        assert len(data["data"]) == 3

    @patch('app.routes.shipment.ShipmentService')
    def test_get_purchase_units_empty(self, mock_service_class, client):
        """测试空购买单位列表"""
        mock_service = Mock()
        mock_service.get_purchase_units.return_value = []
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/orders/purchase-units')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 0
        assert len(data["data"]) == 0

    @patch('app.routes.shipment.ShipmentService')
    def test_get_purchase_units_exception(self, mock_service_class, client):
        """测试异常情况"""
        mock_service_class.side_effect = Exception("数据库错误")

        response = client.get('/api/shipment/orders/purchase-units')

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False


class TestClearShipment:
    """清理出货记录测试"""

    def test_clear_shipment_success(self, client):
        """测试成功清理出货记录"""
        response = client.post(
            '/api/shipment/orders/clear-shipment',
            json={"purchase_unit": "测试公司"},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "已清理" in data["message"]
        assert "deleted_orders" in data

    def test_clear_shipment_missing_purchase_unit(self, client):
        """测试缺少购买单位参数"""
        response = client.post(
            '/api/shipment/orders/clear-shipment',
            json={},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "缺少购买单位参数" in data["message"]

    def test_clear_shipment_empty_purchase_unit(self, client):
        """测试空购买单位"""
        response = client.post(
            '/api/shipment/orders/clear-shipment',
            json={"purchase_unit": ""},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "缺少购买单位参数" in data["message"]


class TestOrders:
    """订单管理测试"""

    @patch('app.routes.shipment.ShipmentService')
    def test_get_orders_success(self, mock_service_class, client):
        """测试成功获取订单列表"""
        mock_service = Mock()
        mock_service.get_orders.return_value = [
            {"order_number": "ORD001", "unit_name": "公司A"},
            {"order_number": "ORD002", "unit_name": "公司B"}
        ]
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/orders')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert "count" in data
        assert data["count"] == 2

    @patch('app.routes.shipment.ShipmentService')
    def test_get_orders_with_limit(self, mock_service_class, client):
        """测试带限制获取订单"""
        mock_service = Mock()
        mock_service.get_orders.return_value = []
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/orders?limit=50')

        assert response.status_code == 200
        mock_service.get_orders.assert_called_once_with(50)

    @patch('app.routes.shipment.ShipmentService')
    def test_get_orders_exception(self, mock_service_class, client):
        """测试异常情况"""
        mock_service_class.side_effect = Exception("数据库错误")

        response = client.get('/api/shipment/orders')

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    @patch('app.routes.shipment.ShipmentService')
    def test_search_orders_success(self, mock_service_class, client):
        """测试成功搜索订单"""
        mock_service = Mock()
        mock_service.search_orders.return_value = [
            {"order_number": "ORD001", "unit_name": "测试公司"}
        ]
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/orders/search?q=测试')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert "count" in data
        mock_service.search_orders.assert_called_once_with("测试")

    @patch('app.routes.shipment.ShipmentService')
    def test_search_orders_empty_query(self, mock_service_class, client):
        """测试空搜索查询"""
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/orders/search?q=')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"] == []
        assert data["count"] == 0
        mock_service.search_orders.assert_not_called()

    @patch('app.routes.shipment.ShipmentService')
    def test_search_orders_no_results(self, mock_service_class, client):
        """测试无搜索结果"""
        mock_service = Mock()
        mock_service.search_orders.return_value = []
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/orders/search?q=不存在的订单')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 0

    @patch('app.routes.shipment.ShipmentService')
    def test_search_orders_exception(self, mock_service_class, client):
        """测试异常情况"""
        mock_service_class.side_effect = Exception("搜索错误")

        response = client.get('/api/shipment/orders/search?q=测试')

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    @patch('app.routes.shipment.ShipmentService')
    def test_get_order_success(self, mock_service_class, client):
        """测试成功获取订单详情"""
        mock_service = Mock()
        mock_service.get_order.return_value = {
            "order_number": "ORD001",
            "unit_name": "测试公司",
            "status": "pending"
        }
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/orders/ORD001')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        mock_service.get_order.assert_called_once_with("ORD001")

    @patch('app.routes.shipment.ShipmentService')
    def test_get_order_not_found(self, mock_service_class, client):
        """测试订单不存在"""
        mock_service = Mock()
        mock_service.get_order.return_value = None
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/orders/ORD999')

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "订单不存在" in data["message"]

    @patch('app.routes.shipment.ShipmentService')
    def test_get_order_exception(self, mock_service_class, client):
        """测试异常情况"""
        mock_service_class.side_effect = Exception("数据库错误")

        response = client.get('/api/shipment/orders/ORD001')

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    def test_delete_order_success(self, client):
        """测试成功删除订单"""
        response = client.delete('/api/shipment/orders/ORD001')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "ORD001" in data["message"]

    def test_clear_all_orders_success(self, client):
        """测试成功清空所有订单"""
        response = client.delete('/api/shipment/orders/clear-all')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "已清空所有订单" in data["message"]

    @patch('app.routes.shipment.ShipmentService')
    def test_get_latest_orders_success(self, mock_service_class, client):
        """测试成功获取最新订单"""
        mock_service = Mock()
        mock_service.get_orders.return_value = [
            {"order_number": "ORD001"},
            {"order_number": "ORD002"}
        ]
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/orders/latest')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        mock_service.get_orders.assert_called_once_with(10)

    @patch('app.routes.shipment.ShipmentService')
    def test_get_latest_orders_exception(self, mock_service_class, client):
        """测试异常情况"""
        mock_service_class.side_effect = Exception("数据库错误")

        response = client.get('/api/shipment/orders/latest')

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False


class TestOrderSequence:
    """订单序号测试"""

    def test_set_order_sequence_success(self, client):
        """测试成功设置订单序号"""
        response = client.post(
            '/api/shipment/orders/set-sequence',
            json={"sequence": 100},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "序号已设置" in data["message"]

    def test_set_order_sequence_no_body(self, client):
        """测试无请求体"""
        response = client.post(
            '/api/shipment/orders/set-sequence',
            json={},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_reset_order_sequence_success(self, client):
        """测试成功重置订单序号"""
        response = client.post('/api/shipment/orders/reset-sequence')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "序号已重置" in data["message"]


class TestShipmentRecords:
    """出货记录测试"""

    @patch('app.routes.shipment.ShipmentService')
    def test_get_shipment_units_success(self, mock_service_class, client):
        """测试成功获取出货单位列表"""
        mock_service = Mock()
        mock_service.get_purchase_units.return_value = ["公司A", "公司B"]
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/shipment-records/units')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data

    @patch('app.routes.shipment.ShipmentService')
    def test_get_shipment_units_exception(self, mock_service_class, client):
        """测试异常情况"""
        mock_service_class.side_effect = Exception("数据库错误")

        response = client.get('/api/shipment/shipment-records/units')

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    @patch('app.routes.shipment.ShipmentService')
    def test_get_shipment_records_success(self, mock_service_class, client):
        """测试成功获取出货记录"""
        mock_service = Mock()
        mock_service.get_shipment_records.return_value = [
            {"id": 1, "unit_name": "公司A", "date": "2026-03-17"},
            {"id": 2, "unit_name": "公司B", "date": "2026-03-16"}
        ]
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/shipment-records/records')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        mock_service.get_shipment_records.assert_called_once_with(None)

    @patch('app.routes.shipment.ShipmentService')
    def test_get_shipment_records_with_unit(self, mock_service_class, client):
        """测试按单位获取出货记录"""
        mock_service = Mock()
        mock_service.get_shipment_records.return_value = []
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/shipment-records/records?unit=测试公司')

        assert response.status_code == 200
        mock_service.get_shipment_records.assert_called_once_with("测试公司")

    @patch('app.routes.shipment.ShipmentService')
    def test_get_shipment_records_exception(self, mock_service_class, client):
        """测试异常情况"""
        mock_service_class.side_effect = Exception("数据库错误")

        response = client.get('/api/shipment/shipment-records/records')

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    @patch('app.routes.shipment.ShipmentService')
    def test_update_shipment_record_success(self, mock_service_class, client):
        """测试成功更新出货记录"""
        mock_service = Mock()
        mock_service.update_shipment_record.return_value = {
            "success": True,
            "message": "出货记录已更新"
        }
        mock_service_class.return_value = mock_service
        
        response = client.patch(
            '/api/shipment/shipment-records/record',
            json={
                "id": 1,
                "unit_name": "测试公司",
                "products": [{"name": "产品 A", "quantity": 10}],
                "date": "2026-03-17"
            },
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "出货记录已更新" in data["message"]

    @patch('app.routes.shipment.ShipmentService')
    def test_update_shipment_record_partial(self, mock_service_class, client):
        """测试部分更新出货记录"""
        mock_service = Mock()
        mock_service.update_shipment_record.return_value = {
            "success": True,
            "message": "出货记录已更新"
        }
        mock_service_class.return_value = mock_service
        
        response = client.patch(
            '/api/shipment/shipment-records/record',
            json={"id": 1, "unit_name": "新公司名"},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch('app.routes.shipment.ShipmentService')
    def test_delete_shipment_record_success(self, mock_service_class, client):
        """测试成功删除出货记录"""
        mock_service = Mock()
        mock_service.delete_shipment_record.return_value = {
            "success": True,
            "message": "出货记录已删除"
        }
        mock_service_class.return_value = mock_service
        
        response = client.delete(
            '/api/shipment/shipment-records/record',
            json={"id": 1},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "出货记录已删除" in data["message"]

    def test_delete_shipment_record_missing_id(self, client):
        """测试缺少 ID"""
        response = client.delete(
            '/api/shipment/shipment-records/record',
            json={},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "缺少记录 ID" in data["message"]

    def test_export_shipment_records_success(self, client):
        """测试成功导出出货记录"""
        response = client.get('/api/shipment/shipment-records/export')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_export_shipment_records_with_unit(self, client):
        """测试按单位导出出货记录"""
        response = client.get('/api/shipment/shipment-records/export?unit=测试公司')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        # 验证返回了文件信息
        assert "file_path" in data or "filename" in data or "count" in data


class TestBusinessWorkflow:
    """业务流程集成测试"""

    @patch('app.routes.shipment.ShipmentService')
    @patch('app.routes.shipment.os.path.exists')
    def test_complete_shipment_workflow(self, mock_exists, mock_service_class, client):
        """测试完整的发货单工作流：生成 -> 打印 -> 查询"""
        mock_service = Mock()
        mock_service.generate_shipment_document.return_value = {
            "success": True,
            "doc_name": "发货单_测试公司.xlsx",
            "file_path": "/path/to/file.xlsx"
        }
        mock_service.mark_as_printed.return_value = {
            "success": True,
            "message": "打印成功"
        }
        mock_service.query_shipment_orders.return_value = {
            "success": True,
            "data": [],
            "total": 0
        }
        mock_service_class.return_value = mock_service
        mock_exists.return_value = True

        shipment_data = {
            "unit_name": "测试公司",
            "products": [{"name": "产品A", "quantity": 10, "unit": "个", "price": 100}],
            "date": "2026-03-17"
        }

        response = client.post('/api/shipment/generate', json=shipment_data)
        assert response.status_code == 200
        assert response.get_json()["success"] is True

        response = client.post('/api/shipment/print', json={"file_path": "/path/to/file.xlsx"})
        assert response.status_code == 200
        assert response.get_json()["success"] is True

        response = client.get('/api/shipment/list?unit=测试公司')
        assert response.status_code == 200
        assert response.get_json()["success"] is True

    @patch('app.routes.shipment.ShipmentService')
    def test_order_management_workflow(self, mock_service_class, client):
        """测试订单管理工作流：创建 -> 查询 -> 搜索 -> 删除"""
        mock_service = Mock()
        mock_service.get_orders.return_value = []
        mock_service.get_order.return_value = {"order_number": "ORD001"}
        mock_service.search_orders.return_value = []
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/orders')
        assert response.status_code == 200

        response = client.get('/api/shipment/orders/ORD001')
        assert response.status_code == 200

        response = client.get('/api/shipment/orders/search?q=ORD001')
        assert response.status_code == 200

        response = client.delete('/api/shipment/orders/ORD001')
        assert response.status_code == 200

    @patch('app.routes.shipment.ShipmentService')
    def test_shipment_records_workflow(self, mock_service_class, client):
        """测试出货记录工作流：获取单位 -> 获取记录 -> 更新 -> 导出"""
        mock_service = Mock()
        mock_service.get_purchase_units.return_value = ["公司 A"]
        mock_service.get_shipment_records.return_value = []
        mock_service.update_shipment_record.return_value = {
            "success": True,
            "message": "出货记录已更新"
        }
        mock_service.export_to_excel.return_value = {
            "success": True,
            "file_path": "/path/to/file.xlsx",
            "filename": "shipment_records.xlsx",
            "count": 0
        }
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/shipment-records/units')
        assert response.status_code == 200

        response = client.get('/api/shipment/shipment-records/records?unit=公司 A')
        assert response.status_code == 200

        response = client.patch(
            '/api/shipment/shipment-records/record',
            json={"id": 1, "unit_name": "公司 A"}
        )
        assert response.status_code == 200

        response = client.get('/api/shipment/shipment-records/export?unit=公司 A')
        assert response.status_code == 200


class TestEdgeCases:
    """边界条件和错误处理测试"""

    def test_invalid_json_format(self, client):
        """测试无效的JSON格式"""
        response = client.post(
            '/api/shipment/generate',
            data='invalid json',
            content_type='application/json'
        )
        assert response.status_code in [400, 500]

    def test_missing_content_type(self, client):
        """测试缺少Content-Type"""
        response = client.post(
            '/api/shipment/generate',
            data=json.dumps({"unit_name": "测试公司", "products": []})
        )
        assert response.status_code in [200, 400, 500]

    @patch('app.routes.shipment.ShipmentService')
    def test_large_pagination_values(self, mock_service_class, client):
        """测试大的分页值"""
        mock_service = Mock()
        mock_service.query_shipment_orders.return_value = {
            "success": True,
            "data": [],
            "total": 0
        }
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/list?page=9999&per_page=9999')
        assert response.status_code == 200

    @patch('app.routes.shipment.ShipmentService')
    def test_negative_pagination_values(self, mock_service_class, client):
        """测试负的分页值"""
        mock_service = Mock()
        mock_service.query_shipment_orders.side_effect = ValueError("无效的页码")
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/list?page=-1&per_page=-10')
        assert response.status_code == 500

    @patch('app.routes.shipment.ShipmentService')
    def test_special_characters_in_search(self, mock_service_class, client):
        """测试搜索中的特殊字符"""
        mock_service = Mock()
        mock_service.search_orders.return_value = []
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/orders/search?q=<script>alert("xss")</script>')
        assert response.status_code == 200

    @patch('app.routes.shipment.ShipmentService')
    def test_unicode_in_unit_name(self, mock_service_class, client):
        """测试单位名称中的Unicode字符"""
        mock_service = Mock()
        mock_service.generate_shipment_document.return_value = {
            "success": True,
            "doc_name": "发货单_测试公司.xlsx",
            "file_path": "/path/to/file.xlsx"
        }
        mock_service_class.return_value = mock_service

        response = client.post(
            '/api/shipment/generate',
            json={
                "unit_name": "测试公司中文🎉",
                "products": [{"name": "产品A", "quantity": 10, "unit": "个", "price": 100}]
            }
        )
        assert response.status_code == 200

    @patch('app.routes.shipment.ShipmentService')
    def test_empty_product_list_in_search(self, mock_service_class, client):
        """测试搜索空结果"""
        mock_service = Mock()
        mock_service.search_orders.return_value = []
        mock_service_class.return_value = mock_service

        response = client.get('/api/shipment/orders/search?q=')
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 0

    @patch('app.routes.shipment.ShipmentService')
    def test_very_long_search_query(self, mock_service_class, client):
        """测试超长搜索查询"""
        mock_service = Mock()
        mock_service.search_orders.return_value = []
        mock_service_class.return_value = mock_service

        long_query = "a" * 1000
        response = client.get(f'/api/shipment/orders/search?q={long_query}')
        assert response.status_code == 200
