"""
pytest 配置和 fixtures
"""

import os
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch
import tempfile
import shutil

# 添加项目根目录到 sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(scope="session")
def app():
    """创建测试用的 Flask 应用"""
    from app import create_app
    from app.config import TestingConfig
    
    app = create_app(TestingConfig)
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True
    
    yield app


@pytest.fixture(scope="function")
def client(app):
    """创建测试用的 HTTP 客户端"""
    with app.test_client() as client:
        yield client


@pytest.fixture
def runner(app):
    """创建测试用的 CLI runner"""
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def db_session(app):
    """创建独立的数据库会话，每个测试自动回滚"""
    from app.db import SessionLocal
    from app.db.base import Base
    
    # 创建所有表
    Base.metadata.create_all(bind=app.engine if hasattr(app, 'engine') else SessionLocal().bind)
    
    session = SessionLocal()
    try:
        yield session
    finally:
        # 回滚所有更改
        session.rollback()
        session.close()


@pytest.fixture
def mock_external_api():
    """Mock 外部 API 调用"""
    mocks = {
        'httpx': MagicMock(),
        'redis': MagicMock(),
        'wechat': MagicMock(),
    }
    
    with patch('httpx.AsyncClient', mocks['httpx']), \
         patch('redis.Redis', mocks['redis']):
        yield mocks


@pytest.fixture
def mock_file_system():
    """Mock 文件系统操作"""
    temp_dir = tempfile.mkdtemp()
    
    mocks = {
        'temp_dir': temp_dir,
        'os_path_exists': MagicMock(return_value=True),
        'os_path_join': MagicMock(side_effect=os.path.join),
        'open': MagicMock(),
    }
    
    with patch('os.path.exists', mocks['os_path_exists']), \
         patch('os.path.join', mocks['os_path_join']), \
         patch('builtins.open', mocks['open']):
        yield mocks
    
    # 清理临时目录
    try:
        shutil.rmtree(temp_dir)
    except:
        pass


@pytest.fixture
def sample_data_factory():
    """测试数据工厂 - 生成各种测试数据"""
    
    class SampleDataFactory:
        @staticmethod
        def product(overrides=None):
            """生成产品测试数据"""
            data = {
                "product_name": f"测试产品_{SampleDataFactory._random_id()}",
                "price": 99.99,
                "unit": "个",
                "description": "测试描述",
                "category": "测试分类",
                "specification": "测试规格"
            }
            if overrides:
                data.update(overrides)
            return data
        
        @staticmethod
        def customer(overrides=None):
            """生成客户测试数据"""
            data = {
                "unit_name": f"测试公司_{SampleDataFactory._random_id()}",
                "contact": "张三",
                "phone": "13800138000",
                "address": "测试地址",
                "tax_id": "91310000MA1234567X",
                "bank_info": "测试银行信息"
            }
            if overrides:
                data.update(overrides)
            return data
        
        @staticmethod
        def shipment(overrides=None):
            """生成发货单测试数据"""
            data = {
                "unit_name": f"测试公司_{SampleDataFactory._random_id()}",
                "order_number": f"ORD{SampleDataFactory._random_id()}",
                "products": [
                    {"name": "产品 A", "quantity": 10, "price": 100},
                    {"name": "产品 B", "quantity": 5, "price": 50}
                ],
                "date": "2026-03-17",
                "total_amount": 1250.00,
                "status": "pending"
            }
            if overrides:
                data.update(overrides)
            return data
        
        @staticmethod
        def wechat_contact(overrides=None):
            """生成微信联系人测试数据"""
            data = {
                "wxid": f"wxid_{SampleDataFactory._random_id()}",
                "nickname": f"测试用户_{SampleDataFactory._random_id()}",
                "remark": "测试备注",
                "phone": "13800138000",
                "type": "friend"
            }
            if overrides:
                data.update(overrides)
            return data
        
        @staticmethod
        def material(overrides=None):
            """生成原材料测试数据"""
            data = {
                "name": f"原材料_{SampleDataFactory._random_id()}",
                "specification": "测试规格",
                "unit": "kg",
                "quantity": 100.0,
                "min_quantity": 10.0,
                "price": 50.0
            }
            if overrides:
                data.update(overrides)
            return data
        
        @staticmethod
        def _random_id():
            """生成随机 ID"""
            import random
            import time
            return f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
    
    return SampleDataFactory


@pytest.fixture
def sample_product():
    """示例产品数据"""
    return {
        "product_name": "测试产品",
        "price": 99.99,
        "unit": "个",
        "description": "测试描述"
    }


@pytest.fixture
def sample_customer():
    """示例客户数据"""
    return {
        "unit_name": "测试公司",
        "contact": "张三",
        "phone": "13800138000",
        "address": "测试地址"
    }


@pytest.fixture
def sample_shipment():
    """示例发货单数据"""
    return {
        "unit_name": "测试公司",
        "products": [
            {"name": "产品 A", "quantity": 10, "price": 100},
            {"name": "产品 B", "quantity": 5, "price": 50}
        ],
        "date": "2026-03-17"
    }


@pytest.fixture
def sample_template():
    """示例模板数据"""
    return {
        "name": "测试发货单模板",
        "template_type": "发货单",
        "business_scope": "orders",
        "fields": [
            {"label": "产品型号", "name": "model", "type": "text"},
            {"label": "数量", "name": "quantity", "type": "number"},
            {"label": "单价", "name": "price", "type": "number"},
            {"label": "金额", "name": "amount", "type": "number"}
        ],
        "preview_data": {
            "sample_rows": [{"产品型号": "ABC-001", "数量": 5}],
            "sheet_name": "Sheet1"
        }
    }


@pytest.fixture
def assert_response():
    """断言辅助函数"""
    
    def assert_success(response, expected_status=200):
        """断言响应成功"""
        assert response.status_code == expected_status
        assert response.content_type == 'application/json'
    
    def assert_error(response, expected_status=400):
        """断言响应错误"""
        assert response.status_code == expected_status
        assert response.content_type == 'application/json'
        data = response.get_json()
        assert 'error' in data or 'message' in data
    
    def assert_json_structure(response, required_fields):
        """断言 JSON 结构包含必需字段"""
        data = response.get_json()
        assert isinstance(data, dict)
        for field in required_fields:
            assert field in data, f"缺少必需字段：{field}"
    
    def assert_list_response(response, key='items'):
        """断言列表响应格式"""
        data = response.get_json()
        assert isinstance(data, dict)
        assert key in data
        assert isinstance(data[key], list)
    
    return {
        'success': assert_success,
        'error': assert_error,
        'json_structure': assert_json_structure,
        'list': assert_list_response
    }
