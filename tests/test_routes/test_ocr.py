"""
OCR路由测试
"""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, MagicMock, patch
from io import BytesIO


class TestOCRRecognize:
    """文字识别测试"""

    def test_recognize_test(self, client):
        """测试 OCR 服务健康检查接口"""
        response = client.get('/api/ocr/test')
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert 'message' in data

    @patch('app.routes.ocr.get_ocr_service')
    def test_recognize_with_file_path_success(self, mock_get_service, client):
        """测试通过文件路径识别 - 成功"""
        mock_service = MagicMock()
        mock_service.recognize_file.return_value = {
            "success": True,
            "message": "识别成功",
            "text": "测试文本内容"
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/recognize',
            data={"file_path": "/path/to/test.jpg"},
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert 'text' in data

    @patch('app.routes.ocr.get_ocr_service')
    def test_recognize_with_file_path_failure(self, mock_get_service, client):
        """测试通过文件路径识别 - 失败"""
        mock_service = MagicMock()
        mock_service.recognize_file.return_value = {
            "success": False,
            "message": "文件不存在"
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/recognize',
            data={"file_path": "/nonexistent/path.jpg"},
            content_type='multipart/form-data'
        )
        assert response.status_code == 400

    @patch('app.routes.ocr.get_ocr_service')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_recognize_with_file_upload_success(self, mock_exists, mock_makedirs, mock_open, mock_get_service, client):
        """测试通过文件上传识别 - 成功"""
        mock_exists.return_value = True
        mock_service = MagicMock()
        mock_service.recognize_file.return_value = {
            "success": True,
            "message": "识别成功",
            "text": "上传文件的文本内容"
        }
        mock_get_service.return_value = mock_service

        data = {
            'image': (BytesIO(b'fake image data'), 'test.jpg')
        }
        response = client.post(
            '/api/ocr/recognize',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True

    def test_recognize_missing_file(self, client):
        """测试识别 - 缺少文件"""
        response = client.post(
            '/api/ocr/recognize',
            data={},
            content_type='multipart/form-data'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get('success') is False
        assert 'message' in data

    @patch('app.routes.ocr.get_ocr_service')
    def test_recognize_service_exception(self, mock_get_service, client):
        """测试识别 - 服务异常"""
        mock_service = MagicMock()
        mock_service.recognize_file.side_effect = Exception("OCR服务异常")
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/recognize',
            data={"file_path": "/path/to/test.jpg"},
            content_type='multipart/form-data'
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data.get('success') is False

    @patch('app.routes.ocr.get_ocr_service')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_recognize_with_different_extensions(self, mock_exists, mock_makedirs, mock_open, mock_get_service, client):
        """测试识别 - 不同文件扩展名"""
        mock_exists.return_value = True
        mock_service = MagicMock()
        mock_service.recognize_file.return_value = {
            "success": True,
            "message": "识别成功",
            "text": "测试文本"
        }
        mock_get_service.return_value = mock_service

        extensions = ['png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp']
        for ext in extensions:
            data = {
                'image': (BytesIO(b'fake image data'), f'test.{ext}')
            }
            response = client.post(
                '/api/ocr/recognize',
                data=data,
                content_type='multipart/form-data'
            )
            assert response.status_code == 200

    @patch('app.routes.ocr.get_ocr_service')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_recognize_with_special_filename(self, mock_exists, mock_makedirs, mock_open, mock_get_service, client):
        """测试识别 - 特殊文件名"""
        mock_exists.return_value = True
        mock_service = MagicMock()
        mock_service.recognize_file.return_value = {
            "success": True,
            "message": "识别成功",
            "text": "测试文本"
        }
        mock_get_service.return_value = mock_service

        data = {
            'image': (BytesIO(b'fake image data'), '测试文件_2026-03-17.jpg')
        }
        response = client.post(
            '/api/ocr/recognize',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True

    @patch('app.routes.ocr.get_ocr_service')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_recognize_with_empty_file(self, mock_exists, mock_makedirs, mock_open, mock_get_service, client):
        """测试识别 - 空文件"""
        mock_exists.return_value = True
        mock_service = MagicMock()
        mock_service.recognize_file.return_value = {
            "success": False,
            "message": "文件为空"
        }
        mock_get_service.return_value = mock_service

        data = {
            'image': (BytesIO(b''), 'test.jpg')
        }
        response = client.post(
            '/api/ocr/recognize',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400

    @patch('app.routes.ocr.get_ocr_service')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_recognize_with_large_file(self, mock_exists, mock_makedirs, mock_open, mock_get_service, client):
        """测试识别 - 大文件"""
        mock_exists.return_value = True
        mock_service = MagicMock()
        mock_service.recognize_file.return_value = {
            "success": True,
            "message": "识别成功",
            "text": "测试文本"
        }
        mock_get_service.return_value = mock_service

        large_data = b'x' * (10 * 1024 * 1024)
        data = {
            'image': (BytesIO(large_data), 'large.jpg')
        }
        response = client.post(
            '/api/ocr/recognize',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200

    @patch('app.routes.ocr.get_ocr_service')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_recognize_with_unicode_filename(self, mock_exists, mock_makedirs, mock_open, mock_get_service, client):
        """测试识别 - Unicode文件名"""
        mock_exists.return_value = True
        mock_service = MagicMock()
        mock_service.recognize_file.return_value = {
            "success": True,
            "message": "识别成功",
            "text": "测试文本"
        }
        mock_get_service.return_value = mock_service

        data = {
            'image': (BytesIO(b'fake image data'), '文件名🎉.jpg')
        }
        response = client.post(
            '/api/ocr/recognize',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200


class TestOCRExtract:
    """结构化提取测试"""

    @patch('app.routes.ocr.get_ocr_service')
    def test_extract_success(self, mock_get_service, client):
        """测试结构化提取 - 成功"""
        mock_service = MagicMock()
        mock_service.extract_structured_data.return_value = {
            "purchase_unit": "测试公司",
            "contact_person": "张三",
            "contact_phone": "13800138000",
            "purchase_date": "2026-03-17",
            "order_number": "ORD001",
            "total_amount": 1000.00,
            "products": [
                {"model": "A01", "name": "产品A", "quantity": 10, "unit_price": 100, "total_price": 1000}
            ]
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/extract',
            json={"text": "购货单位：测试公司\n联系人：张三\n联系电话：13800138000"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert 'data' in data

    def test_extract_empty_text(self, client):
        """测试结构化提取 - 空文本"""
        response = client.post(
            '/api/ocr/extract',
            json={"text": ""},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_extract_missing_text(self, client):
        """测试结构化提取 - 缺少文本参数"""
        response = client.post(
            '/api/ocr/extract',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get('success') is False

    @patch('app.routes.ocr.get_ocr_service')
    def test_extract_service_exception(self, mock_get_service, client):
        """测试结构化提取 - 服务异常"""
        mock_service = MagicMock()
        mock_service.extract_structured_data.side_effect = Exception("提取服务异常")
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/extract',
            json={"text": "测试文本"},
            content_type='application/json'
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data.get('success') is False

    @patch('app.routes.ocr.get_ocr_service')
    def test_extract_with_partial_data(self, mock_get_service, client):
        """测试结构化提取 - 部分数据"""
        mock_service = MagicMock()
        mock_service.extract_structured_data.return_value = {
            "purchase_unit": "测试公司",
            "contact_person": None,
            "contact_phone": None,
            "purchase_date": None,
            "order_number": None,
            "total_amount": None,
            "products": []
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/extract',
            json={"text": "购货单位：测试公司"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert data.get('data', {}).get('purchase_unit') == "测试公司"

    @patch('app.routes.ocr.get_ocr_service')
    def test_extract_with_multiple_products(self, mock_get_service, client):
        """测试结构化提取 - 多个产品"""
        mock_service = MagicMock()
        mock_service.extract_structured_data.return_value = {
            "purchase_unit": "测试公司",
            "contact_person": "张三",
            "contact_phone": "13800138000",
            "purchase_date": "2026-03-17",
            "order_number": "ORD001",
            "total_amount": 3000.00,
            "products": [
                {"model": "A01", "name": "产品A", "quantity": 10, "unit_price": 100, "total_price": 1000},
                {"model": "B02", "name": "产品B", "quantity": 5, "unit_price": 200, "total_price": 1000},
                {"model": "C03", "name": "产品C", "quantity": 20, "unit_price": 50, "total_price": 1000}
            ]
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/extract',
            json={"text": "购货单位：测试公司\n联系人：张三\n产品A x10\n产品B x5\n产品C x20"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert len(data.get('data', {}).get('products', [])) == 3

    @patch('app.routes.ocr.get_ocr_service')
    def test_extract_with_special_characters(self, mock_get_service, client):
        """测试结构化提取 - 特殊字符"""
        mock_service = MagicMock()
        mock_service.extract_structured_data.return_value = {
            "purchase_unit": "测试公司（有限公司）",
            "contact_person": "张三",
            "contact_phone": "138-0013-8000",
            "purchase_date": "2026/03/17",
            "order_number": "ORD-001",
            "total_amount": 1000.00,
            "products": []
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/extract',
            json={"text": "购货单位：测试公司（有限公司）\n联系人：张三\n电话：138-0013-8000"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True

    @patch('app.routes.ocr.get_ocr_service')
    def test_extract_with_long_text(self, mock_get_service, client):
        """测试结构化提取 - 长文本"""
        mock_service = MagicMock()
        mock_service.extract_structured_data.return_value = {
            "purchase_unit": "测试公司",
            "contact_person": "张三",
            "contact_phone": "13800138000",
            "purchase_date": "2026-03-17",
            "order_number": "ORD001",
            "total_amount": 1000.00,
            "products": []
        }
        mock_get_service.return_value = mock_service

        long_text = "购货单位：测试公司\n联系人：张三\n联系电话：13800138000\n" + "备注信息\n" * 100
        response = client.post(
            '/api/ocr/extract',
            json={"text": long_text},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True


class TestOCRAnalyze:
    """文本分析测试"""

    @patch('app.routes.ocr.get_ocr_service')
    def test_analyze_success(self, mock_get_service, client):
        """测试文本分析 - 成功"""
        mock_service = MagicMock()
        mock_service.analyze_text.return_value = {
            "text_type": "order",
            "confidence": 0.8,
            "detected_fields": {
                "purchase_unit": "测试公司",
                "contact_person": "张三",
                "date": "2026-03-17"
            },
            "missing_fields": [],
            "suggestions": []
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/analyze',
            json={"text": "购货单位：测试公司\n联系人：张三\n订单编号：ORD001"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert 'data' in data

    def test_analyze_empty_text(self, client):
        """测试文本分析 - 空文本"""
        response = client.post(
            '/api/ocr/analyze',
            json={"text": ""},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_analyze_missing_text(self, client):
        """测试文本分析 - 缺少文本参数"""
        response = client.post(
            '/api/ocr/analyze',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 400

    @patch('app.routes.ocr.get_ocr_service')
    def test_analyze_unknown_type(self, mock_get_service, client):
        """测试文本分析 - 未知类型"""
        mock_service = MagicMock()
        mock_service.analyze_text.return_value = {
            "text_type": "unknown",
            "confidence": 0.0,
            "detected_fields": {},
            "missing_fields": ["purchase_unit", "contact_person"],
            "suggestions": ["文本类型不明确，请手动确认"]
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/analyze',
            json={"text": "一些随机文本内容"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('data', {}).get('text_type') == 'unknown'

    @patch('app.routes.ocr.get_ocr_service')
    def test_analyze_service_exception(self, mock_get_service, client):
        """测试文本分析 - 服务异常"""
        mock_service = MagicMock()
        mock_service.analyze_text.side_effect = Exception("分析服务异常")
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/analyze',
            json={"text": "测试文本"},
            content_type='application/json'
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data.get('success') is False

    @patch('app.routes.ocr.get_ocr_service')
    def test_analyze_invoice_type(self, mock_get_service, client):
        """测试文本分析 - 发票类型"""
        mock_service = MagicMock()
        mock_service.analyze_text.return_value = {
            "text_type": "invoice",
            "confidence": 0.9,
            "detected_fields": {
                "invoice_number": "INV001",
                "amount": 1000.00,
                "date": "2026-03-17"
            },
            "missing_fields": [],
            "suggestions": []
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/analyze',
            json={"text": "发票号码：INV001\n金额：1000.00"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('data', {}).get('text_type') == 'invoice'
        assert data.get('data', {}).get('confidence') == 0.9

    @patch('app.routes.ocr.get_ocr_service')
    def test_analyze_with_missing_fields(self, mock_get_service, client):
        """测试文本分析 - 缺失字段"""
        mock_service = MagicMock()
        mock_service.analyze_text.return_value = {
            "text_type": "order",
            "confidence": 0.6,
            "detected_fields": {
                "purchase_unit": "测试公司"
            },
            "missing_fields": ["contact_person", "contact_phone", "order_number"],
            "suggestions": ["请补充联系人信息", "请补充订单编号"]
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/analyze',
            json={"text": "购货单位：测试公司"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data.get('data', {}).get('missing_fields', [])) > 0
        assert len(data.get('data', {}).get('suggestions', [])) > 0

    @patch('app.routes.ocr.get_ocr_service')
    def test_analyze_long_text(self, mock_get_service, client):
        """测试文本分析 - 长文本"""
        mock_service = MagicMock()
        mock_service.analyze_text.return_value = {
            "text_type": "order",
            "confidence": 0.85,
            "detected_fields": {
                "purchase_unit": "测试公司",
                "contact_person": "张三",
                "contact_phone": "13800138000"
            },
            "missing_fields": [],
            "suggestions": []
        }
        mock_get_service.return_value = mock_service

        long_text = "购货单位：测试公司\n联系人：张三\n联系电话：13800138000\n" + "测试内容\n" * 100
        response = client.post(
            '/api/ocr/analyze',
            json={"text": long_text},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True

    @patch('app.routes.ocr.get_ocr_service')
    def test_analyze_special_characters(self, mock_get_service, client):
        """测试文本分析 - 特殊字符"""
        mock_service = MagicMock()
        mock_service.analyze_text.return_value = {
            "text_type": "order",
            "confidence": 0.7,
            "detected_fields": {},
            "missing_fields": [],
            "suggestions": []
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/analyze',
            json={"text": "测试文本！@#￥%……&*（）——+【】{}；：""'，。、？"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True

    @patch('app.routes.ocr.get_ocr_service')
    def test_analyze_whitespace_only(self, mock_get_service, client):
        """测试文本分析 - 只有空白字符"""
        mock_service = MagicMock()
        mock_service.analyze_text.return_value = {
            "text_type": "unknown",
            "confidence": 0.0,
            "detected_fields": {},
            "missing_fields": [],
            "suggestions": []
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/analyze',
            json={"text": "   \n\t  \n  "},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True


class TestOCRRecognizeAndExtract:
    """一站式识别提取测试"""

    @patch('app.routes.ocr.get_ocr_service')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_recognize_and_extract_success(self, mock_exists, mock_makedirs, mock_open, mock_get_service, client):
        """测试一站式识别提取 - 成功"""
        mock_exists.return_value = True
        mock_service = MagicMock()
        mock_service.recognize_file.return_value = {
            "success": True,
            "message": "识别成功",
            "text": "购货单位：测试公司\n联系人：张三"
        }
        mock_service.extract_structured_data.return_value = {
            "purchase_unit": "测试公司",
            "contact_person": "张三",
            "contact_phone": None
        }
        mock_service.analyze_text.return_value = {
            "text_type": "order",
            "confidence": 0.7,
            "detected_fields": {}
        }
        mock_get_service.return_value = mock_service

        data = {
            'image': (BytesIO(b'fake image data'), 'test.jpg')
        }
        response = client.post(
            '/api/ocr/recognize-and-extract',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert 'text' in data
        assert 'data' in data

    @patch('app.routes.ocr.get_ocr_service')
    def test_recognize_and_extract_recognize_failure(self, mock_get_service, client):
        """测试一站式识别提取 - 识别失败"""
        mock_service = MagicMock()
        mock_service.recognize_file.return_value = {
            "success": False,
            "message": "识别失败"
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/recognize-and-extract',
            data={"file_path": "/path/to/test.jpg"},
            content_type='multipart/form-data'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get('success') is False

    def test_recognize_and_extract_missing_file(self, client):
        """测试一站式识别提取 - 缺少文件"""
        response = client.post(
            '/api/ocr/recognize-and-extract',
            data={},
            content_type='multipart/form-data'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get('success') is False

    @patch('app.routes.ocr.get_ocr_service')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_recognize_and_extract_exception(self, mock_exists, mock_makedirs, mock_get_service, client):
        """测试一站式识别提取 - 服务异常"""
        mock_exists.return_value = False
        mock_service = MagicMock()
        mock_service.recognize_file.side_effect = Exception("OCR服务异常")
        mock_get_service.return_value = mock_service

        data = {
            'image': (BytesIO(b'fake image data'), 'test.jpg')
        }
        response = client.post(
            '/api/ocr/recognize-and-extract',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data.get('success') is False

    @patch('app.routes.ocr.get_ocr_service')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_recognize_and_extract_with_file_path(self, mock_exists, mock_makedirs, mock_open, mock_get_service, client):
        """测试一站式识别提取 - 使用文件路径"""
        mock_service = MagicMock()
        mock_service.recognize_file.return_value = {
            "success": True,
            "message": "识别成功",
            "text": "购货单位：测试公司\n联系人：张三"
        }
        mock_service.extract_structured_data.return_value = {
            "purchase_unit": "测试公司",
            "contact_person": "张三"
        }
        mock_service.analyze_text.return_value = {
            "text_type": "order",
            "confidence": 0.8,
            "detected_fields": {}
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            '/api/ocr/recognize-and-extract',
            data={"file_path": "/path/to/test.jpg"},
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert 'text' in data
        assert 'data' in data
        assert 'analysis' in data

    @patch('app.routes.ocr.get_ocr_service')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_recognize_and_extract_extract_failure(self, mock_exists, mock_makedirs, mock_open, mock_get_service, client):
        """测试一站式识别提取 - 提取失败但仍返回结果"""
        mock_exists.return_value = True
        mock_service = MagicMock()
        mock_service.recognize_file.return_value = {
            "success": True,
            "message": "识别成功",
            "text": "购货单位：测试公司\n联系人：张三"
        }
        mock_service.extract_structured_data.side_effect = Exception("提取失败")
        mock_service.analyze_text.return_value = {
            "text_type": "unknown",
            "confidence": 0.0,
            "detected_fields": {}
        }
        mock_get_service.return_value = mock_service

        data = {
            'image': (BytesIO(b'fake image data'), 'test.jpg')
        }
        response = client.post(
            '/api/ocr/recognize-and-extract',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data.get('success') is False

    @patch('app.routes.ocr.get_ocr_service')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_recognize_and_extract_analyze_failure(self, mock_exists, mock_makedirs, mock_open, mock_get_service, client):
        """测试一站式识别提取 - 分析失败但仍返回结果"""
        mock_exists.return_value = True
        mock_service = MagicMock()
        mock_service.recognize_file.return_value = {
            "success": True,
            "message": "识别成功",
            "text": "购货单位：测试公司\n联系人：张三"
        }
        mock_service.extract_structured_data.return_value = {
            "purchase_unit": "测试公司",
            "contact_person": "张三"
        }
        mock_service.analyze_text.side_effect = Exception("分析失败")
        mock_get_service.return_value = mock_service

        data = {
            'image': (BytesIO(b'fake image data'), 'test.jpg')
        }
        response = client.post(
            '/api/ocr/recognize-and-extract',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data.get('success') is False


class TestOCRAllowedFile:
    """文件类型验证测试"""

    def test_allowed_file_valid_extensions(self, client):
        """测试允许的文件扩展名"""
        from app.routes.ocr import allowed_file

        assert allowed_file("test.png") is True
        assert allowed_file("test.jpg") is True
        assert allowed_file("test.jpeg") is True
        assert allowed_file("test.bmp") is True
        assert allowed_file("test.tiff") is True
        assert allowed_file("test.webp") is True

    def test_allowed_file_invalid_extensions(self, client):
        """测试不允许的文件扩展名"""
        from app.routes.ocr import allowed_file

        assert allowed_file("test.txt") is False
        assert allowed_file("test.pdf") is False
        assert allowed_file("test.doc") is False
        assert allowed_file("test") is False
        assert allowed_file("test.") is False

    def test_allowed_file_case_insensitive(self, client):
        """测试文件扩展名大小写不敏感"""
        from app.routes.ocr import allowed_file

        assert allowed_file("test.PNG") is True
        assert allowed_file("test.JPG") is True
        assert allowed_file("test.Jpeg") is True
        assert allowed_file("test.BMP") is True
        assert allowed_file("test.TIFF") is True
        assert allowed_file("test.WebP") is True

    def test_allowed_file_with_path(self, client):
        """测试带路径的文件名"""
        from app.routes.ocr import allowed_file

        assert allowed_file("/path/to/test.jpg") is True
        assert allowed_file("C:\\Users\\test.png") is True
        assert allowed_file("./uploads/test.jpeg") is True

    def test_allowed_file_with_dots_in_name(self, client):
        """测试文件名中包含多个点"""
        from app.routes.ocr import allowed_file

        assert allowed_file("test.file.jpg") is True
        assert allowed_file("my.photo.png") is True
        assert allowed_file("image..jpg") is True

    def test_allowed_file_with_special_chars(self, client):
        """测试包含特殊字符的文件名"""
        from app.routes.ocr import allowed_file

        assert allowed_file("测试文件.jpg") is True
        assert allowed_file("file-name.jpg") is True
        assert allowed_file("file_name.jpg") is True
        assert allowed_file("file.name.jpg") is True

    def test_allowed_file_empty_filename(self, client):
        """测试空文件名"""
        from app.routes.ocr import allowed_file

        assert allowed_file("") is False

    def test_allowed_file_none_filename(self, client):
        """测试None文件名"""
        from app.routes.ocr import allowed_file

        try:
            result = allowed_file(None)
            assert False, "Expected TypeError for None filename"
        except TypeError:
            pass

    def test_allowed_file_only_extension(self, client):
        """测试只有扩展名的文件"""
        from app.routes.ocr import allowed_file

        assert allowed_file(".jpg") is True
        assert allowed_file(".png") is True

    def test_allowed_file_with_spaces(self, client):
        """测试包含空格的文件名"""
        from app.routes.ocr import allowed_file

        assert allowed_file("test file.jpg") is True
        assert allowed_file("  test.jpg  ") is False

    def test_allowed_file_multiple_extensions(self, client):
        """测试多个扩展名的情况"""
        from app.routes.ocr import allowed_file

        assert allowed_file("test.jpg.png") is True
        assert allowed_file("test.tar.gz") is False
