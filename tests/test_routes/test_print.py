"""
打印管理路由测试
"""

import pytest
import json
from unittest.mock import MagicMock, patch


class TestPrintRoutes:
    """打印管理路由测试"""

    def test_get_printers_success(self, client):
        """测试获取打印机列表成功"""
        mock_printer_service = MagicMock()
        mock_printer_service.get_printers.return_value = {
            "success": True,
            "printers": ["打印机1", "打印机2"],
            "count": 2
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.get('/api/print/printers')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["printers"]) == 2

    def test_get_printers_failure(self, client):
        """测试获取打印机列表失败"""
        mock_printer_service = MagicMock()
        mock_printer_service.get_printers.side_effect = Exception("获取失败")

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.get('/api/print/printers')

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    def test_get_default_printer_success(self, client):
        """测试获取默认打印机成功"""
        mock_printer_service = MagicMock()
        mock_printer_service.get_default_printer.return_value = {
            "success": True,
            "printer": "默认打印机"
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.get('/api/print/default')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["printer"] == "默认打印机"

    def test_get_default_printer_not_found(self, client):
        """测试未找到默认打印机"""
        mock_printer_service = MagicMock()
        mock_printer_service.get_default_printer.return_value = {
            "success": False,
            "message": "未找到默认打印机"
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.get('/api/print/default')

        assert response.status_code == 200

    def test_print_document_success(self, client):
        """测试打印文档成功"""
        mock_printer_service = MagicMock()
        mock_printer_service.print_document.return_value = {
            "success": True,
            "message": "打印成功",
            "printer": "打印机1"
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service), \
             patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/document',
                json={"file_path": "test.pdf"},
                content_type='application/json'
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_printer_service.print_document.assert_called_once()

    def test_print_document_with_printer(self, client):
        """测试打印文档指定打印机"""
        mock_printer_service = MagicMock()
        mock_printer_service.print_document.return_value = {
            "success": True,
            "message": "打印成功",
            "printer": "指定打印机"
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service), \
             patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/document',
                json={"file_path": "test.pdf", "printer_name": "指定打印机"},
                content_type='application/json'
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_printer_service.print_document.assert_called_once_with("test.pdf", "指定打印机", False)

    def test_print_document_with_automation(self, client):
        """测试打印文档使用自动化"""
        mock_printer_service = MagicMock()
        mock_printer_service.print_document.return_value = {
            "success": True,
            "message": "打印成功",
            "printer": "打印机1"
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service), \
             patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/document',
                json={"file_path": "test.pdf", "use_automation": True},
                content_type='application/json'
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_printer_service.print_document.assert_called_once_with("test.pdf", None, True)

    def test_print_document_exception(self, client):
        """测试打印文档异常处理"""
        mock_printer_service = MagicMock()
        mock_printer_service.print_document.side_effect = Exception("打印服务异常")

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service), \
             patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/document',
                json={"file_path": "test.pdf"},
                content_type='application/json'
            )

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "打印失败" in data["message"]

    def test_print_document_non_json(self, client):
        """测试打印文档非JSON请求"""
        with patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/document',
                data="not json",
                content_type='text/plain'
            )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "文件路径不能为空" in data["message"]

    def test_print_document_missing_file_path(self, client):
        """测试打印文档缺少文件路径"""
        response = client.post(
            '/api/print/document',
            json={},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "文件路径不能为空" in data["message"]

    def test_print_document_file_not_exists(self, client):
        """测试打印文档文件不存在"""
        with patch('os.path.exists', return_value=False):
            response = client.post(
                '/api/print/document',
                json={"file_path": "nonexistent.pdf"},
                content_type='application/json'
            )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "文件不存在" in data["message"]

    def test_print_document_failure(self, client):
        """测试打印文档失败"""
        mock_printer_service = MagicMock()
        mock_printer_service.print_document.return_value = {
            "success": False,
            "message": "打印失败"
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service), \
             patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/document',
                json={"file_path": "test.pdf"},
                content_type='application/json'
            )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_print_label_success(self, client):
        """测试打印标签成功"""
        mock_printer_service = MagicMock()
        mock_printer_service.print_label.return_value = {
            "success": True,
            "message": "标签打印完成: 1/1 成功",
            "printer": "标签打印机",
            "copies": 1
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service), \
             patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/label',
                json={"file_path": "label.pdf", "copies": 1},
                content_type='application/json'
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_print_label_with_printer(self, client):
        """测试打印标签指定打印机"""
        mock_printer_service = MagicMock()
        mock_printer_service.print_label.return_value = {
            "success": True,
            "message": "标签打印完成: 5/5 成功",
            "printer": "指定标签打印机",
            "copies": 5
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service), \
             patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/label',
                json={"file_path": "label.pdf", "printer_name": "指定标签打印机", "copies": 5},
                content_type='application/json'
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["copies"] == 5
        mock_printer_service.print_label.assert_called_once_with("label.pdf", "指定标签打印机", 5)

    def test_print_label_file_not_exists(self, client):
        """测试打印标签文件不存在"""
        with patch('os.path.exists', return_value=False):
            response = client.post(
                '/api/print/label',
                json={"file_path": "nonexistent.pdf", "copies": 1},
                content_type='application/json'
            )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "文件不存在" in data["message"]

    def test_print_label_failure(self, client):
        """测试打印标签失败"""
        mock_printer_service = MagicMock()
        mock_printer_service.print_label.return_value = {
            "success": False,
            "message": "打印失败"
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service), \
             patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/label',
                json={"file_path": "label.pdf", "copies": 1},
                content_type='application/json'
            )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_print_label_exception(self, client):
        """测试打印标签异常处理"""
        mock_printer_service = MagicMock()
        mock_printer_service.print_label.side_effect = Exception("打印服务异常")

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service), \
             patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/label',
                json={"file_path": "label.pdf", "copies": 1},
                content_type='application/json'
            )

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "打印标签失败" in data["message"]

    def test_print_label_non_json(self, client):
        """测试打印标签非JSON请求"""
        with patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/label',
                data="not json",
                content_type='text/plain'
            )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "文件路径不能为空" in data["message"]

    def test_print_label_copies_boundary_min(self, client):
        """测试打印标签份数边界值-最小值"""
        mock_printer_service = MagicMock()
        mock_printer_service.print_label.return_value = {
            "success": True,
            "message": "标签打印完成: 1/1 成功",
            "copies": 1
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service), \
             patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/label',
                json={"file_path": "label.pdf", "copies": 1},
                content_type='application/json'
            )

        assert response.status_code == 200

    def test_print_label_copies_boundary_max(self, client):
        """测试打印标签份数边界值-最大值"""
        mock_printer_service = MagicMock()
        mock_printer_service.print_label.return_value = {
            "success": True,
            "message": "标签打印完成: 100/100 成功",
            "copies": 100
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service), \
             patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/label',
                json={"file_path": "label.pdf", "copies": 100},
                content_type='application/json'
            )

        assert response.status_code == 200

    def test_print_label_copies_negative(self, client):
        """测试打印标签份数为负数"""
        with patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/label',
                json={"file_path": "label.pdf", "copies": -1},
                content_type='application/json'
            )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "打印份数必须在1-100之间" in data["message"]

    def test_print_label_missing_file_path(self, client):
        """测试打印标签缺少文件路径"""
        response = client.post(
            '/api/print/label',
            json={},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "文件路径不能为空" in data["message"]

    def test_print_label_invalid_copies(self, client):
        """测试打印标签份数无效"""
        with patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/label',
                json={"file_path": "label.pdf", "copies": 0},
                content_type='application/json'
            )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "打印份数必须在1-100之间" in data["message"]

    def test_print_label_copies_too_large(self, client):
        """测试打印标签份数超出限制"""
        response = client.post(
            '/api/print/label',
            json={"file_path": "label.pdf", "copies": 101},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_test_printer_success(self, client):
        """测试打印机成功"""
        mock_printer_service = MagicMock()
        mock_printer_service.test_printer.return_value = {
            "success": True,
            "available": True,
            "printer": "打印机1",
            "status": "就绪"
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.post(
                '/api/print/test',
                json={"printer_name": "打印机1"},
                content_type='application/json'
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["available"] is True

    def test_test_printer_not_available(self, client):
        """测试打印机不可用"""
        mock_printer_service = MagicMock()
        mock_printer_service.test_printer.return_value = {
            "success": False,
            "available": False,
            "printer": "打印机1",
            "status": "离线"
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.post(
                '/api/print/test',
                json={"printer_name": "打印机1"},
                content_type='application/json'
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert data["available"] is False

    def test_test_printer_exception(self, client):
        """测试打印机异常处理"""
        mock_printer_service = MagicMock()
        mock_printer_service.test_printer.side_effect = Exception("打印机服务异常")

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.post(
                '/api/print/test',
                json={"printer_name": "打印机1"},
                content_type='application/json'
            )

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "打印机服务异常" in data["message"]

    def test_test_printer_non_json(self, client):
        """测试打印机非JSON请求"""
        response = client.post(
            '/api/print/test',
            data="not json",
            content_type='text/plain'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "打印机名称不能为空" in data["message"]

    def test_test_printer_missing_name(self, client):
        """测试打印机缺少名称"""
        response = client.post(
            '/api/print/test',
            json={},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "打印机名称不能为空" in data["message"]

    def test_validate_printer_separation_valid(self, client):
        """测试验证打印机分离成功"""
        mock_printer_service = MagicMock()
        mock_printer_service.validate_printer_separation.return_value = {
            "valid": True,
            "doc_printer": "发货单打印机",
            "label_printer": "标签打印机"
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.get('/api/print/validate')

        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is True
        assert data["success"] is True

    def test_validate_printer_separation_invalid(self, client):
        """测试验证打印机分离无效"""
        mock_printer_service = MagicMock()
        mock_printer_service.validate_printer_separation.return_value = {
            "valid": False,
            "error": "发货单打印机和标签打印机相同",
            "doc_printer": "同一打印机",
            "label_printer": "同一打印机"
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.get('/api/print/validate')

        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is False
        assert data["success"] is True

    def test_validate_printer_separation_exception(self, client):
        """测试验证打印机分离异常处理"""
        mock_printer_service = MagicMock()
        mock_printer_service.validate_printer_separation.side_effect = Exception("验证服务异常")

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.get('/api/print/validate')

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert data["valid"] is False
        assert "验证服务异常" in data["error"]

    def test_get_document_printer_success(self, client):
        """测试获取发货单打印机成功"""
        mock_printer_service = MagicMock()
        mock_printer_service.get_document_printer.return_value = "发货单打印机"

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.get('/api/print/document-printer')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["printer"] == "发货单打印机"

    def test_get_document_printer_not_found(self, client):
        """测试获取发货单打印机未找到"""
        mock_printer_service = MagicMock()
        mock_printer_service.get_document_printer.return_value = None

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.get('/api/print/document-printer')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "未找到发货单打印机" in data["message"]

    def test_get_label_printer_success(self, client):
        """测试获取标签打印机成功"""
        mock_printer_service = MagicMock()
        mock_printer_service.get_label_printer.return_value = "标签打印机"

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.get('/api/print/label-printer')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["printer"] == "标签打印机"

    def test_get_label_printer_not_found(self, client):
        """测试获取标签打印机未找到"""
        mock_printer_service = MagicMock()
        mock_printer_service.get_label_printer.return_value = None

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.get('/api/print/label-printer')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "未找到标签打印机" in data["message"]

    def test_test_endpoint(self, client):
        """测试打印服务测试接口"""
        response = client.get('/api/print/test')

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "打印服务运行正常" in data["message"]

    def test_get_printers_exception(self, client):
        """测试获取打印机列表异常处理"""
        mock_printer_service = MagicMock()
        mock_printer_service.get_printers.side_effect = Exception("打印机服务异常")

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.get('/api/print/printers')

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "获取打印机列表失败" in data["message"]

    def test_get_default_printer_exception(self, client):
        """测试获取默认打印机异常处理"""
        mock_printer_service = MagicMock()
        mock_printer_service.get_default_printer.side_effect = Exception("默认打印机服务异常")

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.get('/api/print/default')

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "默认打印机服务异常" in data["message"]

    def test_get_document_printer_exception(self, client):
        """测试获取发货单打印机异常处理"""
        mock_printer_service = MagicMock()
        mock_printer_service.get_document_printer.side_effect = Exception("发货单打印机服务异常")

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.get('/api/print/document-printer')

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "发货单打印机服务异常" in data["message"]

    def test_get_label_printer_exception(self, client):
        """测试获取标签打印机异常处理"""
        mock_printer_service = MagicMock()
        mock_printer_service.get_label_printer.side_effect = Exception("标签打印机服务异常")

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service):
            response = client.get('/api/print/label-printer')

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "标签打印机服务异常" in data["message"]

    def test_print_document_empty_file_path(self, client):
        """测试打印文档空文件路径"""
        response = client.post(
            '/api/print/document',
            json={"file_path": ""},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "文件路径不能为空" in data["message"]

    def test_print_label_empty_file_path(self, client):
        """测试打印标签空文件路径"""
        response = client.post(
            '/api/print/label',
            json={"file_path": ""},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "文件路径不能为空" in data["message"]

    def test_test_printer_empty_name(self, client):
        """测试打印机空名称"""
        response = client.post(
            '/api/print/test',
            json={"printer_name": ""},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "打印机名称不能为空" in data["message"]

    def test_print_document_with_all_parameters(self, client):
        """测试打印文档包含所有参数"""
        mock_printer_service = MagicMock()
        mock_printer_service.print_document.return_value = {
            "success": True,
            "message": "打印成功",
            "printer": "指定打印机"
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service), \
             patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/document',
                json={
                    "file_path": "test.pdf",
                    "printer_name": "指定打印机",
                    "use_automation": True
                },
                content_type='application/json'
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_printer_service.print_document.assert_called_once_with("test.pdf", "指定打印机", True)

    def test_print_label_with_all_parameters(self, client):
        """测试打印标签包含所有参数"""
        mock_printer_service = MagicMock()
        mock_printer_service.print_label.return_value = {
            "success": True,
            "message": "标签打印完成: 10/10 成功",
            "printer": "指定标签打印机",
            "copies": 10
        }

        with patch('app.routes.print.get_printer_service', return_value=mock_printer_service), \
             patch('os.path.exists', return_value=True):
            response = client.post(
                '/api/print/label',
                json={
                    "file_path": "label.pdf",
                    "printer_name": "指定标签打印机",
                    "copies": 10
                },
                content_type='application/json'
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["copies"] == 10
        mock_printer_service.print_label.assert_called_once_with("label.pdf", "指定标签打印机", 10)
