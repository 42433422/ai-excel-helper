"""
工具管理路由测试
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestTools:
    """工具管理路由测试"""

    def test_get_tools_list(self, client):
        """测试获取工具列表"""
        response = client.get('/api/tools')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'tools' in data
        assert isinstance(data['tools'], list)
        assert len(data['tools']) > 0

    def test_get_tools_list_structure(self, client):
        """测试工具列表数据结构"""
        response = client.get('/api/tools')
        data = response.get_json()
        tools = data['tools']
        for tool in tools:
            assert 'id' in tool
            assert 'name' in tool
            assert 'description' in tool
            assert 'category' in tool
            assert 'actions' in tool

    def test_get_tool_categories(self, client):
        """测试获取工具分类"""
        response = client.get('/api/tool-categories')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'categories' in data
        assert isinstance(data['categories'], list)
        assert len(data['categories']) > 0

    def test_get_tool_categories_structure(self, client):
        """测试工具分类数据结构"""
        response = client.get('/api/tool-categories')
        data = response.get_json()
        categories = data['categories']
        for category in categories:
            assert 'id' in category
            assert 'category_name' in category
            assert 'category_key' in category
            assert 'description' in category
            assert 'icon' in category

    def test_execute_tool_products(self, client):
        """测试执行产品管理工具"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "products", "action": "view"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_customers(self, client):
        """测试执行客户管理工具"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "customers", "action": "view"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_orders(self, client):
        """测试执行出货单工具"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "orders", "action": "view"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_shipment_generate(self, client):
        """测试执行生成发货单工具"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "shipment_generate", "action": "view"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_print(self, client):
        """测试执行标签打印工具"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "print", "action": "view"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_materials(self, client):
        """测试执行原材料仓库工具"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "materials", "action": "view"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_ocr(self, client):
        """测试执行图片 OCR 工具"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "ocr", "action": "view"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_wechat(self, client):
        """测试执行微信任务工具"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "wechat", "action": "view"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_excel_decompose(self, client):
        """测试执行 Excel 模板分解工具"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "excel_decompose", "action": "view"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_shipment_template(self, client):
        """测试执行发货单模板工具"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "shipment_template", "action": "view"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_database(self, client):
        """测试执行数据库管理工具"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "database"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_system(self, client):
        """测试执行系统设置工具"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "system"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_with_params(self, client):
        """测试执行工具时传递参数"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "products", "action": "view", "params": {"keyword": "测试"}},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_nonexistent_tool(self, client):
        """测试执行不存在的工具"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "nonexistent_tool"},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_execute_tool_missing_tool_id(self, client):
        """测试缺少 tool_id 参数"""
        response = client.post(
            '/api/tools/execute',
            json={"action": "view"},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_execute_tool_empty_body(self, client):
        """测试请求体为空"""
        response = client.post(
            '/api/tools/execute',
            content_type='application/json'
        )
        assert response.status_code in [400, 500]
        data = response.get_json()
        assert data['success'] is False

    def test_execute_tool_missing_action(self, client):
        """测试缺少 action 参数（应使用默认值 'view'）"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "products"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'redirect' in data

    def test_execute_tool_with_different_actions(self, client):
        """测试不同 action 类型的工具执行"""
        test_cases = [
            ("products", "view", "/console?view=products"),
            ("customers", "view", "/console?view=customers"),
            ("orders", "view", "/console?view=shipment-orders"),
            ("shipment_generate", "view", "/console?view=shipment"),
            ("print", "view", "/console?view=print"),
            ("materials", "view", "/console?view=materials"),
            ("ocr", "view", "/console?view=ocr"),
            ("wechat", "view", "/console?view=wechat-contacts"),
            ("excel_decompose", "view", "/console?view=excel"),
            ("shipment_template", "view", "/console?view=template-preview"),
        ]
        
        for tool_id, action, expected_redirect in test_cases:
            response = client.post(
                '/api/tools/execute',
                json={"tool_id": tool_id, "action": action},
                content_type='application/json'
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['redirect'] == expected_redirect

    def test_execute_tool_with_non_view_action(self, client):
        """测试非 view action 的工具执行"""
        test_cases = [
            ("products", "add"),
            ("customers", "add"),
            ("orders", "create"),
            ("print", "batch"),
        ]
        
        for tool_id, action in test_cases:
            response = client.post(
                '/api/tools/execute',
                json={"tool_id": tool_id, "action": action},
                content_type='application/json'
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'message' in data

    def test_execute_tool_with_complex_params(self, client):
        """测试执行工具时传递复杂参数"""
        complex_params = {
            "keyword": "测试",
            "page": 1,
            "page_size": 20,
            "filters": {
                "category": "电子产品",
                "price_range": [0, 1000]
            },
            "sort": {
                "field": "name",
                "order": "asc"
            }
        }
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "products", "action": "view", "params": complex_params},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_with_invalid_json(self, client):
        """测试无效的 JSON 请求体"""
        response = client.post(
            '/api/tools/execute',
            data='{"tool_id": "products", "action": "view"',
            content_type='application/json'
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False

    def test_execute_tool_with_empty_tool_id(self, client):
        """测试空的 tool_id 参数"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "", "action": "view"},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_execute_tool_with_null_params(self, client):
        """测试 params 为 null 的情况"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "products", "action": "view", "params": None},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_database_without_action(self, client):
        """测试数据库工具不需要 action 参数"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "database"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'message' in data

    def test_execute_tool_system_without_action(self, client):
        """测试系统工具不需要 action 参数"""
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "system"},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'message' in data

    def test_get_tools_list_content_type(self, client):
        """测试工具列表接口返回正确的 Content-Type"""
        response = client.get('/api/tools')
        assert response.content_type == 'application/json'

    def test_get_tool_categories_content_type(self, client):
        """测试工具分类接口返回正确的 Content-Type"""
        response = client.get('/api/tool-categories')
        assert response.content_type == 'application/json'

    def test_get_tools_list_all_fields(self, client):
        """测试工具列表返回所有必需字段"""
        response = client.get('/api/tools')
        data = response.get_json()
        tools = data['tools']
        expected_fields = ['id', 'name', 'description', 'category', 'actions']
        for tool in tools:
            for field in expected_fields:
                assert field in tool, f"工具 {tool.get('id')} 缺少字段 {field}"

    def test_get_tool_categories_all_fields(self, client):
        """测试工具分类返回所有必需字段"""
        response = client.get('/api/tool-categories')
        data = response.get_json()
        categories = data['categories']
        expected_fields = ['id', 'category_name', 'category_key', 'description', 'icon', 'sort_order', 'is_active']
        for category in categories:
            for field in expected_fields:
                assert field in category, f"分类 {category.get('id')} 缺少字段 {field}"

    def test_get_tools_list_count(self, client):
        """测试工具列表返回正确的工具数量"""
        response = client.get('/api/tools')
        data = response.get_json()
        tools = data['tools']
        assert len(tools) >= 10, "工具列表应至少包含 10 个工具"

    def test_get_tool_categories_count(self, client):
        """测试工具分类返回正确的分类数量"""
        response = client.get('/api/tool-categories')
        data = response.get_json()
        categories = data['categories']
        assert len(categories) >= 10, "工具分类应至少包含 10 个分类"

    def test_execute_tool_with_special_characters(self, client):
        """测试工具参数中包含特殊字符"""
        special_params = {
            "keyword": "测试<>&\"'特殊字符",
            "description": "包含\n换行符\t制表符"
        }
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "products", "action": "view", "params": special_params},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_with_large_params(self, client):
        """测试工具参数中包含大量数据"""
        large_params = {
            "keyword": "测试" * 1000,
            "description": "描述" * 1000
        }
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "products", "action": "view", "params": large_params},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_with_nested_params(self, client):
        """测试工具参数中包含嵌套对象"""
        nested_params = {
            "filter": {
                "level1": {
                    "level2": {
                        "level3": "深层嵌套值"
                    }
                }
            },
            "list": [1, 2, [3, 4, [5, 6]]]
        }
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "products", "action": "view", "params": nested_params},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_execute_tool_all_tools_view_action(self, client):
        """测试所有工具的 view action"""
        tool_ids = [
            "products", "customers", "orders", "shipment_generate", "print",
            "materials", "ocr", "wechat", "excel_decompose", "shipment_template"
        ]
        for tool_id in tool_ids:
            response = client.post(
                '/api/tools/execute',
                json={"tool_id": tool_id, "action": "view"},
                content_type='application/json'
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'redirect' in data
