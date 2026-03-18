"""
Excel 提取与生成路由测试
"""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, MagicMock, patch
from io import BytesIO


class TestExcelExtractHelpers:
    """Excel 提取与生成辅助函数测试"""

    def test_get_base_dir(self):
        """测试 get_base_dir 函数"""
        from app.routes.excel_extract import get_base_dir

        base_dir = get_base_dir()
        assert base_dir is not None
        assert os.path.isdir(base_dir)

    @patch('openpyxl.load_workbook')
    @patch('app.routes.excel_extract.os.path.exists')
    def test_extract_from_excel_file_not_exists(self, mock_exists, mock_load_workbook):
        """测试 _extract_from_excel - 文件不存在"""
        from app.routes.excel_extract import _extract_from_excel

        mock_exists.return_value = False

        result, status = _extract_from_excel('/nonexistent.xlsx')
        assert status == 404
        assert result.get('success') is False
        assert '文件不存在' in result.get('message', '')

    @patch('openpyxl.load_workbook')
    @patch('app.routes.excel_extract.os.path.exists')
    def test_extract_from_excel_success(self, mock_exists, mock_load_workbook):
        """测试 _extract_from_excel - 成功提取"""
        from app.routes.excel_extract import _extract_from_excel

        mock_exists.return_value = True

        mock_ws = MagicMock()
        mock_ws.title = "Sheet1"
        mock_ws.max_column = 2
        mock_ws.max_row = 3
        mock_ws.cell.side_effect = lambda row, col: MagicMock(value=f"cell_{row}_{col}")

        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Sheet1"]
        mock_wb.__getitem__ = MagicMock(return_value=mock_ws)
        mock_load_workbook.return_value = mock_wb

        result, status = _extract_from_excel('/test.xlsx')
        assert status == 200
        assert result.get('success') is True
        assert result.get('file') == 'test.xlsx'
        assert result.get('sheet') == 'Sheet1'

    @patch('openpyxl.load_workbook')
    @patch('app.routes.excel_extract.os.path.exists')
    def test_extract_from_excel_with_sheet_name(self, mock_exists, mock_load_workbook):
        """测试 _extract_from_excel - 指定工作表"""
        from app.routes.excel_extract import _extract_from_excel

        mock_exists.return_value = True

        mock_ws = MagicMock()
        mock_ws.title = "Sheet2"
        mock_ws.max_column = 2
        mock_ws.max_row = 2
        mock_ws.cell.side_effect = lambda row, col: MagicMock(value=f"cell_{row}_{col}")

        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Sheet1", "Sheet2"]
        mock_wb.__getitem__ = MagicMock(return_value=mock_ws)
        mock_load_workbook.return_value = mock_wb

        result, status = _extract_from_excel('/test.xlsx', sheet_name='Sheet2')
        assert status == 200
        assert result.get('sheet') == 'Sheet2'

    @patch('openpyxl.load_workbook')
    @patch('app.routes.excel_extract.os.path.exists')
    def test_extract_from_excel_exception(self, mock_exists, mock_load_workbook):
        """测试 _extract_from_excel - 异常处理"""
        from app.routes.excel_extract import _extract_from_excel

        mock_exists.return_value = True
        mock_load_workbook.side_effect = Exception("Load error")

        result, status = _extract_from_excel('/test.xlsx')
        assert status == 500
        assert result.get('success') is False

    @patch('openpyxl.Workbook')
    @patch('app.routes.excel_extract.os.makedirs')
    def test_generate_excel_success(self, mock_makedirs, mock_workbook):
        """测试 _generate_excel - 成功生成"""
        from app.routes.excel_extract import _generate_excel

        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.active = mock_ws
        mock_workbook.return_value = mock_wb

        data = [{"col1": "val1", "col2": "val2"}]

        result, status = _generate_excel(data, filename='test.xlsx')
        assert status == 200
        assert result.get('success') is True
        assert result.get('filename') == 'test.xlsx'
        assert result.get('rows') == 1

    @patch('openpyxl.Workbook')
    @patch('app.routes.excel_extract.os.makedirs')
    def test_generate_excel_empty_data(self, mock_makedirs, mock_workbook):
        """测试 _generate_excel - 空数据"""
        from app.routes.excel_extract import _generate_excel

        result, status = _generate_excel([])
        assert status == 400
        assert result.get('success') is False
        assert '数据格式错误' in result.get('message', '')

    @patch('openpyxl.Workbook')
    @patch('app.routes.excel_extract.os.makedirs')
    def test_generate_excel_invalid_data_format(self, mock_makedirs, mock_workbook):
        """测试 _generate_excel - 无效数据格式"""
        from app.routes.excel_extract import _generate_excel

        result, status = _generate_excel("not a list")
        assert status == 400
        assert result.get('success') is False

    @patch('openpyxl.Workbook')
    @patch('app.routes.excel_extract.os.makedirs')
    def test_generate_excel_with_sheet_name(self, mock_makedirs, mock_workbook):
        """测试 _generate_excel - 指定工作表名"""
        from app.routes.excel_extract import _generate_excel

        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.active = mock_ws
        mock_workbook.return_value = mock_wb

        data = [{"col1": "val1"}]

        result, status = _generate_excel(data, sheet_name='MySheet')
        assert status == 200
        mock_ws.title = 'MySheet'

    @patch('openpyxl.Workbook')
    @patch('app.routes.excel_extract.os.makedirs')
    def test_generate_excel_exception(self, mock_makedirs, mock_workbook):
        """测试 _generate_excel - 异常处理"""
        from app.routes.excel_extract import _generate_excel

        mock_workbook.side_effect = Exception("Workbook error")

        result, status = _generate_excel([{"col1": "val1"}])
        assert status == 500
        assert result.get('success') is False


class TestExcelExtract:
    """Excel 提取与生成路由测试"""

    def test_extract_test(self, client):
        """测试提取服务健康检查接口"""
        response = client.get('/api/excel/data/extract/test')
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert 'timestamp' in data

    @patch('app.routes.excel_extract._extract_from_excel')
    def test_extract_from_excel_success(self, mock_extract, client):
        """测试从 Excel 文件提取数据 - 成功"""
        mock_extract.return_value = ({
            "success": True,
            "file": "test.xlsx",
            "sheet": "Sheet1",
            "headers": [{"column": "A", "column_index": 1, "value": "名称"}],
            "rows": [{"名称": "产品1"}],
            "total_rows": 1
        }, 200)

        response = client.post(
            '/api/excel/data/extract',
            json={"file_path": "/path/to/test.xlsx"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True

    def test_extract_from_excel_missing_file_path(self, client):
        """测试从 Excel 文件提取数据 - 缺少文件路径"""
        response = client.post(
            '/api/excel/data/extract',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get('success') is False

    @patch('app.routes.excel_extract._extract_from_excel')
    def test_extract_from_excel_file_not_found(self, mock_extract, client):
        """测试从 Excel 文件提取数据 - 文件不存在"""
        mock_extract.return_value = ({"success": False, "message": "文件不存在"}, 404)

        response = client.post(
            '/api/excel/data/extract',
            json={"file_path": "/nonexistent.xlsx"},
            content_type='application/json'
        )
        assert response.status_code == 404

    @patch('app.routes.excel_extract._extract_from_excel')
    def test_extract_from_excel_with_sheet_name(self, mock_extract, client):
        """测试从 Excel 文件提取数据 - 指定工作表"""
        mock_extract.return_value = ({
            "success": True,
            "file": "test.xlsx",
            "sheet": "Sheet2",
            "headers": [{"column": "A", "column_index": 1, "value": "名称"}],
            "rows": [{"名称": "产品1"}],
            "total_rows": 1
        }, 200)

        response = client.post(
            '/api/excel/data/extract',
            json={"file_path": "/path/to/test.xlsx", "sheet_name": "Sheet2"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert data.get('sheet') == "Sheet2"

    @patch('app.routes.excel_extract._extract_from_excel')
    def test_extract_from_excel_with_header_row(self, mock_extract, client):
        """测试从 Excel 文件提取数据 - 指定表头行"""
        mock_extract.return_value = ({
            "success": True,
            "file": "test.xlsx",
            "sheet": "Sheet1",
            "header_row": 2,
            "headers": [{"column": "A", "column_index": 1, "value": "名称"}],
            "rows": [{"名称": "产品1"}],
            "total_rows": 1
        }, 200)

        response = client.post(
            '/api/excel/data/extract',
            json={"file_path": "/path/to/test.xlsx", "header_row": 2},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert data.get('header_row') == 2

    @patch('app.routes.excel_extract._extract_from_excel')
    def test_extract_from_excel_server_error(self, mock_extract, client):
        """测试从 Excel 文件提取数据 - 服务器错误"""
        mock_extract.return_value = ({"success": False, "message": "读取文件失败"}, 500)

        response = client.post(
            '/api/excel/data/extract',
            json={"file_path": "/path/to/test.xlsx"},
            content_type='application/json'
        )
        assert response.status_code == 500

    @patch('app.routes.excel_extract._extract_from_excel')
    def test_extract_from_excel_exception(self, mock_extract, client):
        """测试从 Excel 文件提取数据 - 异常处理"""
        mock_extract.side_effect = Exception("Unexpected error")

        response = client.post(
            '/api/excel/data/extract',
            json={"file_path": "/path/to/test.xlsx"},
            content_type='application/json'
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data.get('success') is False


class TestExcelUpload:
    """Excel 上传提取测试"""

    def test_extract_upload_no_file(self, client):
        """测试上传提取 - 无文件"""
        response = client.post('/api/excel/data/extract/upload')
        assert response.status_code == 400
        data = response.get_json()
        assert data.get('success') is False

    def test_extract_upload_empty_filename(self, client):
        """测试上传提取 - 文件名为空"""
        data = {
            'excel_file': (BytesIO(b''), '')
        }
        response = client.post(
            '/api/excel/data/extract/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400

    def test_extract_upload_invalid_file_type(self, client):
        """测试上传提取 - 无效文件类型"""
        data = {
            'excel_file': (BytesIO(b'test'), 'test.txt')
        }
        response = client.post(
            '/api/excel/data/extract/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400

    @patch('app.routes.excel_extract._extract_from_excel')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_extract_upload_success(self, mock_remove, mock_exists, mock_extract, client):
        """测试上传提取 - 成功"""
        mock_exists.return_value = True
        mock_extract.return_value = ({
            "success": True,
            "file": "test.xlsx",
            "headers": [{"column": "A", "column_index": 1, "value": "名称"}],
            "rows": [{"名称": "产品1"}],
            "total_rows": 1
        }, 200)

        data = {
            'excel_file': (BytesIO(b'test content'), 'test.xlsx')
        }
        response = client.post(
            '/api/excel/data/extract/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True

    @patch('app.routes.excel_extract._extract_from_excel')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_extract_upload_with_sheet_name(self, mock_remove, mock_exists, mock_extract, client):
        """测试上传提取 - 指定工作表"""
        mock_exists.return_value = True
        mock_extract.return_value = ({
            "success": True,
            "file": "test.xlsx",
            "sheet": "Sheet2",
            "headers": [{"column": "A", "column_index": 1, "value": "名称"}],
            "rows": [{"名称": "产品1"}],
            "total_rows": 1
        }, 200)

        data = {
            'excel_file': (BytesIO(b'test content'), 'test.xlsx'),
            'sheet_name': 'Sheet2'
        }
        response = client.post(
            '/api/excel/data/extract/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200

    @patch('app.routes.excel_extract._extract_from_excel')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_extract_upload_with_header_row(self, mock_remove, mock_exists, mock_extract, client):
        """测试上传提取 - 指定表头行"""
        mock_exists.return_value = True
        mock_extract.return_value = ({
            "success": True,
            "file": "test.xlsx",
            "header_row": 2,
            "headers": [{"column": "A", "column_index": 1, "value": "名称"}],
            "rows": [{"名称": "产品1"}],
            "total_rows": 1
        }, 200)

        data = {
            'excel_file': (BytesIO(b'test content'), 'test.xlsx'),
            'header_row': '2'
        }
        response = client.post(
            '/api/excel/data/extract/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200

    @patch('app.routes.excel_extract._extract_from_excel')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_extract_upload_file_not_found(self, mock_remove, mock_exists, mock_extract, client):
        """测试上传提取 - 文件不存在"""
        mock_exists.return_value = True
        mock_extract.return_value = ({"success": False, "message": "文件不存在"}, 404)

        data = {
            'excel_file': (BytesIO(b'test content'), 'test.xlsx')
        }
        response = client.post(
            '/api/excel/data/extract/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 404

    @patch('app.routes.excel_extract._extract_from_excel')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_extract_upload_server_error(self, mock_remove, mock_exists, mock_extract, client):
        """测试上传提取 - 服务器错误"""
        mock_exists.return_value = True
        mock_extract.return_value = ({"success": False, "message": "处理失败"}, 500)

        data = {
            'excel_file': (BytesIO(b'test content'), 'test.xlsx')
        }
        response = client.post(
            '/api/excel/data/extract/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 500

    @patch('app.routes.excel_extract._extract_from_excel')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_extract_upload_exception(self, mock_remove, mock_exists, mock_extract, client):
        """测试上传提取 - 异常处理"""
        mock_exists.return_value = True
        mock_extract.side_effect = Exception("Unexpected error")

        data = {
            'excel_file': (BytesIO(b'test content'), 'test.xlsx')
        }
        response = client.post(
            '/api/excel/data/extract/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 500


class TestExcelGenerate:
    """Excel 生成测试"""

    def test_generate_excel_empty_data(self, client):
        """测试生成 Excel - 空数据"""
        response = client.post(
            '/api/excel/data/generate',
            json={"data": []},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get('success') is False

    def test_generate_excel_missing_data(self, client):
        """测试生成 Excel - 缺少数据参数"""
        response = client.post(
            '/api/excel/data/generate',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get('success') is False

    @patch('app.routes.excel_extract._generate_excel')
    def test_generate_excel_success(self, mock_generate, client):
        """测试生成 Excel - 成功"""
        mock_generate.return_value = ({
            "success": True,
            "file_path": "/tmp/test.xlsx",
            "filename": "test.xlsx",
            "rows": 2
        }, 200)

        response = client.post(
            '/api/excel/data/generate',
            json={
                "data": [
                    {"名称": "产品1", "价格": 100},
                    {"名称": "产品2", "价格": 200}
                ],
                "filename": "test.xlsx"
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True

    @patch('app.routes.excel_extract._generate_excel')
    def test_generate_excel_invalid_data_format(self, mock_generate, client):
        """测试生成 Excel - 无效数据格式"""
        mock_generate.return_value = ({"success": False, "message": "数据格式错误，需要数组类型"}, 400)

        response = client.post(
            '/api/excel/data/generate',
            json={"data": "not a list"},
            content_type='application/json'
        )
        assert response.status_code == 400

    @patch('app.routes.excel_extract._generate_excel')
    def test_generate_excel_with_filename(self, mock_generate, client):
        """测试生成 Excel - 指定文件名"""
        mock_generate.return_value = ({
            "success": True,
            "file_path": "/tmp/custom.xlsx",
            "filename": "custom.xlsx",
            "rows": 2
        }, 200)

        response = client.post(
            '/api/excel/data/generate',
            json={
                "data": [{"col1": "val1", "col2": "val2"}],
                "filename": "custom.xlsx"
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('filename') == "custom.xlsx"

    @patch('app.routes.excel_extract._generate_excel')
    def test_generate_excel_with_sheet_name(self, mock_generate, client):
        """测试生成 Excel - 指定工作表名"""
        mock_generate.return_value = ({
            "success": True,
            "file_path": "/tmp/test.xlsx",
            "filename": "test.xlsx",
            "sheet": "MySheet",
            "rows": 2
        }, 200)

        response = client.post(
            '/api/excel/data/generate',
            json={
                "data": [{"col1": "val1"}],
                "sheet_name": "MySheet"
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('sheet') == "MySheet"

    @patch('app.routes.excel_extract._generate_excel')
    def test_generate_excel_server_error(self, mock_generate, client):
        """测试生成 Excel - 服务器错误"""
        mock_generate.return_value = ({"success": False, "message": "生成失败"}, 500)

        response = client.post(
            '/api/excel/data/generate',
            json={"data": [{"col": "val"}]},
            content_type='application/json'
        )
        assert response.status_code == 500

    @patch('app.routes.excel_extract._generate_excel')
    def test_generate_excel_exception(self, mock_generate, client):
        """测试生成 Excel - 异常处理"""
        mock_generate.side_effect = Exception("Unexpected error")

        response = client.post(
            '/api/excel/data/generate',
            json={"data": [{"col": "val"}]},
            content_type='application/json'
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data.get('success') is False


class TestExcelDownload:
    """Excel 下载测试"""

    def test_download_excel_empty_data(self, client):
        """测试下载 Excel - 空数据"""
        response = client.post(
            '/api/excel/data/generate/download',
            json={"data": []},
            content_type='application/json'
        )
        assert response.status_code == 400

    @patch('app.routes.excel_extract._generate_excel')
    def test_download_excel_file_not_exists(self, mock_generate, client):
        """测试下载 Excel - 生成后文件不存在"""
        mock_generate.return_value = ({
            "success": True,
            "file_path": "/nonexistent/test.xlsx",
            "filename": "test.xlsx",
            "rows": 1
        }, 200)

        with patch('os.path.exists', return_value=False):
            response = client.post(
                '/api/excel/data/generate/download',
                json={"data": [{"col": "value"}]},
                content_type='application/json'
            )
            assert response.status_code == 500

    @patch('app.routes.excel_extract._generate_excel')
    @patch('os.path.exists')
    def test_download_excel_success(self, mock_exists, mock_generate, client):
        """测试下载 Excel - 成功"""
        mock_generate.return_value = ({
            "success": True,
            "file_path": "/tmp/test.xlsx",
            "filename": "test.xlsx",
            "rows": 1
        }, 200)
        mock_exists.return_value = True

        with patch('app.routes.excel_extract.send_file') as mock_send_file:
            mock_send_file.return_value = b'fake excel content'
            response = client.post(
                '/api/excel/data/generate/download',
                json={"data": [{"col": "value"}]},
                content_type='application/json'
            )
            assert response.status_code == 200

    @patch('app.routes.excel_extract._generate_excel')
    def test_download_excel_generate_failed(self, mock_generate, client):
        """测试下载 Excel - 生成失败"""
        mock_generate.return_value = ({"success": False, "message": "生成失败"}, 400)

        response = client.post(
            '/api/excel/data/generate/download',
            json={"data": [{"col": "value"}]},
            content_type='application/json'
        )
        assert response.status_code == 400

    @patch('app.routes.excel_extract._generate_excel')
    @patch('os.path.exists')
    def test_download_excel_with_filename(self, mock_exists, mock_generate, client):
        """测试下载 Excel - 指定文件名"""
        mock_generate.return_value = ({
            "success": True,
            "file_path": "/tmp/custom.xlsx",
            "filename": "custom.xlsx",
            "rows": 1
        }, 200)
        mock_exists.return_value = True

        with patch('app.routes.excel_extract.send_file') as mock_send_file:
            mock_send_file.return_value = b'fake excel content'
            response = client.post(
                '/api/excel/data/generate/download',
                json={
                    "data": [{"col": "value"}],
                    "filename": "custom.xlsx"
                },
                content_type='application/json'
            )
            assert response.status_code == 200

    @patch('app.routes.excel_extract._generate_excel')
    @patch('os.path.exists')
    def test_download_excel_exception(self, mock_exists, mock_generate, client):
        """测试下载 Excel - 异常处理"""
        mock_generate.return_value = ({
            "success": True,
            "file_path": "/tmp/test.xlsx",
            "filename": "test.xlsx",
            "rows": 1
        }, 200)
        mock_exists.side_effect = Exception("File system error")

        response = client.post(
            '/api/excel/data/generate/download',
            json={"data": [{"col": "value"}]},
            content_type='application/json'
        )
        assert response.status_code == 500


class TestCustomerImport:
    """客户导入测试"""

    @patch('app.services.ExtractLogService')
    @patch('app.services.CustomerImportService')
    def test_import_customers_success(self, mock_customer_service, mock_log_service, client):
        """测试客户导入 - 成功"""
        mock_log_instance = MagicMock()
        mock_log_instance.create_log.return_value = 1
        mock_log_instance.update_log.return_value = None
        mock_log_service.return_value = mock_log_instance

        mock_service_instance = MagicMock()
        mock_service_instance.import_data.return_value = {
            'imported': 3,
            'skipped': 0,
            'failed': 0,
            'details': {'skipped_items': [], 'failed_items': []}
        }
        mock_customer_service.return_value = mock_service_instance

        response = client.post(
            '/api/excel/data/import/customers',
            json={
                "data": [
                    {"unit_name": "公司1", "contact": "张三", "phone": "13800138000"},
                    {"unit_name": "公司2", "contact": "李四", "phone": "13900139000"},
                    {"unit_name": "公司3", "contact": "王五", "phone": "13700137000"}
                ],
                "file_name": "customers.xlsx"
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert data.get('imported') == 3

    def test_import_customers_missing_data(self, client):
        """测试客户导入 - 缺少数据"""
        response = client.post(
            '/api/excel/data/import/customers',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 400

    @patch('app.services.ExtractLogService')
    @patch('app.services.CustomerImportService')
    def test_import_customers_with_options(self, mock_customer_service, mock_log_service, client):
        """测试客户导入 - 带选项"""
        mock_log_instance = MagicMock()
        mock_log_instance.create_log.return_value = 1
        mock_log_service.return_value = mock_log_instance

        mock_service_instance = MagicMock()
        mock_service_instance.import_data.return_value = {
            'imported': 2,
            'skipped': 1,
            'failed': 0,
            'details': {'skipped_items': [], 'failed_items': []}
        }
        mock_customer_service.return_value = mock_service_instance

        response = client.post(
            '/api/excel/data/import/customers',
            json={
                "data": [
                    {"unit_name": "公司1", "contact": "张三"},
                    {"unit_name": "公司2", "contact": "李四"},
                    {"unit_name": "公司3", "contact": "王五"}
                ],
                "options": {
                    "skip_duplicates": True,
                    "validate_before_import": False,
                    "clean_data": True
                }
            },
            content_type='application/json'
        )
        assert response.status_code == 200

    @patch('app.services.ExtractLogService')
    @patch('app.services.CustomerImportService')
    def test_import_customers_partial_success(self, mock_customer_service, mock_log_service, client):
        """测试客户导入 - 部分成功"""
        mock_log_instance = MagicMock()
        mock_log_instance.create_log.return_value = 1
        mock_log_instance.update_log.return_value = None
        mock_log_service.return_value = mock_log_instance

        mock_service_instance = MagicMock()
        mock_service_instance.import_data.return_value = {
            'imported': 2,
            'skipped': 1,
            'failed': 1,
            'details': {
                'skipped_items': [{'row': 2, 'reason': 'duplicate'}],
                'failed_items': [{'row': 3, 'reason': 'invalid data'}]
            }
        }
        mock_customer_service.return_value = mock_service_instance

        response = client.post(
            '/api/excel/data/import/customers',
            json={
                "data": [
                    {"unit_name": "公司1", "contact": "张三"},
                    {"unit_name": "公司2", "contact": "李四"},
                    {"unit_name": "公司3", "contact": "王五"}
                ]
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert data.get('imported') == 2
        assert data.get('failed') == 1

    @patch('app.services.ExtractLogService')
    @patch('app.services.CustomerImportService')
    def test_import_customers_exception(self, mock_customer_service, mock_log_service, client):
        """测试客户导入 - 异常处理"""
        mock_log_instance = MagicMock()
        mock_log_instance.create_log.return_value = 1
        mock_log_service.return_value = mock_log_instance

        mock_service_instance = MagicMock()
        mock_service_instance.import_data.side_effect = Exception("Import failed")
        mock_customer_service.return_value = mock_service_instance

        response = client.post(
            '/api/excel/data/import/customers',
            json={
                "data": [{"unit_name": "公司1", "contact": "张三"}]
            },
            content_type='application/json'
        )
        assert response.status_code == 500


class TestProductImport:
    """产品导入测试"""

    @patch('app.services.ExtractLogService')
    @patch('app.services.ProductImportService')
    def test_import_products_success(self, mock_product_service, mock_log_service, client):
        """测试产品导入 - 成功"""
        mock_log_instance = MagicMock()
        mock_log_instance.create_log.return_value = 1
        mock_log_instance.update_log.return_value = None
        mock_log_service.return_value = mock_log_instance

        mock_service_instance = MagicMock()
        mock_service_instance.import_data.return_value = {
            'imported': 5,
            'skipped': 0,
            'failed': 0,
            'details': {'skipped_items': [], 'failed_items': []}
        }
        mock_product_service.return_value = mock_service_instance

        response = client.post(
            '/api/excel/data/import/products',
            json={
                "data": [
                    {"name": "产品1", "price": 100, "stock": 10},
                    {"name": "产品2", "price": 200, "stock": 20},
                    {"name": "产品3", "price": 300, "stock": 30},
                    {"name": "产品4", "price": 400, "stock": 40},
                    {"name": "产品5", "price": 500, "stock": 50}
                ],
                "file_name": "products.xlsx"
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert data.get('imported') == 5

    def test_import_products_missing_data(self, client):
        """测试产品导入 - 缺少数据"""
        response = client.post(
            '/api/excel/data/import/products',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 400

    @patch('app.services.ExtractLogService')
    @patch('app.services.ProductImportService')
    def test_import_products_with_options(self, mock_product_service, mock_log_service, client):
        """测试产品导入 - 带选项"""
        mock_log_instance = MagicMock()
        mock_log_instance.create_log.return_value = 1
        mock_log_service.return_value = mock_log_instance

        mock_service_instance = MagicMock()
        mock_service_instance.import_data.return_value = {
            'imported': 3,
            'skipped': 2,
            'failed': 0,
            'details': {'skipped_items': [], 'failed_items': []}
        }
        mock_product_service.return_value = mock_service_instance

        response = client.post(
            '/api/excel/data/import/products',
            json={
                "data": [
                    {"name": "产品1", "price": 100},
                    {"name": "产品2", "price": 200},
                    {"name": "产品3", "price": 300},
                    {"name": "产品4", "price": 400},
                    {"name": "产品5", "price": 500}
                ],
                "options": {
                    "skip_duplicates": True,
                    "validate_before_import": True,
                    "clean_data": True
                }
            },
            content_type='application/json'
        )
        assert response.status_code == 200

    @patch('app.services.ExtractLogService')
    @patch('app.services.ProductImportService')
    def test_import_products_partial_success(self, mock_product_service, mock_log_service, client):
        """测试产品导入 - 部分成功"""
        mock_log_instance = MagicMock()
        mock_log_instance.create_log.return_value = 1
        mock_log_instance.update_log.return_value = None
        mock_log_service.return_value = mock_log_instance

        mock_service_instance = MagicMock()
        mock_service_instance.import_data.return_value = {
            'imported': 3,
            'skipped': 1,
            'failed': 1,
            'details': {
                'skipped_items': [{'row': 2, 'reason': 'duplicate'}],
                'failed_items': [{'row': 4, 'reason': 'invalid price'}]
            }
        }
        mock_product_service.return_value = mock_service_instance

        response = client.post(
            '/api/excel/data/import/products',
            json={
                "data": [
                    {"name": "产品1", "price": 100},
                    {"name": "产品2", "price": 200},
                    {"name": "产品3", "price": 300},
                    {"name": "产品4", "price": 400},
                    {"name": "产品5", "price": 500}
                ]
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert data.get('imported') == 3
        assert data.get('failed') == 1

    @patch('app.services.ExtractLogService')
    @patch('app.services.ProductImportService')
    def test_import_products_with_field_mapping(self, mock_product_service, mock_log_service, client):
        """测试产品导入 - 带字段映射"""
        mock_log_instance = MagicMock()
        mock_log_instance.create_log.return_value = 1
        mock_log_instance.update_log.return_value = None
        mock_log_service.return_value = mock_log_instance

        mock_service_instance = MagicMock()
        mock_service_instance.import_data.return_value = {
            'imported': 2,
            'skipped': 0,
            'failed': 0,
            'details': {'skipped_items': [], 'failed_items': []}
        }
        mock_product_service.return_value = mock_service_instance

        response = client.post(
            '/api/excel/data/import/products',
            json={
                "data": [
                    {"产品名称": "产品1", "单价": 100},
                    {"产品名称": "产品2", "单价": 200}
                ],
                "field_mapping": {
                    "产品名称": "name",
                    "单价": "price"
                }
            },
            content_type='application/json'
        )
        assert response.status_code == 200

    @patch('app.services.ExtractLogService')
    @patch('app.services.ProductImportService')
    def test_import_products_exception(self, mock_product_service, mock_log_service, client):
        """测试产品导入 - 异常处理"""
        mock_log_instance = MagicMock()
        mock_log_instance.create_log.return_value = 1
        mock_log_service.return_value = mock_log_instance

        mock_service_instance = MagicMock()
        mock_service_instance.import_data.side_effect = Exception("Import failed")
        mock_product_service.return_value = mock_service_instance

        response = client.post(
            '/api/excel/data/import/products',
            json={
                "data": [{"name": "产品1", "price": 100}]
            },
            content_type='application/json'
        )
        assert response.status_code == 500


class TestExtractLogs:
    """提取日志测试"""

    @patch('app.services.ExtractLogService')
    def test_get_logs_success(self, mock_log_service, client):
        """测试获取日志列表 - 成功"""
        mock_log_instance = MagicMock()
        mock_log_instance.get_logs.return_value = [
            {"id": 1, "file_name": "test1.xlsx", "status": "completed"},
            {"id": 2, "file_name": "test2.xlsx", "status": "pending"}
        ]
        mock_log_service.return_value = mock_log_instance

        response = client.get('/api/excel/data/logs')
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert len(data.get('logs', [])) == 2

    @patch('app.services.ExtractLogService')
    def test_get_logs_with_filters(self, mock_log_service, client):
        """测试获取日志列表 - 带过滤条件"""
        mock_log_instance = MagicMock()
        mock_log_instance.get_logs.return_value = [
            {"id": 1, "file_name": "products.xlsx", "data_type": "products", "status": "completed"}
        ]
        mock_log_service.return_value = mock_log_instance

        response = client.get('/api/excel/data/logs?data_type=products&status=completed')
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True

    @patch('app.services.ExtractLogService')
    def test_get_logs_empty(self, mock_log_service, client):
        """测试获取日志列表 - 空结果"""
        mock_log_instance = MagicMock()
        mock_log_instance.get_logs.return_value = []
        mock_log_service.return_value = mock_log_instance

        response = client.get('/api/excel/data/logs')
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert data.get('total') == 0

    @patch('app.services.ExtractLogService')
    def test_get_logs_with_limit(self, mock_log_service, client):
        """测试获取日志列表 - 带限制"""
        mock_log_instance = MagicMock()
        mock_log_instance.get_logs.return_value = [
            {"id": 1, "file_name": "test1.xlsx"},
            {"id": 2, "file_name": "test2.xlsx"},
            {"id": 3, "file_name": "test3.xlsx"}
        ]
        mock_log_service.return_value = mock_log_instance

        response = client.get('/api/excel/data/logs?limit=3')
        assert response.status_code == 200

    @patch('app.services.ExtractLogService')
    def test_get_logs_with_offset(self, mock_log_service, client):
        """测试获取日志列表 - 带偏移量"""
        mock_log_instance = MagicMock()
        mock_log_instance.get_logs.return_value = [
            {"id": 6, "file_name": "test6.xlsx"},
            {"id": 7, "file_name": "test7.xlsx"}
        ]
        mock_log_service.return_value = mock_log_instance

        response = client.get('/api/excel/data/logs?offset=5&limit=2')
        assert response.status_code == 200

    @patch('app.services.ExtractLogService')
    def test_get_logs_with_status_filter(self, mock_log_service, client):
        """测试获取日志列表 - 按状态过滤"""
        mock_log_instance = MagicMock()
        mock_log_instance.get_logs.return_value = [
            {"id": 1, "file_name": "test1.xlsx", "status": "failed"},
            {"id": 2, "file_name": "test2.xlsx", "status": "failed"}
        ]
        mock_log_service.return_value = mock_log_instance

        response = client.get('/api/excel/data/logs?status=failed')
        assert response.status_code == 200

    @patch('app.services.ExtractLogService')
    def test_get_logs_exception(self, mock_log_service, client):
        """测试获取日志列表 - 异常处理"""
        mock_log_instance = MagicMock()
        mock_log_instance.get_logs.side_effect = Exception("Database error")
        mock_log_service.return_value = mock_log_instance

        response = client.get('/api/excel/data/logs')
        assert response.status_code == 500


class TestExtractLogDetail:
    """提取日志详情测试"""

    @patch('app.services.ExtractLogService')
    def test_get_log_detail_success(self, mock_log_service, client):
        """测试获取日志详情 - 成功"""
        mock_log_instance = MagicMock()
        mock_log_instance.get_log.return_value = {
            "id": 1,
            "file_name": "test.xlsx",
            "data_type": "products",
            "status": "completed",
            "total_rows": 10,
            "imported_rows": 8,
            "skipped_rows": 1,
            "failed_rows": 1
        }
        mock_log_service.return_value = mock_log_instance

        response = client.get('/api/excel/data/logs/1')
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True
        assert data.get('log', {}).get('id') == 1

    @patch('app.services.ExtractLogService')
    def test_get_log_detail_not_found(self, mock_log_service, client):
        """测试获取日志详情 - 不存在"""
        mock_log_instance = MagicMock()
        mock_log_instance.get_log.return_value = None
        mock_log_service.return_value = mock_log_instance

        response = client.get('/api/excel/data/logs/999')
        assert response.status_code == 404
        data = response.get_json()
        assert data.get('success') is False

    @patch('app.services.ExtractLogService')
    def test_get_log_detail_exception(self, mock_log_service, client):
        """测试获取日志详情 - 异常处理"""
        mock_log_instance = MagicMock()
        mock_log_instance.get_log.side_effect = Exception("Database error")
        mock_log_service.return_value = mock_log_instance

        response = client.get('/api/excel/data/logs/1')
        assert response.status_code == 500

    @patch('app.services.ExtractLogService')
    def test_get_log_detail_with_different_status(self, mock_log_service, client):
        """测试获取日志详情 - 不同状态"""
        mock_log_instance = MagicMock()
        mock_log_instance.get_log.return_value = {
            "id": 2,
            "file_name": "test2.xlsx",
            "data_type": "customers",
            "status": "partial",
            "total_rows": 10,
            "imported_rows": 7,
            "skipped_rows": 2,
            "failed_rows": 1
        }
        mock_log_service.return_value = mock_log_instance

        response = client.get('/api/excel/data/logs/2')
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('log', {}).get('status') == "partial"


class TestPreviewData:
    """预览数据测试"""

    @patch('app.services.ExtractLogService')
    def test_get_preview_success(self, mock_log_service, client):
        """测试预览数据 - 成功"""
        mock_log_instance = MagicMock()
        mock_log_instance.get_log.return_value = {
            "id": 1,
            "file_name": "test.xlsx",
            "status": "completed"
        }
        mock_log_service.return_value = mock_log_instance

        response = client.get('/api/excel/data/preview/1')
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True

    @patch('app.services.ExtractLogService')
    def test_get_preview_not_found(self, mock_log_service, client):
        """测试预览数据 - 日志不存在"""
        mock_log_instance = MagicMock()
        mock_log_instance.get_log.return_value = None
        mock_log_service.return_value = mock_log_instance

        response = client.get('/api/excel/data/preview/999')
        assert response.status_code == 404
        data = response.get_json()
        assert data.get('success') is False

    @patch('app.services.ExtractLogService')
    def test_get_preview_exception(self, mock_log_service, client):
        """测试预览数据 - 异常处理"""
        mock_log_instance = MagicMock()
        mock_log_instance.get_log.side_effect = Exception("Database error")
        mock_log_service.return_value = mock_log_instance

        response = client.get('/api/excel/data/preview/1')
        assert response.status_code == 500

    @patch('app.services.ExtractLogService')
    def test_get_preview_with_different_status(self, mock_log_service, client):
        """测试预览数据 - 不同状态"""
        mock_log_instance = MagicMock()
        mock_log_instance.get_log.return_value = {
            "id": 2,
            "file_name": "test2.xlsx",
            "status": "pending"
        }
        mock_log_service.return_value = mock_log_instance

        response = client.get('/api/excel/data/preview/2')
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('log', {}).get('status') == "pending"
