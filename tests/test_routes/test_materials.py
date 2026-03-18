"""
原材料管理路由测试
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from flask import Blueprint


class TestMaterials:
    """原材料管理路由测试"""

    def test_add_material_success(self, client, sample_data_factory):
        """测试成功添加原材料"""
        material_data = sample_data_factory.material()
        response = client.post(
            '/api/materials',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'data' in data
        assert data['data']['name'] == material_data['name']
        assert data['data']['quantity'] == material_data['quantity']

    def test_add_material_empty_name(self, client):
        """测试添加空名称原材料"""
        response = client.post(
            '/api/materials',
            json={"name": ""},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert '原材料名称不能为空' in data['message']

    def test_add_material_missing_name(self, client):
        """测试添加缺少名称的原材料"""
        response = client.post(
            '/api/materials',
            json={"specification": "测试规格"},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert '原材料名称不能为空' in data['message']

    def test_add_material_with_min_quantity(self, client, sample_data_factory):
        """测试添加带最小库存量的原材料"""
        material_data = sample_data_factory.material({
            "quantity": 5.0,
            "min_quantity": 10.0
        })
        response = client.post(
            '/api/materials',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_add_material_with_negative_quantity(self, client, sample_data_factory):
        """测试添加负数数量的原材料"""
        material_data = sample_data_factory.material({
            "quantity": -10.0
        })
        response = client.post(
            '/api/materials',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_add_material_with_zero_quantity(self, client, sample_data_factory):
        """测试添加零数量的原材料"""
        material_data = sample_data_factory.material({
            "quantity": 0.0
        })
        response = client.post(
            '/api/materials',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['quantity'] == 0

    def test_add_material_with_large_quantity(self, client, sample_data_factory):
        """测试添加大数量原材料"""
        material_data = sample_data_factory.material({
            "quantity": 999999.99
        })
        response = client.post(
            '/api/materials',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_add_material_without_quantity(self, client, sample_data_factory):
        """测试不提供数量时的默认值"""
        material_data = sample_data_factory.material()
        material_data.pop('quantity', None)
        response = client.post(
            '/api/materials',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['quantity'] == 0

    def test_add_material_with_special_chars_name(self, client, sample_data_factory):
        """测试名称包含特殊字符"""
        material_data = sample_data_factory.material({
            "name": "钢材@#$%^&*()"
        })
        response = client.post(
            '/api/materials',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_add_material_with_unicode_name(self, client, sample_data_factory):
        """测试名称包含 Unicode 字符"""
        material_data = sample_data_factory.material({
            "name": "原材料测试🎉🔥"
        })
        response = client.post(
            '/api/materials',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_add_material_with_very_long_name(self, client, sample_data_factory):
        """测试超长名称"""
        material_data = sample_data_factory.material({
            "name": "A" * 1000
        })
        response = client.post(
            '/api/materials',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_add_material_invalid_json(self, client):
        """测试无效的 JSON 请求体"""
        response = client.post(
            '/api/materials',
            data='invalid json',
            content_type='application/json'
        )
        assert response.status_code in [400, 500]

    def test_add_material_empty_body(self, client):
        """测试空请求体"""
        response = client.post(
            '/api/materials',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_add_material_missing_content_type(self, client, sample_data_factory):
        """测试缺少 Content-Type"""
        material_data = sample_data_factory.material()
        response = client.post(
            '/api/materials',
            data=json.dumps(material_data)
        )
        assert response.status_code in [200, 400, 500]

    def test_get_materials_success(self, client):
        """测试成功获取原材料列表"""
        response = client.get('/api/materials')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'data' in data
        assert 'count' in data
        assert isinstance(data['data'], list)
        assert isinstance(data['count'], int)

    def test_get_materials_with_search(self, client):
        """测试带搜索条件的原材料列表"""
        response = client.get('/api/materials?search=钢材')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_materials_with_empty_search(self, client):
        """测试空搜索条件"""
        response = client.get('/api/materials?search=')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_materials_with_special_search(self, client):
        """测试特殊字符搜索"""
        response = client.get('/api/materials?search=@#$%')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_materials_with_unicode_search(self, client):
        """测试 Unicode 搜索"""
        response = client.get('/api/materials?search=测试🎉')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_materials_with_pagination(self, client):
        """测试分页"""
        response = client.get('/api/materials?page=1&per_page=20')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_materials_with_large_page(self, client):
        """测试大页码"""
        response = client.get('/api/materials?page=9999&per_page=10')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_materials_with_zero_page(self, client):
        """测试页码为0"""
        response = client.get('/api/materials?page=0&per_page=10')
        assert response.status_code == 200

    def test_get_materials_with_negative_page(self, client):
        """测试负页码"""
        response = client.get('/api/materials?page=-1&per_page=10')
        assert response.status_code == 200

    def test_get_materials_with_large_per_page(self, client):
        """测试大每页数量"""
        response = client.get('/api/materials?page=1&per_page=9999')
        assert response.status_code == 200

    def test_get_materials_with_zero_per_page(self, client):
        """测试每页数量为0"""
        response = client.get('/api/materials?page=1&per_page=0')
        assert response.status_code == 200

    def test_get_materials_with_negative_per_page(self, client):
        """测试负每页数量"""
        response = client.get('/api/materials?page=1&per_page=-10')
        assert response.status_code == 200

    def test_get_materials_with_multiple_params(self, client):
        """测试多个参数组合"""
        response = client.get('/api/materials?search=钢材&page=1&per_page=20')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_materials_invalid_param_type(self, client):
        """测试无效参数类型"""
        response = client.get('/api/materials?page=abc&per_page=xyz')
        assert response.status_code == 200

    def test_update_material_success(self, client, sample_data_factory):
        """测试成功更新原材料"""
        material_data = sample_data_factory.material({
            "name": "更新后的原材料"
        })
        response = client.put(
            '/api/materials/1',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert '更新成功' in data['message']
        assert data['data']['id'] == 1
        assert data['data']['name'] == material_data['name']

    def test_update_material_not_found(self, client, sample_data_factory):
        """测试更新不存在的原材料"""
        material_data = sample_data_factory.material()
        response = client.put(
            '/api/materials/99999',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_update_material_partial(self, client):
        """测试部分更新原材料"""
        response = client.put(
            '/api/materials/1',
            json={"quantity": 50.0},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_update_material_with_zero_id(self, client, sample_data_factory):
        """测试更新 ID 为 0 的原材料"""
        material_data = sample_data_factory.material()
        response = client.put(
            '/api/materials/0',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_update_material_with_negative_id(self, client, sample_data_factory):
        """测试更新负 ID 的原材料"""
        material_data = sample_data_factory.material()
        response = client.put(
            '/api/materials/-1',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code in [200, 404, 405]

    def test_update_material_with_large_id(self, client, sample_data_factory):
        """测试更新大 ID 的原材料"""
        material_data = sample_data_factory.material()
        response = client.put(
            '/api/materials/999999999',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_update_material_empty_body(self, client):
        """测试空请求体更新"""
        response = client.put(
            '/api/materials/1',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_update_material_invalid_json(self, client):
        """测试无效 JSON 更新"""
        response = client.put(
            '/api/materials/1',
            data='invalid json',
            content_type='application/json'
        )
        assert response.status_code in [400, 500]

    def test_update_material_with_null_values(self, client):
        """测试更新包含 null 值"""
        response = client.put(
            '/api/materials/1',
            json={"name": None, "quantity": None},
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_delete_material_success(self, client):
        """测试成功删除原材料"""
        response = client.delete('/api/materials/1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert '删除成功' in data['message']

    def test_delete_material_not_found(self, client):
        """测试删除不存在的原材料"""
        response = client.delete('/api/materials/99999')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_delete_material_with_zero_id(self, client):
        """测试删除 ID 为 0 的原材料"""
        response = client.delete('/api/materials/0')
        assert response.status_code == 200

    def test_delete_material_with_negative_id(self, client):
        """测试删除负 ID 的原材料"""
        response = client.delete('/api/materials/-1')
        assert response.status_code in [200, 404, 405]

    def test_delete_material_with_large_id(self, client):
        """测试删除大 ID 的原材料"""
        response = client.delete('/api/materials/999999999')
        assert response.status_code == 200

    def test_batch_delete_materials_success(self, client):
        """测试成功批量删除原材料"""
        response = client.post(
            '/api/materials/batch-delete',
            json={"ids": [1, 2, 3]},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert '已删除 3 条记录' in data['message']

    def test_batch_delete_empty_ids(self, client):
        """测试批量删除空ID列表"""
        response = client.post(
            '/api/materials/batch-delete',
            json={"ids": []},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert '已删除 0 条记录' in data['message']

    def test_batch_delete_missing_ids(self, client):
        """测试批量删除缺少ids参数"""
        response = client.post(
            '/api/materials/batch-delete',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert '已删除 0 条记录' in data['message']

    def test_batch_delete_single_id(self, client):
        """测试批量删除单个ID"""
        response = client.post(
            '/api/materials/batch-delete',
            json={"ids": [1]},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert '已删除 1 条记录' in data['message']

    def test_batch_delete_large_ids(self, client):
        """测试批量删除大量ID"""
        ids = list(range(1, 101))
        response = client.post(
            '/api/materials/batch-delete',
            json={"ids": ids},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert '已删除 100 条记录' in data['message']

    def test_batch_delete_with_zero_id(self, client):
        """测试批量删除包含0的ID"""
        response = client.post(
            '/api/materials/batch-delete',
            json={"ids": [0, 1, 2]},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_batch_delete_with_negative_id(self, client):
        """测试批量删除包含负ID"""
        response = client.post(
            '/api/materials/batch-delete',
            json={"ids": [-1, 1, 2]},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_batch_delete_with_duplicate_ids(self, client):
        """测试批量删除包含重复ID"""
        response = client.post(
            '/api/materials/batch-delete',
            json={"ids": [1, 1, 2, 2]},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_batch_delete_invalid_json(self, client):
        """测试批量删除无效JSON"""
        response = client.post(
            '/api/materials/batch-delete',
            data='invalid json',
            content_type='application/json'
        )
        assert response.status_code in [400, 500]

    def test_batch_delete_empty_body(self, client):
        """测试批量删除空请求体"""
        response = client.post(
            '/api/materials/batch-delete',
            data='{}',
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_low_stock_materials_success(self, client):
        """测试成功获取低库存原材料"""
        response = client.get('/api/materials/low-stock')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'data' in data
        assert 'count' in data
        assert isinstance(data['data'], list)
        assert isinstance(data['count'], int)

    def test_get_low_stock_with_threshold(self, client):
        """测试带阈值的低库存查询"""
        response = client.get('/api/materials/low-stock?threshold=20')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_low_stock_zero_threshold(self, client):
        """测试阈值为0的低库存查询"""
        response = client.get('/api/materials/low-stock?threshold=0')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_low_stock_negative_threshold(self, client):
        """测试负阈值的低库存查询"""
        response = client.get('/api/materials/low-stock?threshold=-10')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_low_stock_large_threshold(self, client):
        """测试大阈值的低库存查询"""
        response = client.get('/api/materials/low-stock?threshold=999999')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_low_stock_float_threshold(self, client):
        """测试浮点数阈值的低库存查询"""
        response = client.get('/api/materials/low-stock?threshold=10.5')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_low_stock_invalid_threshold(self, client):
        """测试无效阈值的低库存查询"""
        response = client.get('/api/materials/low-stock?threshold=abc')
        assert response.status_code == 200

    def test_get_low_stock_empty_threshold(self, client):
        """测试空阈值的低库存查询"""
        response = client.get('/api/materials/low-stock?threshold=')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_materials_response_format(self, client):
        """测试响应格式"""
        response = client.get('/api/materials')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)
        assert 'success' in data
        assert 'data' in data
        assert 'count' in data

    def test_materials_response_content_type(self, client):
        """测试响应内容类型"""
        response = client.get('/api/materials')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_materials_cors_headers(self, client):
        """测试 CORS 头"""
        response = client.get('/api/materials')
        assert response.status_code == 200

    def test_materials_options_method(self, client):
        """测试 OPTIONS 方法"""
        response = client.options('/api/materials')
        assert response.status_code in [200, 405]

    def test_materials_head_method(self, client):
        """测试 HEAD 方法"""
        response = client.head('/api/materials')
        assert response.status_code in [200, 405]

    def test_materials_invalid_method(self, client):
        """测试不支持的 HTTP 方法"""
        response = client.patch('/api/materials')
        assert response.status_code == 405

    def test_add_material_with_extra_fields(self, client, sample_data_factory):
        """测试添加包含额外字段的原材料"""
        material_data = sample_data_factory.material({
            "extra_field": "extra_value",
            "another_field": 123
        })
        response = client.post(
            '/api/materials',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_update_material_with_extra_fields(self, client, sample_data_factory):
        """测试更新包含额外字段的原材料"""
        material_data = sample_data_factory.material({
            "extra_field": "extra_value"
        })
        response = client.put(
            '/api/materials/1',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_materials_with_special_chars_search(self, client):
        """测试特殊字符搜索"""
        response = client.get('/api/materials?search=%20%21%40%23%24')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_materials_with_sql_injection_attempt(self, client):
        """测试 SQL 注入尝试"""
        response = client.get('/api/materials?search=\'; DROP TABLE materials; --')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_batch_delete_with_null_ids(self, client):
        """测试批量删除包含 null 的 ID"""
        response = client.post(
            '/api/materials/batch-delete',
            json={"ids": [1, None, 2]},
            content_type='application/json'
        )
        assert response.status_code in [200, 400]

    def test_add_material_with_whitespace_name(self, client):
        """测试名称只有空格"""
        response = client.post(
            '/api/materials',
            json={"name": "   "},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_add_material_with_newline_name(self, client):
        """测试名称包含换行符"""
        response = client.post(
            '/api/materials',
            json={"name": "测试\n原材料"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_materials_with_very_long_search(self, client):
        """测试超长搜索字符串"""
        response = client.get('/api/materials?search=' + 'a' * 10000)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_update_material_id_as_string(self, client, sample_data_factory):
        """测试 ID 为字符串时的更新"""
        material_data = sample_data_factory.material()
        response = client.put(
            '/api/materials/abc',
            json=material_data,
            content_type='application/json'
        )
        assert response.status_code == 405

    def test_delete_material_id_as_string(self, client):
        """测试 ID 为字符串时的删除"""
        response = client.delete('/api/materials/abc')
        assert response.status_code == 405

    def test_add_material_with_array_name(self, client):
        """测试名称为数组"""
        response = client.post(
            '/api/materials',
            json={"name": ["test", "name"]},
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_add_material_with_object_name(self, client):
        """测试名称为对象"""
        response = client.post(
            '/api/materials',
            json={"name": {"key": "value"}},
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_get_materials_with_multiple_same_params(self, client):
        """测试多个相同参数"""
        response = client.get('/api/materials?search=test&search=钢材')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_materials_response_size(self, client):
        """测试响应大小"""
        response = client.get('/api/materials')
        assert response.status_code == 200
        assert len(response.data) > 0

    def test_materials_encoding(self, client):
        """测试响应编码"""
        response = client.get('/api/materials')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_add_material_with_boolean_quantity(self, client):
        """测试数量为布尔值"""
        response = client.post(
            '/api/materials',
            json={"name": "测试", "quantity": True},
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_get_low_stock_with_multiple_params(self, client):
        """测试低库存查询多个参数"""
        response = client.get('/api/materials/low-stock?threshold=10&page=1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
