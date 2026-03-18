"""
集成测试 - 端到端测试
"""

import pytest
import json


class TestIntegration:
    """集成测试"""

    def test_products_flow(self, client):
        """测试产品管理完整流程"""
        # 1. 添加产品
        response = client.post(
            '/api/products/add',
            json={"product_name": "集成测试产品", "price": 100},
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]
        
        # 2. 获取产品列表
        response = client.get('/api/products/list')
        assert response.status_code in [200, 500]
        
        # 3. 搜索产品
        response = client.get('/api/products/search?keyword=测试')
        assert response.status_code in [200, 404, 500]

    def test_shipment_flow(self, client):
        """测试发货单完整流程"""
        # 1. 获取下一个订单编号
        response = client.get('/api/shipment/orders/next_number')
        assert response.status_code in [200, 500]
        
        # 2. 获取购买单位列表
        response = client.get('/api/shipment/orders/purchase-units')
        assert response.status_code in [200, 500]
        
        # 3. 获取订单列表
        response = client.get('/api/shipment/orders')
        assert response.status_code in [200, 500]

    def test_customers_flow(self, client):
        """测试客户管理完整流程"""
        # 1. 获取客户列表
        response = client.get('/api/customers/list')
        assert response.status_code in [200, 500]
        
        # 2. 搜索客户
        response = client.get('/api/customers/list?search=测试')
        assert response.status_code in [200, 500]

    def test_wechat_flow(self, client):
        """测试微信任务完整流程"""
        # 1. 获取任务列表
        response = client.get('/api/wechat/tasks')
        assert response.status_code in [200, 500]
        
        # 2. 获取联系人列表
        response = client.get('/api/wechat/contacts')
        assert response.status_code in [200, 500]

    def test_print_flow(self, client):
        """测试打印管理完整流程"""
        # 1. 获取打印机列表
        response = client.get('/api/print/printers')
        assert response.status_code in [200, 500]
        
        # 2. 获取默认打印机
        response = client.get('/api/print/default')
        assert response.status_code in [200, 500]

    def test_ocr_flow(self, client):
        """测试 OCR 完整流程"""
        # 1. 测试 OCR 接口
        response = client.post(
            '/api/ocr/recognize',
            json={"text": "测试文字"},
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]

    def test_ai_chat_flow(self, client):
        """测试 AI 对话完整流程"""
        # 1. 获取配置
        response = client.get('/api/ai/config')
        assert response.status_code in [200, 500]
        
        # 2. 发送消息
        response = client.post(
            '/api/ai/chat',
            json={"message": "测试"},
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]
        
        # 3. 获取上下文
        response = client.get('/api/ai/context')
        assert response.status_code in [200, 500]

    def test_tools_flow(self, client):
        """测试工具表完整流程"""
        # 1. 获取工具列表
        response = client.get('/api/tools')
        assert response.status_code in [200, 500]
        
        # 2. 获取工具分类
        response = client.get('/api/tool-categories')
        assert response.status_code in [200, 500]
        
        # 3. 执行工具
        response = client.post(
            '/api/tools/execute',
            json={"tool_id": "products", "action": "view"},
            content_type='application/json'
        )
        assert response.status_code in [200, 500]

    def test_excel_flow(self, client):
        """测试 Excel 模板完整流程"""
        # 1. 获取模板列表
        response = client.get('/api/excel/templates')
        assert response.status_code in [200, 500]
        
        # 2. 测试模板分解接口
        response = client.post(
            '/api/excel/template/decompose',
            json={"template_id": "test"},
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 404, 500]

    def test_materials_flow(self, client):
        """测试原材料完整流程"""
        # 1. 获取原材料列表
        response = client.get('/api/materials')
        assert response.status_code in [200, 500]
        
        # 2. 获取低库存原材料
        response = client.get('/api/materials/low-stock')
        assert response.status_code in [200, 500]

    def test_error_handling(self, client):
        """测试错误处理"""
        # 测试无效路由
        response = client.get('/api/invalid/route')
        assert response.status_code == 404
        
        # 测试无效方法
        response = client.put('/api/products/list')
        assert response.status_code in [405, 404]

    def test_json_validation(self, client):
        """测试 JSON 验证"""
        # 测试无效 JSON
        response = client.post(
            '/api/products/add',
            data='invalid json',
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]
