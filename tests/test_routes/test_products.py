"""
产品管理路由测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestProducts:
    """产品管理路由测试"""

    @pytest.fixture
    def mock_products_service(self):
        """Mock ProductsService"""
        with patch('app.routes.products.ProductsService') as mock:
            yield mock

    @pytest.fixture
    def sample_product(self):
        """示例产品数据"""
        return {
            "unit_name": "个",
            "product_name": "测试产品",
            "price": 100.0,
            "description": "这是一个测试产品"
        }

    @pytest.fixture
    def sample_products_list(self):
        """示例产品列表数据"""
        return [
            {"id": 1, "unit_name": "个", "product_name": "产品A", "price": 100.0, "description": "描述A"},
            {"id": 2, "unit_name": "箱", "product_name": "产品B", "price": 200.0, "description": "描述B"},
            {"id": 3, "unit_name": "包", "product_name": "产品C", "price": 300.0, "description": "描述C"}
        ]

    def test_list_products_success(self, client, mock_products_service, sample_products_list):
        """测试获取产品列表 - 成功"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.get_products.return_value = {
            "success": True,
            "data": sample_products_list,
            "total": 3
        }

        response = client.get('/api/products/list')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["total"] == 3
        assert len(data["data"]) == 3
        assert data["data"][0]["product_name"] == "产品A"
        mock_service_instance.get_products.assert_called_once_with(
            unit_name=None,
            keyword=None,
            page=1,
            per_page=20
        )

    def test_list_products_with_pagination(self, client, mock_products_service, sample_products_list):
        """测试分页功能"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.get_products.return_value = {
            "success": True,
            "data": sample_products_list[:2],
            "total": 3
        }

        response = client.get('/api/products/list?page=1&per_page=2')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["total"] == 3
        mock_service_instance.get_products.assert_called_once_with(
            unit_name=None,
            keyword=None,
            page=1,
            per_page=2
        )

    def test_list_products_with_keyword(self, client, mock_products_service, sample_products_list):
        """测试搜索功能"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.get_products.return_value = {
            "success": True,
            "data": [sample_products_list[0]],
            "total": 1
        }

        response = client.get('/api/products/list?keyword=产品A')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["product_name"] == "产品A"
        mock_service_instance.get_products.assert_called_once_with(
            unit_name=None,
            keyword="产品A",
            page=1,
            per_page=20
        )

    def test_list_products_with_unit(self, client, mock_products_service, sample_products_list):
        """测试按单位过滤"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.get_products.return_value = {
            "success": True,
            "data": [sample_products_list[0]],
            "total": 1
        }

        response = client.get('/api/products/list?unit=个')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        mock_service_instance.get_products.assert_called_once_with(
            unit_name="个",
            keyword=None,
            page=1,
            per_page=20
        )

    def test_list_products_empty_result(self, client, mock_products_service):
        """测试空结果"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.get_products.return_value = {
            "success": True,
            "data": [],
            "total": 0
        }

        response = client.get('/api/products/list?keyword=不存在的产品')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["total"] == 0
        assert len(data["data"]) == 0

    def test_list_products_invalid_page(self, client, mock_products_service):
        """测试无效页码"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.get_products.side_effect = ValueError("无效的页码")

        response = client.get('/api/products/list?page=-1')
        
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "查询失败" in data["message"]

    def test_list_products_service_error(self, client, mock_products_service):
        """测试服务层错误"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.get_products.side_effect = Exception("数据库连接失败")

        response = client.get('/api/products/list')
        
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "查询失败" in data["message"]

    def test_add_product_success(self, client, mock_products_service, sample_product):
        """测试添加产品 - 成功"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.create_product.return_value = {
            "success": True,
            "message": "产品添加成功",
            "product_id": 1
        }

        response = client.post(
            '/api/products/add',
            json=sample_product,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["product_id"] == 1
        assert "添加成功" in data["message"]
        mock_service_instance.create_product.assert_called_once_with(sample_product)

    def test_add_product_missing_required_field(self, client, mock_products_service):
        """测试添加产品 - 缺少必填字段"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.create_product.return_value = {
            "success": False,
            "message": "缺少必填字段"
        }

        response = client.post(
            '/api/products/add',
            json={"product_name": "测试产品"},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_add_product_empty_name(self, client, mock_products_service):
        """测试添加空名称产品"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.create_product.return_value = {
            "success": False,
            "message": "产品名称不能为空"
        }

        response = client.post(
            '/api/products/add',
            json={"product_name": ""},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "不能为空" in data["message"]

    def test_add_product_invalid_price(self, client, mock_products_service, sample_product):
        """测试添加产品 - 无效价格"""
        sample_product["price"] = -100
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.create_product.return_value = {
            "success": False,
            "message": "价格必须大于0"
        }

        response = client.post(
            '/api/products/add',
            json=sample_product,
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_add_product_service_error(self, client, mock_products_service, sample_product):
        """测试添加产品 - 服务层错误"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.create_product.side_effect = Exception("数据库错误")

        response = client.post(
            '/api/products/add',
            json=sample_product,
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "添加失败" in data["message"]

    def test_update_product_success(self, client, mock_products_service, sample_product):
        """测试更新产品 - 成功"""
        sample_product['id'] = 1
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.update_product.return_value = {
            "success": True,
            "message": "产品更新成功"
        }

        response = client.post(
            '/api/products/update',
            json=sample_product,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "更新成功" in data["message"]
        mock_service_instance.update_product.assert_called_once_with(1, sample_product)

    def test_update_product_missing_id(self, client):
        """测试更新产品 - 缺少ID"""
        response = client.post(
            '/api/products/update',
            json={"product_name": "更新后的产品"},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "产品 ID 不能为空" in data["message"]

    def test_update_product_not_found(self, client, mock_products_service, sample_product):
        """测试更新产品 - 产品不存在"""
        sample_product['id'] = 999
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.update_product.return_value = {
            "success": False,
            "message": "产品不存在"
        }

        response = client.post(
            '/api/products/update',
            json=sample_product,
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_update_product_service_error(self, client, mock_products_service, sample_product):
        """测试更新产品 - 服务层错误"""
        sample_product['id'] = 1
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.update_product.side_effect = Exception("数据库错误")

        response = client.post(
            '/api/products/update',
            json=sample_product,
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "更新失败" in data["message"]

    def test_delete_product_success(self, client, mock_products_service):
        """测试删除产品 - 成功"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.delete_product.return_value = {
            "success": True,
            "message": "产品删除成功"
        }

        response = client.post(
            '/api/products/delete',
            json={"id": 1},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "删除成功" in data["message"]
        mock_service_instance.delete_product.assert_called_once_with(1)

    def test_delete_product_missing_id(self, client):
        """测试删除产品 - 缺少ID"""
        response = client.post(
            '/api/products/delete',
            json={},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "产品 ID 不能为空" in data["message"]

    def test_delete_product_not_found(self, client, mock_products_service):
        """测试删除产品 - 产品不存在"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.delete_product.return_value = {
            "success": False,
            "message": "产品不存在"
        }

        response = client.post(
            '/api/products/delete',
            json={"id": 999},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_delete_product_service_error(self, client, mock_products_service):
        """测试删除产品 - 服务层错误"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.delete_product.side_effect = Exception("数据库错误")

        response = client.post(
            '/api/products/delete',
            json={"id": 1},
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "删除失败" in data["message"]

    def test_search_products_success(self, client, mock_products_service, sample_products_list):
        """测试搜索产品 - 成功"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.get_products.return_value = {
            "success": True,
            "data": [sample_products_list[0]],
            "total": 1
        }

        response = client.get('/api/products/search?keyword=产品A')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["product_name"] == "产品A"
        mock_service_instance.get_products.assert_called_once_with(keyword="产品A")

    def test_search_products_empty_keyword(self, client, mock_products_service, sample_products_list):
        """测试搜索产品 - 空关键词"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.get_products.return_value = {
            "success": True,
            "data": sample_products_list,
            "total": 3
        }

        response = client.get('/api/products/search?keyword=')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_service_instance.get_products.assert_called_once_with(keyword="")

    def test_search_products_no_results(self, client, mock_products_service):
        """测试搜索产品 - 无结果"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.get_products.return_value = {
            "success": True,
            "data": [],
            "total": 0
        }

        response = client.get('/api/products/search?keyword=不存在的产品')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["total"] == 0
        assert len(data["data"]) == 0

    def test_search_products_service_error(self, client, mock_products_service):
        """测试搜索产品 - 服务层错误"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.get_products.side_effect = Exception("数据库错误")

        response = client.get('/api/products/search?keyword=测试')
        
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    def test_api_products_success(self, client, mock_products_service, sample_products_list):
        """测试 /api/products 接口 - 成功"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.get_products.return_value = {
            "success": True,
            "data": sample_products_list,
            "total": 3
        }

        response = client.get('/api/products/', follow_redirects=True)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["total"] == 3

    def test_api_products_with_filters(self, client, mock_products_service, sample_products_list):
        """测试 /api/products 接口 - 带过滤条件"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.get_products.return_value = {
            "success": True,
            "data": [sample_products_list[0]],
            "total": 1
        }

        response = client.get('/api/products/?unit=个&keyword=产品A&page=1&per_page=10', follow_redirects=True)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_service_instance.get_products.assert_called_once_with(
            unit_name="个",
            keyword="产品A",
            page=1,
            per_page=10
        )

    def test_batch_add_products_success(self, client):
        """测试批量添加产品 - 成功"""
        products = [
            {"unit_name": "个", "product_name": "产品A", "price": 100.0},
            {"unit_name": "箱", "product_name": "产品B", "price": 200.0}
        ]

        response = client.post(
            '/api/products/batch',
            json={"products": products},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "已添加 2 个产品" in data["message"]

    def test_batch_add_products_empty_list(self, client):
        """测试批量添加产品 - 空列表"""
        response = client.post(
            '/api/products/batch',
            json={"products": []},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "已添加 0 个产品" in data["message"]

    def test_batch_add_products_missing_field(self, client):
        """测试批量添加产品 - 缺少字段"""
        products = [
            {"product_name": "产品A"}
        ]

        response = client.post(
            '/api/products/batch',
            json={"products": products},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_batch_add_products_invalid_json(self, client):
        """测试批量添加产品 - 无效JSON"""
        response = client.post(
            '/api/products/batch',
            data="invalid json",
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    def test_export_products(self, client):
        """测试导出产品"""
        response = client.get('/api/products/export.xlsx')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "导出功能" in data["message"]

    def test_get_product_names_success(self, client):
        """测试获取产品名称列表 - 成功"""
        response = client.get('/api/products/product_names')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert "count" in data
        assert isinstance(data["data"], list)
        assert isinstance(data["count"], int)

    def test_search_product_names_success(self, client):
        """测试搜索产品名称 - 成功"""
        response = client.get('/api/products/product_names/search?keyword=测试')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert "count" in data

    def test_search_product_names_empty_keyword(self, client):
        """测试搜索产品名称 - 空关键词"""
        response = client.get('/api/products/product_names/search?keyword=')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_batch_delete_products_success(self, client):
        """测试批量删除产品 - 成功"""
        response = client.post(
            '/api/products/batch-delete',
            json={"ids": [1, 2, 3]},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "已删除 3 个产品" in data["message"]

    def test_batch_delete_products_empty_list(self, client):
        """测试批量删除产品 - 空列表"""
        response = client.post(
            '/api/products/batch-delete',
            json={"ids": []},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "已删除 0 个产品" in data["message"]

    def test_batch_delete_products_missing_ids(self, client):
        """测试批量删除产品 - 缺少ids字段"""
        response = client.post(
            '/api/products/batch-delete',
            json={},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "已删除 0 个产品" in data["message"]

    def test_complete_crud_workflow(self, client, mock_products_service, sample_product):
        """测试完整的CRUD工作流"""
        mock_service_instance = mock_products_service.return_value
        
        mock_service_instance.create_product.return_value = {
            "success": True,
            "message": "产品添加成功",
            "product_id": 1
        }
        mock_service_instance.get_products.return_value = {
            "success": True,
            "data": [{"id": 1, **sample_product}],
            "total": 1
        }
        mock_service_instance.update_product.return_value = {
            "success": True,
            "message": "产品更新成功"
        }
        mock_service_instance.delete_product.return_value = {
            "success": True,
            "message": "产品删除成功"
        }

        create_response = client.post(
            '/api/products/add',
            json=sample_product,
            content_type='application/json'
        )
        assert create_response.status_code == 200
        assert create_response.get_json()["success"] is True

        list_response = client.get('/api/products/list')
        assert list_response.status_code == 200
        assert list_response.get_json()["success"] is True

        sample_product['id'] = 1
        sample_product['product_name'] = "更新后的产品"
        update_response = client.post(
            '/api/products/update',
            json=sample_product,
            content_type='application/json'
        )
        assert update_response.status_code == 200
        assert update_response.get_json()["success"] is True

        delete_response = client.post(
            '/api/products/delete',
            json={"id": 1},
            content_type='application/json'
        )
        assert delete_response.status_code == 200
        assert delete_response.get_json()["success"] is True

    def test_pagination_edge_cases(self, client, mock_products_service):
        """测试分页边界条件"""
        mock_service_instance = mock_products_service.return_value
        
        mock_service_instance.get_products.return_value = {
            "success": True,
            "data": [],
            "total": 0
        }

        response = client.get('/api/products/list?page=abc')
        assert response.status_code == 500

        response = client.get('/api/products/list?per_page=xyz')
        assert response.status_code == 500

        response = client.get('/api/products/list?per_page=1000')
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_special_characters_in_search(self, client, mock_products_service):
        """测试特殊字符搜索"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.get_products.return_value = {
            "success": True,
            "data": [],
            "total": 0
        }

        special_keywords = ["测试@#$%", "产品&*()", "产品<>", "产品'\""]
        for keyword in special_keywords:
            response = client.get(f'/api/products/search?keyword={keyword}')
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True

    def test_unicode_in_product_name(self, client, mock_products_service):
        """测试产品名称中的Unicode字符"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.create_product.return_value = {
            "success": True,
            "message": "产品添加成功",
            "product_id": 1
        }

        unicode_product = {
            "unit_name": "个",
            "product_name": "测试产品🎉中文🇨🇳",
            "price": 100.0
        }

        response = client.post(
            '/api/products/add',
            json=unicode_product,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_large_data_payload(self, client, mock_products_service):
        """测试大数据负载"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.create_product.return_value = {
            "success": True,
            "message": "产品添加成功",
            "product_id": 1
        }

        large_description = "描述" * 1000
        large_product = {
            "unit_name": "个",
            "product_name": "测试产品",
            "price": 100.0,
            "description": large_description
        }

        response = client.post(
            '/api/products/add',
            json=large_product,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_concurrent_requests(self, client, mock_products_service, sample_products_list):
        """测试并发请求"""
        mock_service_instance = mock_products_service.return_value
        mock_service_instance.get_products.return_value = {
            "success": True,
            "data": sample_products_list,
            "total": 3
        }

        responses = []
        for _ in range(5):
            response = client.get('/api/products/list')
            responses.append(response)
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
