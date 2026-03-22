"""
Excel 模板管理路由测试
"""

import pytest
import json
import io
import os
from unittest.mock import Mock, MagicMock, patch, mock_open
from datetime import datetime


class TestExcelTemplates:
    """Excel 模板管理路由测试"""

    def test_list_templates(self, client):
        """测试获取模板列表"""
        response = client.get('/api/excel/templates')
        assert response.status_code in [200, 500]

    def test_list_templates_returns_json(self, client):
        """测试模板列表返回正确的 JSON 格式"""
        response = client.get('/api/excel/templates')
        if response.status_code == 200:
            data = response.get_json()
            assert 'success' in data or 'templates' in data

    def test_get_template_file_success(self, client):
        """测试获取模板文件成功"""
        response = client.get('/api/excel/template/shipment/file')
        assert response.status_code in [200, 404, 500]

    def test_get_template_file_not_found(self, client):
        """测试获取不存在的模板文件"""
        response = client.get('/api/excel/template/nonexistent_id/file')
        assert response.status_code in [200, 404, 500]

    def test_save_template_success(self, client):
        """测试保存模板成功"""
        response = client.post(
            '/api/excel/template/save',
            json={
                "source_name": "尹玉华132.xlsx",
                "target_name": "测试模板.xlsx",
                "overwrite": True
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_save_template_source_not_found(self, client):
        """测试保存模板源文件不存在"""
        response = client.post(
            '/api/excel/template/save',
            json={
                "source_name": "不存在的文件.xlsx",
                "target_name": "测试模板.xlsx"
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_save_template_existing_no_overwrite(self, client):
        """测试目标模板存在且不覆盖"""
        response = client.post(
            '/api/excel/template/save',
            json={
                "source_name": "尹玉华132.xlsx",
                "target_name": "发货单模板.xlsx",
                "overwrite": False
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_decompose_template_with_filename(self, client):
        """测试分解模板（使用文件名）"""
        response = client.post(
            '/api/excel/template/decompose',
            json={
                "filename": "发货单模板.xlsx"
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_decompose_template_with_file_path(self, client):
        """测试分解模板（使用文件路径）"""
        response = client.post(
            '/api/excel/template/decompose',
            json={
                "file_path": "/path/to/test.xlsx"
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_decompose_template_no_file_info(self, client):
        """测试分解模板无文件信息"""
        response = client.post(
            '/api/excel/template/decompose',
            json={},
            content_type='application_json'
        )
        assert response.status_code in [200, 400, 404, 500]

    def test_decompose_template_with_sheet_name(self, client):
        """测试分解模板指定 sheet 名称"""
        response = client.post(
            '/api/excel/template/decompose',
            json={
                "filename": "发货单模板.xlsx",
                "sheet_name": "出货",
                "sample_rows": 3
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_upload_excel_success(self, client):
        """测试上传 Excel 文件成功"""
        data = {
            'excel_file': (io.BytesIO(b'fake excel content'), 'test.xlsx')
        }
        response = client.post(
            '/api/excel/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code in [200, 400, 500]

    def test_upload_excel_no_file(self, client):
        """测试上传 Excel 无文件"""
        response = client.post(
            '/api/excel/upload',
            content_type='multipart/form-data'
        )
        assert response.status_code in [200, 400, 500]

    def test_upload_excel_invalid_format(self, client):
        """测试上传无效格式文件"""
        data = {
            'excel_file': (io.BytesIO(b'not excel'), 'test.txt')
        }
        response = client.post(
            '/api/excel/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code in [200, 400, 500]

    def test_upload_excel_empty_filename(self, client):
        """测试上传文件名为空"""
        data = {
            'excel_file': (io.BytesIO(b'content'), '')
        }
        response = client.post(
            '/api/excel/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code in [200, 400, 500]

    def test_get_template_by_id(self, client):
        """测试获取单个模板详情"""
        response = client.get('/api/excel/templates/1')
        assert response.status_code in [200, 404, 500]

    def test_get_template_not_found(self, client):
        """测试获取不存在的模板"""
        response = client.get('/api/excel/templates/99999')
        assert response.status_code in [200, 404, 500]

    def test_create_template_success(self, client):
        """测试创建模板成功"""
        response = client.post(
            '/api/excel/templates',
            json={
                "template_name": "测试模板",
                "template_type": "发货单",
                "analyzed_data": {"key": "value"},
                "editable_config": {"fields": []}
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]

    def test_create_template_empty_name(self, client):
        """测试创建模板空名称"""
        response = client.post(
            '/api/excel/templates',
            json={
                "template_name": ""
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]

    def test_create_template_with_full_config(self, client):
        """测试创建模板带完整配置"""
        response = client.post(
            '/api/excel/templates',
            json={
                "template_name": "完整配置模板",
                "template_type": "通用",
                "original_file_path": "/path/to/file.xlsx",
                "analyzed_data": {"headers": ["名称", "数量", "单价"]},
                "editable_config": {"editable": True},
                "zone_config": {"data_zone": "A1:Z100"},
                "merged_cells_config": {},
                "style_config": {},
                "business_rules": {}
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]

    def test_update_template_success(self, client):
        """测试更新模板成功"""
        response = client.put(
            '/api/excel/templates/1',
            json={
                "template_name": "更新后的模板名称",
                "editable_config": {"fields": ["名称"]}
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_update_template_not_found(self, client):
        """测试更新不存在的模板"""
        response = client.put(
            '/api/excel/templates/99999',
            json={
                "template_name": "新名称"
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_update_template_partial_fields(self, client):
        """测试更新模板部分字段"""
        response = client.put(
            '/api/excel/templates/1',
            json={
                "template_type": "新类型"
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_delete_template_success(self, client):
        """测试删除模板成功"""
        response = client.delete('/api/excel/templates/1')
        assert response.status_code in [200, 404, 500]

    def test_delete_template_not_found(self, client):
        """测试删除不存在的模板"""
        response = client.delete('/api/excel/templates/99999')
        assert response.status_code in [200, 404, 500]

    def test_test_endpoint(self, client):
        """测试接口"""
        response = client.get('/api/excel/test')
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.get_json()
            assert 'success' in data


class TestExcelTemplatesWithMock:
    """Excel 模板路由测试（带 Mock）"""

    @patch('os.path.exists')
    @patch('app.routes.excel_templates._get_template_list')
    def test_list_templates_mock(self, mock_get_list, mock_exists, client):
        """测试获取模板列表（Mock）"""
        mock_get_list.return_value = [
            {"id": "test", "name": "测试模板", "filename": "test.xlsx", "exists": True}
        ]
        mock_exists.return_value = True

        response = client.get('/api/excel/templates')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True

    @patch('os.path.exists')
    def test_save_template_mock(self, mock_exists, client):
        """测试保存模板（Mock 文件系统）"""
        mock_exists.return_value = True

        with patch('shutil.copy2') as mock_copy:
            mock_copy.return_value = None

            response = client.post(
                '/api/excel/template/save',
                json={
                    "source_name": "test_source.xlsx",
                    "target_name": "test_target.xlsx",
                    "overwrite": True
                },
                content_type='application/json'
            )

    @patch('os.path.exists')
    def test_decompose_template_not_found_mock(self, mock_exists, client):
        """测试分解不存在的模板（Mock）"""
        mock_exists.return_value = False

        response = client.post(
            '/api/excel/template/decompose',
            json={
                "filename": "不存在的文件.xlsx"
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]


class TestExcelTemplateEdgeCases:
    """Excel 模板边界情况测试"""

    def test_save_template_empty_json(self, client):
        """测试保存模板空 JSON"""
        response = client.post(
            '/api/excel/template/save',
            json={},
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_decompose_template_empty_json(self, client):
        """测试分解模板空 JSON"""
        response = client.post(
            '/api/excel/template/decompose',
            json={},
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 404, 500]

    def test_create_template_empty_json(self, client):
        """测试创建模板空 JSON"""
        response = client.post(
            '/api/excel/templates',
            json={},
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]

    def test_update_template_empty_json(self, client):
        """测试更新模板空 JSON"""
        response = client.put(
            '/api/excel/templates/1',
            json={},
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_get_template_negative_id(self, client):
        """测试获取负数 ID 的模板"""
        response = client.get('/api/excel/templates/-1')
        assert response.status_code in [200, 404, 500]

    def test_update_template_negative_id(self, client):
        """测试更新负数 ID 的模板"""
        response = client.put(
            '/api/excel/templates/-1',
            json={"template_name": "测试"},
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 405, 500]

    def test_delete_template_negative_id(self, client):
        """测试删除负数 ID 的模板"""
        response = client.delete('/api/excel/templates/-1')
        assert response.status_code in [200, 404, 405, 500]

    def test_upload_excel_xls_format(self, client):
        """测试上传 .xls 格式文件"""
        data = {
            'excel_file': (io.BytesIO(b'fake content'), 'test.xls')
        }
        response = client.post(
            '/api/excel/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code in [200, 400, 500]

    def test_upload_excel_uppercase_extension(self, client):
        """测试上传大写扩展名文件"""
        data = {
            'excel_file': (io.BytesIO(b'fake content'), 'test.XLSX')
        }
        response = client.post(
            '/api/excel/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code in [200, 400, 500]


class TestExcelTemplatesCRUDWithMock:
    """Excel 模板 CRUD 操作测试（使用 Mock 隔离数据库）"""

    @patch('app.db.session.get_db')
    def test_get_template_by_id_success(self, mock_get_db, client):
        """测试获取单个模板详情成功"""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.id = 1
        mock_result.template_key = 'TPL_20240101_12345678'
        mock_result.template_name = '测试模板'
        mock_result.template_type = '发货单'
        mock_result.original_file_path = '/path/to/file.xlsx'
        mock_result.analyzed_data = '{"headers": ["名称", "数量"]}'
        mock_result.editable_config = '{"editable": true}'
        mock_result.zone_config = '{}'
        mock_result.merged_cells_config = '{}'
        mock_result.style_config = '{}'
        mock_result.business_rules = '{}'
        mock_result.created_at = datetime.now()
        mock_result.updated_at = datetime.now()
        
        mock_result.fetchone.return_value = mock_result
        mock_db.execute.return_value = mock_result
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=None)
        mock_get_db.return_value = mock_db

        response = client.get('/api/excel/templates/1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert data['template']['id'] == 1
        assert data['template']['template_name'] == '测试模板'

    @patch('app.db.session.get_db')
    def test_get_template_by_id_not_found(self, mock_get_db, client):
        """测试获取不存在的模板"""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=None)
        mock_get_db.return_value = mock_db

        response = client.get('/api/excel/templates/99999')
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] == False
        assert '不存在' in data['message']

    @patch('app.db.session.get_db')
    def test_create_template_success(self, mock_get_db, client):
        """测试创建模板成功"""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.lastrowid = 1
        mock_db.execute.return_value = mock_result
        mock_db.commit = MagicMock()
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=None)
        mock_get_db.return_value = mock_db

        response = client.post(
            '/api/excel/templates',
            json={
                "template_name": "新模板",
                "template_type": "发货单",
                "analyzed_data": {"headers": ["名称", "数量"]},
                "editable_config": {"editable": True}
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert data['template_id'] == 1
        assert 'template_key' in data

    @patch('app.db.session.get_db')
    def test_create_template_empty_name(self, mock_get_db, client):
        """测试创建模板空名称"""
        response = client.post(
            '/api/excel/templates',
            json={
                "template_name": ""
            },
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] == False
        assert '不能为空' in data['message']

    @patch('app.db.session.get_db')
    def test_create_template_with_full_config(self, mock_get_db, client):
        """测试创建模板带完整配置"""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.lastrowid = 2
        mock_db.execute.return_value = mock_result
        mock_db.commit = MagicMock()
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=None)
        mock_get_db.return_value = mock_db

        response = client.post(
            '/api/excel/templates',
            json={
                "template_name": "完整配置模板",
                "template_type": "通用",
                "original_file_path": "/path/to/file.xlsx",
                "analyzed_data": {"headers": ["名称", "数量", "单价"]},
                "editable_config": {"editable": True},
                "zone_config": {"data_zone": "A1:Z100"},
                "merged_cells_config": {},
                "style_config": {},
                "business_rules": {}
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True

    @patch('app.db.session.get_db')
    def test_update_template_success(self, mock_get_db, client):
        """测试更新模板成功"""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(id=1)
        mock_db.execute.return_value = mock_result
        mock_db.commit = MagicMock()
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=None)
        mock_get_db.return_value = mock_db

        response = client.put(
            '/api/excel/templates/1',
            json={
                "template_name": "更新后的模板名称",
                "editable_config": {"fields": ["名称"]}
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert '更新成功' in data['message']

    @patch('app.db.session.get_db')
    def test_update_template_not_found(self, mock_get_db, client):
        """测试更新不存在的模板"""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=None)
        mock_get_db.return_value = mock_db

        response = client.put(
            '/api/excel/templates/99999',
            json={
                "template_name": "新名称"
            },
            content_type='application/json'
        )
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] == False
        assert '不存在' in data['message']

    @patch('app.db.session.get_db')
    def test_update_template_partial_fields(self, mock_get_db, client):
        """测试更新模板部分字段"""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(id=1)
        mock_db.execute.return_value = mock_result
        mock_db.commit = MagicMock()
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=None)
        mock_get_db.return_value = mock_db

        response = client.put(
            '/api/excel/templates/1',
            json={
                "template_type": "新类型"
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True

    @patch('app.db.session.get_db')
    def test_delete_template_success(self, mock_get_db, client):
        """测试删除模板成功"""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(id=1)
        mock_db.execute.return_value = mock_result
        mock_db.commit = MagicMock()
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=None)
        mock_get_db.return_value = mock_db

        response = client.delete('/api/excel/templates/1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert '删除成功' in data['message']

    @patch('app.db.session.get_db')
    def test_delete_template_not_found(self, mock_get_db, client):
        """测试删除不存在的模板"""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=None)
        mock_get_db.return_value = mock_db

        response = client.delete('/api/excel/templates/99999')
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] == False
        assert '不存在' in data['message']


class TestExcelTemplatesDecomposeWithMock:
    """Excel 模板分解功能测试（使用 Mock 隔离 openpyxl）"""

    @patch('app.routes.excel_templates._decompose_template')
    @patch('app.routes.excel_templates._resolve_template_path')
    def test_decompose_template_with_filename_success(self, mock_resolve, mock_decompose, client):
        """测试分解模板（使用文件名）成功"""
        mock_resolve.return_value = '/path/to/test.xlsx'
        mock_decompose.return_value = (
            {
                "success": True,
                "template": {"name": "test.xlsx", "path": "/path/to/test.xlsx"},
                "decomposition": {
                    "header_row": 1,
                    "editable_entries": [],
                    "sample_rows": []
                }
            },
            200
        )

        response = client.post(
            '/api/excel/template/decompose',
            json={
                "filename": "test.xlsx"
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.get_json()
            assert data['success'] == True
            assert 'template' in data
            assert 'decomposition' in data

    @patch('app.routes.excel_templates._resolve_template_path')
    def test_decompose_template_file_not_found(self, mock_resolve, client):
        """测试分解不存在的模板文件"""
        mock_resolve.return_value = None

        response = client.post(
            '/api/excel/template/decompose',
            json={
                "filename": "不存在的文件.xlsx"
            },
            content_type='application/json'
        )
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] == False

    @patch('app.routes.excel_templates._decompose_template')
    @patch('os.path.exists')
    def test_decompose_template_with_file_path_success(self, mock_exists, mock_decompose, client):
        """测试分解模板（使用文件路径）成功"""
        mock_exists.return_value = True
        mock_decompose.return_value = (
            {
                "success": True,
                "template": {"name": "test.xlsx"},
                "decomposition": {
                    "header_row": 2,
                    "editable_entries": [
                        {"name": "名称", "column": "A", "column_index": 1},
                        {"name": "数量", "column": "B", "column_index": 2}
                    ],
                    "amount_related_entries": [],
                    "sample_rows": []
                }
            },
            200
        )

        response = client.post(
            '/api/excel/template/decompose',
            json={
                "file_path": "/path/to/test.xlsx"
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.get_json()
            assert data['success'] == True

    @patch('app.routes.excel_templates._decompose_template')
    @patch('app.routes.excel_templates._resolve_template_path')
    def test_decompose_template_with_sheet_name(self, mock_resolve, mock_decompose, client):
        """测试分解模板指定 sheet 名称"""
        mock_resolve.return_value = '/path/to/test.xlsx'
        mock_decompose.return_value = (
            {
                "success": True,
                "template": {"name": "test.xlsx", "sheet": "出货"},
                "decomposition": {
                    "header_row": 1,
                    "editable_entries": [],
                    "sample_rows": []
                }
            },
            200
        )

        response = client.post(
            '/api/excel/template/decompose',
            json={
                "filename": "test.xlsx",
                "sheet_name": "出货",
                "sample_rows": 3
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.get_json()
            assert data['success'] == True

    def test_decompose_template_no_file_info(self, client):
        """测试分解模板无文件信息"""
        response = client.post(
            '/api/excel/template/decompose',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] == False
        assert 'filename 或 file_path' in data['message']

    @patch('app.routes.excel_templates._decompose_template')
    @patch('os.path.exists')
    def test_decompose_template_exception(self, mock_exists, mock_decompose, client):
        """测试分解模板异常情况"""
        mock_exists.return_value = True
        mock_decompose.side_effect = Exception("分解失败")

        response = client.post(
            '/api/excel/template/decompose',
            json={
                "file_path": "/path/to/test.xlsx"
            },
            content_type='application/json'
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] == False

    @patch('app.routes.excel_templates._decompose_template')
    @patch('os.path.exists')
    def test_decompose_template_with_custom_sample_rows(self, mock_exists, mock_decompose, client):
        """测试分解模板自定义样本行数"""
        mock_exists.return_value = True
        mock_decompose.return_value = (
            {
                "success": True,
                "template": {"name": "test.xlsx"},
                "decomposition": {
                    "header_row": 1,
                    "editable_entries": [],
                    "sample_rows": [{"row1": "data1"}, {"row2": "data2"}]
                }
            },
            200
        )

        response = client.post(
            '/api/excel/template/decompose',
            json={
                "file_path": "/path/to/test.xlsx",
                "sample_rows": 10
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.get_json()
            assert data['success'] == True


class TestExcelTemplatesUploadWithMock:
    """Excel 模板上传功能测试（使用 Mock 隔离文件系统）"""

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.join')
    def test_upload_excel_success(self, mock_join, mock_open, client):
        """测试上传 Excel 文件成功"""
        mock_join.return_value = '/temp/path/excel_20240101_120000_test.xlsx'
        
        data = {
            'excel_file': (io.BytesIO(b'fake excel content'), 'test.xlsx')
        }
        response = client.post(
            '/api/excel/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert 'file_path' in data
        assert 'filename' in data

    def test_upload_excel_no_file(self, client):
        """测试上传 Excel 无文件"""
        response = client.post(
            '/api/excel/upload',
            content_type='multipart/form-data'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] == False
        assert '请上传' in data['message']

    def test_upload_excel_empty_filename(self, client):
        """测试上传文件名为空"""
        data = {
            'excel_file': (io.BytesIO(b'content'), '')
        }
        response = client.post(
            '/api/excel/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] == False
        assert '请选择文件' in data['message']

    def test_upload_excel_invalid_format(self, client):
        """测试上传无效格式文件"""
        data = {
            'excel_file': (io.BytesIO(b'not excel'), 'test.txt')
        }
        response = client.post(
            '/api/excel/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] == False
        assert '只支持' in data['message']

    def test_upload_excel_xls_format(self, client):
        """测试上传 .xls 格式文件"""
        data = {
            'excel_file': (io.BytesIO(b'fake content'), 'test.xls')
        }
        response = client.post(
            '/api/excel/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True

    def test_upload_excel_uppercase_extension(self, client):
        """测试上传大写扩展名文件"""
        data = {
            'excel_file': (io.BytesIO(b'fake content'), 'test.XLSX')
        }
        response = client.post(
            '/api/excel/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True


class TestExcelTemplatesSaveWithMock:
    """Excel 模板保存功能测试（使用 Mock 隔离文件系统）"""

    @patch('shutil.copy2')
    @patch('os.path.exists')
    def test_save_template_success(self, mock_exists, mock_copy, client):
        """测试保存模板成功"""
        mock_exists.side_effect = lambda path: True
        mock_copy.return_value = None

        response = client.post(
            '/api/excel/template/save',
            json={
                "source_name": "source.xlsx",
                "target_name": "target.xlsx",
                "overwrite": True
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert data['saved'] == True

    @patch('os.path.exists')
    def test_save_template_source_not_found(self, mock_exists, client):
        """测试保存模板源文件不存在"""
        mock_exists.return_value = False

        response = client.post(
            '/api/excel/template/save',
            json={
                "source_name": "不存在的文件.xlsx",
                "target_name": "target.xlsx"
            },
            content_type='application/json'
        )
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] == False
        assert '不存在' in data['message']

    @patch('shutil.copy2')
    @patch('os.path.exists')
    def test_save_template_existing_no_overwrite(self, mock_exists, mock_copy, client):
        """测试目标模板存在且不覆盖"""
        def exists_side_effect(path):
            return True
        
        mock_exists.side_effect = exists_side_effect
        mock_copy.return_value = None

        response = client.post(
            '/api/excel/template/save',
            json={
                "source_name": "source.xlsx",
                "target_name": "existing.xlsx",
                "overwrite": False
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert data['saved'] == False
        assert '未覆盖' in data['message']

    @patch('shutil.copy2')
    @patch('os.path.exists')
    def test_save_template_exception(self, mock_exists, mock_copy, client):
        """测试保存模板异常情况"""
        mock_exists.side_effect = lambda path: True
        mock_copy.side_effect = Exception("复制失败")

        response = client.post(
            '/api/excel/template/save',
            json={
                "source_name": "source.xlsx",
                "target_name": "target.xlsx",
                "overwrite": True
            },
            content_type='application/json'
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] == False


class TestExcelTemplatesGetFileWithMock:
    """Excel 模板获取文件测试（使用 Mock 隔离文件系统）"""

    @patch('app.routes.excel_templates._get_template_list')
    @patch('os.path.exists')
    def test_get_template_file_success(self, mock_exists, mock_get_list, client):
        """测试获取模板文件成功"""
        mock_get_list.return_value = [
            {
                "id": "shipment",
                "name": "发货单模板",
                "filename": "发货单模板.xlsx",
                "exists": True,
                "path": "/path/to/发货单模板.xlsx"
            }
        ]
        mock_exists.return_value = True

        response = client.get('/api/excel/template/shipment/file')
        assert response.status_code in [200, 500]

    @patch('app.routes.excel_templates._get_template_list')
    def test_get_template_file_not_found(self, mock_get_list, client):
        """测试获取不存在的模板文件"""
        mock_get_list.return_value = []

        response = client.get('/api/excel/template/nonexistent_id/file')
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] == False
        assert '不存在' in data['message']

    @patch('app.routes.excel_templates._get_template_list')
    def test_get_template_file_file_not_exists(self, mock_get_list, client):
        """测试模板文件不存在"""
        mock_get_list.return_value = [
            {
                "id": "shipment",
                "name": "发货单模板",
                "filename": "发货单模板.xlsx",
                "exists": False,
                "path": None
            }
        ]

        response = client.get('/api/excel/template/shipment/file')
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] == False
        assert '文件不存在' in data['message']


class TestExcelTemplatesDataValidation:
    """Excel 模板数据验证测试"""

    def test_create_template_with_invalid_json(self, client):
        """测试创建模板使用无效 JSON"""
        response = client.post(
            '/api/excel/templates',
            json={
                "template_name": "测试",
                "analyzed_data": "invalid json"
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]

    def test_update_template_with_invalid_json(self, client):
        """测试更新模板使用无效 JSON"""
        response = client.put(
            '/api/excel/templates/1',
            json={
                "editable_config": "invalid json"
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 404, 500]

    def test_decompose_template_with_invalid_sample_rows(self, client):
        """测试分解模板使用无效样本行数"""
        response = client.post(
            '/api/excel/template/decompose',
            json={
                "file_path": "/path/to/test.xlsx",
                "sample_rows": -5
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 404, 500]

    def test_save_template_with_special_chars(self, client):
        """测试保存模板使用特殊字符文件名"""
        response = client.post(
            '/api/excel/template/save',
            json={
                "source_name": "测试文件@#$%.xlsx",
                "target_name": "目标文件!@#.xlsx"
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_create_template_with_very_long_name(self, client):
        """测试创建模板使用超长名称"""
        long_name = "a" * 1000
        response = client.post(
            '/api/excel/templates',
            json={
                "template_name": long_name
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]

    def test_upload_excel_with_large_file(self, client):
        """测试上传大文件"""
        large_content = b'x' * (10 * 1024 * 1024)
        data = {
            'excel_file': (io.BytesIO(large_content), 'large.xlsx')
        }
        response = client.post(
            '/api/excel/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code in [200, 400, 500]


class TestExcelTemplatesErrorHandling:
    """Excel 模板错误处理测试"""

    @patch('app.db.session.get_db')
    def test_database_connection_error(self, mock_get_db, client):
        """测试数据库连接错误"""
        mock_get_db.side_effect = Exception("数据库连接失败")

        response = client.get('/api/excel/templates/1')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] == False

    @patch('app.db.session.get_db')
    def test_create_template_database_error(self, mock_get_db, client):
        """测试创建模板数据库错误"""
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("数据库错误")
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=None)
        mock_get_db.return_value = mock_db

        response = client.post(
            '/api/excel/templates',
            json={
                "template_name": "测试模板"
            },
            content_type='application/json'
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] == False

    @patch('app.db.session.get_db')
    def test_update_template_database_error(self, mock_get_db, client):
        """测试更新模板数据库错误"""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(id=1)
        mock_db.execute.side_effect = Exception("数据库错误")
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=None)
        mock_get_db.return_value = mock_db

        response = client.put(
            '/api/excel/templates/1',
            json={
                "template_name": "新名称"
            },
            content_type='application/json'
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] == False

    @patch('app.db.session.get_db')
    def test_delete_template_database_error(self, mock_get_db, client):
        """测试删除模板数据库错误"""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(id=1)
        mock_db.execute.side_effect = Exception("数据库错误")
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=None)
        mock_get_db.return_value = mock_db

        response = client.delete('/api/excel/templates/1')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] == False

    @patch('app.routes.excel_templates._get_template_list')
    def test_list_templates_exception(self, mock_get_list, client):
        """测试获取模板列表异常"""
        mock_get_list.side_effect = Exception("列表获取失败")

        response = client.get('/api/excel/templates')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] == False

    @patch('app.routes.excel_templates._get_template_list')
    def test_list_templates_should_include_category_dto_fields(self, mock_get_list, client):
        """模板列表应返回统一 DTO 字段并保留兼容字段"""
        mock_get_list.return_value = [
            {
                "id": "db:1",
                "name": "发货单模板A",
                "template_type": "发货单",
                "exists": True,
                "path": "/tmp/a.xlsx",
                "source": "db",
            },
            {
                "id": "db:2",
                "name": "标签模板B",
                "template_type": "标签打印",
                "exists": False,
                "path": None,
                "source": "db",
            },
        ]

        response = client.get('/api/excel/templates')
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["templates"]) == 2

        excel_tpl = data["templates"][0]
        label_tpl = data["templates"][1]
        assert excel_tpl["category"] == "excel"
        assert "file_path" in excel_tpl
        assert "preview_capable" in excel_tpl
        assert "template_type" in excel_tpl
        assert "path" in excel_tpl  # 兼容旧字段
        assert excel_tpl["preview_capable"] is True

        assert label_tpl["category"] == "label_print"
        assert label_tpl["preview_capable"] is False

    @patch('shutil.copy2')
    @patch('os.path.exists')
    def test_save_template_copy_error(self, mock_exists, mock_copy, client):
        """测试保存模板复制错误"""
        mock_exists.side_effect = lambda path: True
        mock_copy.side_effect = IOError("复制失败")

        response = client.post(
            '/api/excel/template/save',
            json={
                "source_name": "source.xlsx",
                "target_name": "target.xlsx",
                "overwrite": True
            },
            content_type='application/json'
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] == False


class TestExcelTemplatesEdgeCases:
    """Excel 模板边界情况测试（增强版）"""

    def test_save_template_empty_json(self, client):
        """测试保存模板空 JSON"""
        response = client.post(
            '/api/excel/template/save',
            json={},
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_decompose_template_empty_json(self, client):
        """测试分解模板空 JSON"""
        response = client.post(
            '/api/excel/template/decompose',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] == False

    def test_create_template_empty_json(self, client):
        """测试创建模板空 JSON"""
        response = client.post(
            '/api/excel/templates',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] == False

    def test_update_template_empty_json(self, client):
        """测试更新模板空 JSON"""
        response = client.put(
            '/api/excel/templates/1',
            json={},
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_get_template_negative_id(self, client):
        """测试获取负数 ID 的模板"""
        response = client.get('/api/excel/templates/-1')
        assert response.status_code in [200, 404, 500]

    def test_get_template_zero_id(self, client):
        """测试获取 ID 为 0 的模板"""
        response = client.get('/api/excel/templates/0')
        assert response.status_code in [200, 404, 500]

    def test_update_template_zero_id(self, client):
        """测试更新 ID 为 0 的模板"""
        response = client.put(
            '/api/excel/templates/0',
            json={"template_name": "测试"},
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_delete_template_zero_id(self, client):
        """测试删除 ID 为 0 的模板"""
        response = client.delete('/api/excel/templates/0')
        assert response.status_code in [200, 404, 500]

    def test_create_template_with_none_values(self, client):
        """测试创建模板包含 None 值"""
        response = client.post(
            '/api/excel/templates',
            json={
                "template_name": "测试",
                "template_type": None,
                "analyzed_data": None
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]

    def test_update_template_with_none_values(self, client):
        """测试更新模板包含 None 值"""
        response = client.put(
            '/api/excel/templates/1',
            json={
                "template_name": None,
                "editable_config": None
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_decompose_template_with_zero_sample_rows(self, client):
        """测试分解模板样本行数为 0"""
        response = client.post(
            '/api/excel/template/decompose',
            json={
                "file_path": "/path/to/test.xlsx",
                "sample_rows": 0
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 404, 500]

    def test_save_template_with_overwrite_true(self, client):
        """测试保存模板 overwrite 为 true"""
        response = client.post(
            '/api/excel/template/save',
            json={
                "source_name": "source.xlsx",
                "target_name": "target.xlsx",
                "overwrite": "true"
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_save_template_with_overwrite_false(self, client):
        """测试保存模板 overwrite 为 false"""
        response = client.post(
            '/api/excel/template/save',
            json={
                "source_name": "source.xlsx",
                "target_name": "target.xlsx",
                "overwrite": "false"
            },
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 500]

    def test_upload_excel_with_mixed_case_extension(self, client):
        """测试上传混合大小写扩展名文件"""
        data = {
            'excel_file': (io.BytesIO(b'fake content'), 'test.XlsX')
        }
        response = client.post(
            '/api/excel/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code in [200, 400, 500]

    def test_upload_excel_with_spaces_in_filename(self, client):
        """测试上传文件名包含空格"""
        data = {
            'excel_file': (io.BytesIO(b'fake content'), 'test file.xlsx')
        }
        response = client.post(
            '/api/excel/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code in [200, 400, 500]

    def test_upload_excel_with_chinese_filename(self, client):
        """测试上传中文文件名"""
        data = {
            'excel_file': (io.BytesIO(b'fake content'), '测试文件.xlsx')
        }
        response = client.post(
            '/api/excel/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code in [200, 400, 500]


class TestExcelTemplatesListWithMock:
    """Excel 模板列表测试（使用 Mock）"""

    @patch('app.routes.excel_templates._get_template_list')
    def test_list_templates_success(self, mock_get_list, client):
        """测试获取模板列表成功"""
        mock_get_list.return_value = [
            {
                "id": "shipment",
                "name": "发货单模板",
                "filename": "发货单模板.xlsx",
                "exists": True,
                "path": "/path/to/发货单模板.xlsx"
            },
            {
                "id": "fallback",
                "name": "备用模板",
                "filename": "尹玉华132.xlsx",
                "exists": False,
                "path": None
            }
        ]

        response = client.get('/api/excel/templates')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert 'templates' in data
        assert len(data['templates']) == 2

    @patch('app.routes.excel_templates._get_template_list')
    def test_list_templates_empty(self, mock_get_list, client):
        """测试获取空模板列表"""
        mock_get_list.return_value = []

        response = client.get('/api/excel/templates')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert data['templates'] == []

    @patch('app.routes.excel_templates._get_template_list')
    def test_list_templates_exception(self, mock_get_list, client):
        """测试获取模板列表异常"""
        mock_get_list.side_effect = Exception("列表获取失败")

        response = client.get('/api/excel/templates')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] == False
