"""
客户管理路由测试
"""

import pytest
import json
import os
import tempfile
import sys
from unittest.mock import Mock, patch, MagicMock, create_autospec
from io import BytesIO


class TestCustomersImport:
    """客户导入接口测试"""

    @patch('app.routes.customers.import_customers_from_excel', create=True)
    def test_import_get_success(self, mock_import, client):
        """测试 GET 请求 - 返回接口说明"""
        response = client.get('/api/customers/import')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert '导入接口' in data['message']
        mock_import.assert_not_called()

    @patch('app.routes.customers.import_customers_from_excel', create=True)
    def test_import_post_no_file(self, mock_import, client):
        """测试 POST 请求 - 未选择文件"""
        response = client.post('/api/customers/import')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert '未选择文件' in data['message']
        mock_import.assert_not_called()

    @patch('app.routes.customers.import_customers_from_excel', create=True)
    def test_import_post_empty_filename(self, mock_import, client):
        """测试 POST 请求 - 文件名为空"""
        data = {
            'file': (BytesIO(b''), '')
        }
        response = client.post('/api/customers/import', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert '未选择文件' in data['message']
        mock_import.assert_not_called()

    @patch('app.routes.customers.import_customers_from_excel', create=True)
    def test_import_post_success(self, mock_import, client):
        """测试 POST 请求 - 导入成功"""
        mock_import.return_value = (
            True,
            {
                'success': True,
                'message': '导入成功',
                'updated': 5,
                'inserted': 10,
                'skipped': 2
            },
            200
        )
        
        data = {
            'file': (BytesIO(b'fake excel content'), 'test.xlsx')
        }
        response = client.post('/api/customers/import', data=data, content_type='multipart/form-data')
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert result['updated'] == 5
        assert result['inserted'] == 10
        assert result['skipped'] == 2
        mock_import.assert_called_once()

    @patch('app.routes.customers.import_customers_from_excel', create=True)
    def test_import_post_with_excel_file_field(self, mock_import, client):
        """测试 POST 请求 - 使用 excel_file 字段"""
        mock_import.return_value = (
            True,
            {
                'success': True,
                'message': '导入成功',
                'updated': 0,
                'inserted': 3,
                'skipped': 0
            },
            200
        )
        
        data = {
            'excel_file': (BytesIO(b'fake excel content'), 'test.xlsx')
        }
        response = client.post('/api/customers/import', data=data, content_type='multipart/form-data')
        assert response.status_code == 200
        mock_import.assert_called_once()

    @patch('app.routes.customers.import_customers_from_excel', create=True)
    def test_import_post_service_error(self, mock_import, client):
        """测试 POST 请求 - 服务层返回错误"""
        mock_import.return_value = (
            False,
            {
                'success': False,
                'message': 'Excel 格式错误'
            },
            400
        )
        
        data = {
            'file': (BytesIO(b'fake excel content'), 'test.xlsx')
        }
        response = client.post('/api/customers/import', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        assert 'Excel 格式错误' in result['message']

    @patch('app.routes.customers.import_customers_from_excel', create=True)
    def test_import_post_service_exception(self, mock_import, client):
        """测试 POST 请求 - 服务层抛出异常"""
        mock_import.side_effect = Exception('数据库连接失败')
        
        data = {
            'file': (BytesIO(b'fake excel content'), 'test.xlsx')
        }
        try:
            response = client.post('/api/customers/import', data=data, content_type='multipart/form-data')
            assert response.status_code == 500
        except Exception as e:
            assert '数据库连接失败' in str(e)


class TestCustomersExport:
    """客户导出接口测试"""

    @patch('app.routes.customers.export_customers_to_excel', create=True)
    @patch('os.path.exists')
    @patch('app.routes.customers.send_file')
    def test_export_success(self, mock_send_file, mock_exists, mock_export, client):
        """测试导出成功"""
        mock_export.return_value = (
            True,
            {
                'file_path': '/tmp/customers_export.xlsx',
                'filename': '购买单位导出.xlsx'
            },
            200
        )
        mock_exists.return_value = True
        mock_send_file.return_value = 'file content'
        
        response = client.get('/api/customers/export')
        mock_send_file.assert_called_once()
        mock_export.assert_called_once_with(keyword=None)

    @patch('app.routes.customers.export_customers_to_excel', create=True)
    def test_export_with_keyword(self, mock_export, client):
        """测试带关键词的导出"""
        mock_export.return_value = (
            True,
            {
                'file_path': '/tmp/customers_export.xlsx',
                'filename': '购买单位导出.xlsx'
            },
            200
        )
        
        with patch('os.path.exists', return_value=True), \
             patch('app.routes.customers.send_file', return_value='file content'):
            response = client.get('/api/customers/export?keyword=测试')
            mock_export.assert_called_once_with(keyword='测试')

    @patch('app.routes.customers.export_customers_to_excel', create=True)
    def test_export_service_error(self, mock_export, client):
        """测试导出服务层错误"""
        mock_export.return_value = (
            False,
            {
                'success': False,
                'message': '导出失败：没有数据'
            },
            400
        )
        
        response = client.get('/api/customers/export')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert '没有数据' in data['message']

    @patch('app.routes.customers.export_customers_to_excel', create=True)
    @patch('os.path.exists')
    def test_export_file_not_exists(self, mock_exists, mock_export, client):
        """测试导出文件不存在"""
        mock_export.return_value = (
            True,
            {
                'file_path': '/tmp/customers_export.xlsx',
                'filename': '购买单位导出.xlsx'
            },
            200
        )
        mock_exists.return_value = False
        
        response = client.get('/api/customers/export')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert '文件不存在' in data['message']

    @patch('app.routes.customers.export_customers_to_excel', create=True)
    def test_export_exception(self, mock_export, client):
        """测试导出异常"""
        mock_export.side_effect = Exception('文件系统错误')
        
        response = client.get('/api/customers/export')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert '导出失败' in data['message']


class TestCustomersList:
    """客户列表接口测试"""

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_list_default_params(self, mock_get_all, client):
        """测试默认参数获取列表"""
        mock_get_all.return_value = {
            'success': True,
            'data': [],
            'total': 0,
            'page': 1,
            'per_page': 20
        }
        
        response = client.get('/api/customers/list')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        mock_get_all.assert_called_once_with(keyword=None, page=1, per_page=20)

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_list_with_keyword(self, mock_get_all, client):
        """测试带关键词搜索"""
        mock_get_all.return_value = {
            'success': True,
            'data': [
                {'id': 1, 'unit_name': '测试公司A'},
                {'id': 2, 'unit_name': '测试公司B'}
            ],
            'total': 2,
            'page': 1,
            'per_page': 20
        }
        
        response = client.get('/api/customers/list?keyword=测试')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']) == 2
        mock_get_all.assert_called_once_with(keyword='测试', page=1, per_page=20)

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_list_with_pagination(self, mock_get_all, client):
        """测试分页参数"""
        mock_get_all.return_value = {
            'success': True,
            'data': [],
            'total': 0,
            'page': 2,
            'per_page': 50
        }
        
        response = client.get('/api/customers/list?page=2&per_page=50')
        assert response.status_code == 200
        data = response.get_json()
        assert data['page'] == 2
        assert data['per_page'] == 50
        mock_get_all.assert_called_once_with(keyword=None, page=2, per_page=50)

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_list_all_params(self, mock_get_all, client):
        """测试所有参数组合"""
        mock_get_all.return_value = {
            'success': True,
            'data': [],
            'total': 0,
            'page': 3,
            'per_page': 30
        }
        
        response = client.get('/api/customers/list?keyword=公司&page=3&per_page=30')
        assert response.status_code == 200
        mock_get_all.assert_called_once_with(keyword='公司', page=3, per_page=30)

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_list_invalid_page(self, mock_get_all, client):
        """测试无效页码"""
        mock_get_all.return_value = {
            'success': True,
            'data': [],
            'total': 0,
            'page': 0,
            'per_page': 20
        }
        
        response = client.get('/api/customers/list?page=abc')
        assert response.status_code == 500

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_list_invalid_per_page(self, mock_get_all, client):
        """测试无效每页数量"""
        mock_get_all.return_value = {
            'success': True,
            'data': [],
            'total': 0,
            'page': 1,
            'per_page': 0
        }
        
        response = client.get('/api/customers/list?per_page=xyz')
        assert response.status_code == 500

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_list_negative_page(self, mock_get_all, client):
        """测试负页码"""
        mock_get_all.return_value = {
            'success': True,
            'data': [],
            'total': 0,
            'page': -1,
            'per_page': 20
        }
        
        response = client.get('/api/customers/list?page=-1')
        assert response.status_code == 200

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_list_zero_per_page(self, mock_get_all, client):
        """测试每页数量为0"""
        mock_get_all.return_value = {
            'success': True,
            'data': [],
            'total': 0,
            'page': 1,
            'per_page': 0
        }
        
        response = client.get('/api/customers/list?per_page=0')
        assert response.status_code == 200

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_list_large_per_page(self, mock_get_all, client):
        """测试大每页数量"""
        mock_get_all.return_value = {
            'success': True,
            'data': [],
            'total': 0,
            'page': 1,
            'per_page': 1000
        }
        
        response = client.get('/api/customers/list?per_page=1000')
        assert response.status_code == 200

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_list_service_exception(self, mock_get_all, client):
        """测试服务层异常"""
        mock_get_all.side_effect = Exception('数据库查询失败')
        
        response = client.get('/api/customers/list')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert '查询失败' in data['message']


class TestCustomersEdgeCases:
    """边界条件测试"""

    @patch('app.routes.customers.import_customers_from_excel', create=True)
    def test_import_empty_file(self, mock_import, client):
        """测试导入空文件"""
        mock_import.return_value = (
            True,
            {
                'success': True,
                'message': '导入成功',
                'updated': 0,
                'inserted': 0,
                'skipped': 0
            },
            200
        )
        
        data = {
            'file': (BytesIO(b''), 'empty.xlsx')
        }
        response = client.post('/api/customers/import', data=data, content_type='multipart/form-data')
        assert response.status_code == 200

    @patch('app.routes.customers.export_customers_to_excel', create=True)
    def test_export_empty_keyword(self, mock_export, client):
        """测试空关键词导出"""
        mock_export.return_value = (
            True,
            {
                'file_path': '/tmp/customers_export.xlsx',
                'filename': '购买单位导出.xlsx'
            },
            200
        )
        
        with patch('os.path.exists', return_value=True), \
             patch('app.routes.customers.send_file', return_value='file content'):
            response = client.get('/api/customers/export?keyword=')
            assert response.status_code == 200

    @patch('app.routes.customers.export_customers_to_excel', create=True)
    def test_export_special_keyword(self, mock_export, client):
        """测试特殊字符关键词"""
        mock_export.return_value = (
            True,
            {
                'file_path': '/tmp/customers_export.xlsx',
                'filename': '购买单位导出.xlsx'
            },
            200
        )
        
        with patch('os.path.exists', return_value=True), \
             patch('app.routes.customers.send_file', return_value='file content'):
            response = client.get('/api/customers/export?keyword=%E6%B5%8B%E8%AF%95%20%E5%85%AC%E5%8F%B8')
            assert response.status_code == 200

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_list_empty_keyword(self, mock_get_all, client):
        """测试空关键词列表"""
        mock_get_all.return_value = {
            'success': True,
            'data': [],
            'total': 0,
            'page': 1,
            'per_page': 20
        }
        
        response = client.get('/api/customers/list?keyword=')
        assert response.status_code == 200

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_list_large_page_number(self, mock_get_all, client):
        """测试超大页码"""
        mock_get_all.return_value = {
            'success': True,
            'data': [],
            'total': 0,
            'page': 99999,
            'per_page': 20
        }
        
        response = client.get('/api/customers/list?page=99999')
        assert response.status_code == 200


class TestCustomersBusinessFlow:
    """完整业务流程测试"""

    @patch('app.routes.customers.get_all_customers', create=True)
    @patch('app.routes.customers.export_customers_to_excel', create=True)
    @patch('os.path.exists')
    @patch('app.routes.customers.send_file')
    def test_complete_export_flow(self, mock_send_file, mock_exists, mock_export, mock_get_all, client):
        """测试完整导出流程"""
        mock_get_all.return_value = {
            'success': True,
            'data': [
                {'id': 1, 'unit_name': '公司A'},
                {'id': 2, 'unit_name': '公司B'}
            ],
            'total': 2,
            'page': 1,
            'per_page': 20
        }
        
        mock_export.return_value = (
            True,
            {
                'file_path': '/tmp/export.xlsx',
                'filename': '导出.xlsx'
            },
            200
        )
        mock_exists.return_value = True
        mock_send_file.return_value = 'file content'
        
        response = client.get('/api/customers/export?keyword=公司')
        assert response.status_code == 200

    @patch('app.routes.customers.import_customers_from_excel', create=True)
    @patch('app.routes.customers.get_all_customers', create=True)
    def test_import_then_list_flow(self, mock_get_all, mock_import, client):
        """测试导入后查看列表流程"""
        mock_import.return_value = (
            True,
            {
                'success': True,
                'message': '导入成功',
                'updated': 0,
                'inserted': 5,
                'skipped': 0
            },
            200
        )
        
        mock_get_all.return_value = {
            'success': True,
            'data': [
                {'id': 1, 'unit_name': '公司A'},
                {'id': 2, 'unit_name': '公司B'}
            ],
            'total': 2,
            'page': 1,
            'per_page': 20
        }
        
        data = {
            'file': (BytesIO(b'excel content'), 'test.xlsx')
        }
        
        import_response = client.post('/api/customers/import', data=data, content_type='multipart/form-data')
        assert import_response.status_code == 200
        
        list_response = client.get('/api/customers/list')
        assert list_response.status_code == 200


class TestCustomersDataValidation:
    """数据验证测试"""

    @patch('app.routes.customers.import_customers_from_excel', create=True)
    def test_import_validation_error(self, mock_import, client):
        """测试导入数据验证错误"""
        mock_import.return_value = (
            False,
            {
                'success': False,
                'message': '数据验证失败：缺少必填字段',
                'errors': [
                    {'row': 2, 'field': 'unit_name', 'message': '不能为空'}
                ]
            },
            400
        )
        
        data = {
            'file': (BytesIO(b'excel content'), 'test.xlsx')
        }
        response = client.post('/api/customers/import', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        result = response.get_json()
        assert '验证失败' in result['message']

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_list_invalid_keyword_type(self, mock_get_all, client):
        """测试无效关键词类型"""
        mock_get_all.return_value = {
            'success': True,
            'data': [],
            'total': 0,
            'page': 1,
            'per_page': 20
        }
        
        response = client.get('/api/customers/list?keyword=123')
        assert response.status_code == 200


class TestCustomersSearchAndFilter:
    """搜索和过滤功能测试"""

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_search_by_name(self, mock_get_all, client):
        """测试按名称搜索"""
        mock_get_all.return_value = {
            'success': True,
            'data': [
                {'id': 1, 'unit_name': '测试科技有限公司'}
            ],
            'total': 1,
            'page': 1,
            'per_page': 20
        }
        
        response = client.get('/api/customers/list?keyword=科技')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 1

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_search_no_results(self, mock_get_all, client):
        """测试无结果搜索"""
        mock_get_all.return_value = {
            'success': True,
            'data': [],
            'total': 0,
            'page': 1,
            'per_page': 20
        }
        
        response = client.get('/api/customers/list?keyword=不存在的公司')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 0

    @patch('app.routes.customers.export_customers_to_excel', create=True)
    @patch('os.path.exists')
    @patch('app.routes.customers.send_file')
    def test_export_with_filter(self, mock_send_file, mock_exists, mock_export, client):
        """测试带过滤条件的导出"""
        mock_export.return_value = (
            True,
            {
                'file_path': '/tmp/filtered_export.xlsx',
                'filename': '购买单位导出.xlsx'
            },
            200
        )
        mock_exists.return_value = True
        mock_send_file.return_value = 'file content'
        
        response = client.get('/api/customers/export?keyword=科技')
        assert response.status_code == 200


class TestCustomersErrorHandling:
    """错误处理测试"""

    @patch('app.routes.customers.import_customers_from_excel', create=True)
    def test_import_file_too_large(self, mock_import, client):
        """测试文件过大"""
        mock_import.return_value = (
            False,
            {
                'success': False,
                'message': '文件过大，最大支持 10MB'
            },
            400
        )
        
        large_content = b'x' * (11 * 1024 * 1024)
        data = {
            'file': (BytesIO(large_content), 'large.xlsx')
        }
        response = client.post('/api/customers/import', data=data, content_type='multipart/form-data')
        assert response.status_code == 400

    @patch('app.routes.customers.export_customers_to_excel', create=True)
    def test_export_no_data(self, mock_export, client):
        """测试导出无数据"""
        mock_export.return_value = (
            False,
            {
                'success': False,
                'message': '没有可导出的数据'
            },
            400
        )
        
        response = client.get('/api/customers/export')
        assert response.status_code == 400
        data = response.get_json()
        assert '没有可导出的数据' in data['message']

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_list_database_error(self, mock_get_all, client):
        """测试数据库错误"""
        mock_get_all.side_effect = Exception('数据库连接超时')
        
        response = client.get('/api/customers/list')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False


class TestCustomersLegacyRoutes:
    """兼容性测试"""

    @patch('app.routes.customers.get_all_customers', create=True)
    def test_api_customers_route(self, mock_get_all, client):
        """测试 /api/customers 路由（如果存在）"""
        mock_get_all.return_value = {
            'success': True,
            'data': [],
            'total': 0,
            'page': 1,
            'per_page': 20
        }
        
        response = client.get('/api/customers')
        assert response.status_code in [200, 404]
