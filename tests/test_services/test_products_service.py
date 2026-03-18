"""
产品库服务单元测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from app.services.products_service import ProductsService
from app.db.models import Product


class TestProductsService:
    """产品库服务测试"""

    @pytest.fixture
    def service(self):
        """创建产品库服务实例"""
        return ProductsService()

    @pytest.fixture
    def mock_db(self):
        """创建 Mock 数据库会话"""
        db = MagicMock()
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        db.query = MagicMock()
        return db

    class TestGetProducts:
        """获取产品列表测试"""

        @patch('app.services.products_service.get_db')
        def test_get_products_success(self, mock_get_db, service, mock_db):
            """测试成功获取产品列表"""
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_product = Mock()
            mock_product.id = 1
            mock_product.name = "测试产品"
            mock_product.price = 100.0
            mock_product.description = "测试描述"
            mock_product.model_number = "MODEL001"
            mock_product.specification = "规格A"
            mock_product.quantity = 10
            mock_product.category = "类别A"
            mock_product.brand = "品牌A"
            mock_product.unit = "个"
            mock_product.is_active = 1
            mock_product.created_at = datetime.now()
            mock_product.updated_at = datetime.now()

            mock_db.query.return_value.filter.return_value.count.return_value = 2
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = [
                mock_product,
                mock_product
            ]

            result = service.get_products(page=1, per_page=20)

            assert result["success"] is True
            assert result["total"] == 2
            assert len(result["data"]) == 2
            assert result["page"] == 1
            assert result["per_page"] == 20

        @patch('app.services.products_service.get_db')
        def test_get_products_with_keyword(self, mock_get_db, service, mock_db):
            """测试带关键词搜索"""
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_product = Mock()
            mock_product.id = 1
            mock_product.name = "测试产品"
            mock_product.price = 100.0
            mock_product.description = "测试描述"

            mock_db.query.return_value.filter.return_value.count.return_value = 1
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = [mock_product]

            result = service.get_products(keyword="测试")

            assert result["success"] is True
            assert result["total"] == 1

        @patch('app.services.products_service.get_db')
        def test_get_products_table_not_exists(self, mock_get_db, service, mock_db):
            """测试产品表不存在"""
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.bind = Mock()
            mock_db.bind.get_table_names.return_value = []

            result = service.get_products()

            assert result["success"] is True
            assert result["data"] == []
            assert result["total"] == 0

        @patch('app.services.products_service.get_db')
        def test_get_products_exception(self, mock_get_db, service):
            """测试异常情况"""
            mock_get_db.side_effect = Exception("数据库错误")

            result = service.get_products()

            assert result["success"] is False
            assert "数据库错误" in result["message"]

        @patch('app.services.products_service.get_db')
        def test_get_products_pagination(self, mock_get_db, service, mock_db):
            """测试分页功能"""
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_product = Mock()
            mock_product.id = 1
            mock_product.name = "测试产品"
            mock_product.price = 100.0
            mock_product.description = "测试描述"

            mock_db.query.return_value.filter.return_value.count.return_value = 50
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = [mock_product]

            result = service.get_products(page=2, per_page=10)

            assert result["success"] is True
            assert result["page"] == 2
            assert result["per_page"] == 10

    class TestGetProduct:
        """获取单个产品测试"""

        @patch('app.services.products_service.get_db')
        def test_get_product_success(self, mock_get_db, service, mock_db):
            """测试成功获取单个产品"""
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_product = Mock()
            mock_product.id = 1
            mock_product.name = "测试产品"
            mock_product.price = 100.0
            mock_product.description = "测试描述"

            mock_db.query.return_value.filter.return_value.first.return_value = mock_product

            result = service.get_product(1)

            assert result["success"] is True
            assert result["data"]["name"] == "测试产品"
            assert result["data"]["product_name"] == "测试产品"

        @patch('app.services.products_service.get_db')
        def test_get_product_not_found(self, mock_get_db, service, mock_db):
            """测试产品不存在"""
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            result = service.get_product(999)

            assert result["success"] is False
            assert "产品不存在" in result["message"]

        @patch('app.services.products_service.get_db')
        def test_get_product_exception(self, mock_get_db, service):
            """测试异常情况"""
            mock_get_db.side_effect = Exception("数据库错误")

            result = service.get_product(1)

            assert result["success"] is False
            assert "数据库错误" in result["message"]

    class TestCreateProduct:
        """创建产品测试"""

        @patch('app.services.products_service.get_db')
        def test_create_product_success(self, mock_get_db, service, mock_db):
            """测试成功创建产品"""
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_product = Mock()
            mock_product.id = 1
            mock_db.add.return_value = None
            mock_db.refresh.return_value = None
            mock_db.commit.return_value = None

            data = {
                "product_name": "新产品",
                "price": 99.99,
                "description": "产品描述"
            }

            result = service.create_product(data)

            assert result["success"] is True
            assert "product_id" in result

        @patch('app.services.products_service.get_db')
        def test_create_product_with_name_field(self, mock_get_db, service, mock_db):
            """测试使用 name 字段创建产品"""
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_product = Mock()
            mock_product.id = 1
            mock_db.add.return_value = None
            mock_db.refresh.return_value = None
            mock_db.commit.return_value = None

            data = {
                "name": "新产品",
                "price": 99.99
            }

            result = service.create_product(data)

            assert result["success"] is True

        @patch('app.services.products_service.get_db')
        def test_create_product_missing_name(self, mock_get_db, service, mock_db):
            """测试缺少产品名称"""
            mock_get_db.return_value.__enter__.return_value = mock_db

            data = {
                "price": 99.99,
                "description": "产品描述"
            }

            result = service.create_product(data)

            assert result["success"] is False
            assert "产品名称不能为空" in result["message"]

        @patch('app.services.products_service.get_db')
        def test_create_product_exception(self, mock_get_db, service, mock_db):
            """测试异常情况"""
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.add.side_effect = Exception("数据库错误")

            data = {
                "product_name": "新产品",
                "price": 99.99
            }

            result = service.create_product(data)

            assert result["success"] is False
            assert "创建失败" in result["message"]

        @patch('app.services.products_service.get_db')
        def test_create_product_with_all_fields(self, mock_get_db, service, mock_db):
            """测试使用所有字段创建产品"""
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_product = Mock()
            mock_product.id = 1
            mock_db.add.return_value = None
            mock_db.refresh.return_value = None
            mock_db.commit.return_value = None

            data = {
                "product_name": "完整产品",
                "price": 199.99,
                "description": "完整描述",
                "model_number": "MODEL123",
                "specification": "规格B",
                "quantity": 50,
                "category": "类别B",
                "brand": "品牌B",
                "unit": "箱",
                "is_active": 1
            }

            result = service.create_product(data)

            assert result["success"] is True

    class TestUpdateProduct:
        """更新产品测试"""

        @patch('app.services.products_service.get_db')
        def test_update_product_success(self, mock_get_db, service, mock_db):
            """测试成功更新产品"""
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_product = Mock()
            mock_product.id = 1
            mock_product.name = "旧名称"
            mock_product.price = 100.0
            mock_db.query.return_value.filter.return_value.first.return_value = mock_product

            data = {
                "product_name": "新名称",
                "price": 150.0
            }

            result = service.update_product(1, data)

            assert result["success"] is True
            assert "产品更新成功" in result["message"]

        @patch('app.services.products_service.get_db')
        def test_update_product_not_found(self, mock_get_db, service, mock_db):
            """测试产品不存在"""
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            data = {
                "product_name": "新名称"
            }

            result = service.update_product(999, data)

            assert result["success"] is False
            assert "产品不存在" in result["message"]

        @patch('app.services.products_service.get_db')
        def test_update_product_no_fields(self, mock_get_db, service, mock_db):
            """测试没有要更新的字段"""
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_product = Mock()
            mock_product.id = 1
            mock_db.query.return_value.filter.return_value.first.return_value = mock_product

            data = {}

            result = service.update_product(1, data)

            assert result["success"] is False
            assert "没有要更新的字段" in result["message"]

        @patch('app.services.products_service.get_db')
        def test_update_product_exception(self, mock_get_db, service, mock_db):
            """测试异常情况"""
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.side_effect = Exception("数据库错误")

            data = {
                "product_name": "新名称"
            }

            result = service.update_product(1, data)

            assert result["success"] is False
            assert "更新失败" in result["message"]

        @patch('app.services.products_service.get_db')
        def test_update_product_with_name_field(self, mock_get_db, service, mock_db):
            """测试使用 name 字段更新"""
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_product = Mock()
            mock_product.id = 1
            mock_db.query.return_value.filter.return_value.first.return_value = mock_product

            data = {
                "name": "新名称"
            }

            result = service.update_product(1, data)

            assert result["success"] is True

        @patch('app.services.products_service.get_db')
        def test_update_product_multiple_fields(self, mock_get_db, service, mock_db):
            """测试更新多个字段"""
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_product = Mock()
            mock_product.id = 1
            mock_db.query.return_value.filter.return_value.first.return_value = mock_product

            data = {
                "product_name": "新名称",
                "price": 200.0,
                "description": "新描述",
                "quantity": 100,
                "category": "新类别"
            }

            result = service.update_product(1, data)

            assert result["success"] is True

    class TestDeleteProduct:
        """删除产品测试"""

        @patch('app.services.products_service.get_db')
        def test_delete_product_success(self, mock_get_db, service, mock_db):
            """测试成功删除产品"""
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_product = Mock()
            mock_product.id = 1
            mock_db.query.return_value.filter.return_value.first.return_value = mock_product

            result = service.delete_product(1)

            assert result["success"] is True
            assert "产品删除成功" in result["message"]

        @patch('app.services.products_service.get_db')
        def test_delete_product_not_found(self, mock_get_db, service, mock_db):
            """测试产品不存在"""
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            result = service.delete_product(999)

            assert result["success"] is False
            assert "产品不存在" in result["message"]

        @patch('app.services.products_service.get_db')
        def test_delete_product_exception(self, mock_get_db, service):
            """测试异常情况"""
            mock_get_db.side_effect = Exception("数据库错误")

            result = service.delete_product(1)

            assert result["success"] is False
            assert "删除失败" in result["message"]

    class TestProductExists:
        """产品存在性检查测试"""

        @patch('app.services.products_service.get_db')
        def test_product_exists_true(self, mock_get_db, service, mock_db):
            """测试产品存在"""
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_product = Mock()
            mock_product.id = 1
            mock_db.query.return_value.filter.return_value.first.return_value = mock_product

            result = service._product_exists(1)

            assert result is True

        @patch('app.services.products_service.get_db')
        def test_product_exists_false(self, mock_get_db, service, mock_db):
            """测试产品不存在"""
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            result = service._product_exists(999)

            assert result is False

        @patch('app.services.products_service.get_db')
        def test_product_exists_exception(self, mock_get_db, service):
            """测试异常情况"""
            mock_get_db.side_effect = Exception("数据库错误")

            result = service._product_exists(1)

            assert result is False

    class TestProductToDict:
        """产品转字典测试"""

        def test_product_to_dict(self, service):
            """测试产品转字典"""
            mock_product = Mock()
            mock_product.id = 1
            mock_product.name = "测试产品"
            mock_product.price = 100.0
            mock_product.description = "测试描述"

            result = service._product_to_dict(mock_product)

            assert result["id"] == 1
            assert result["name"] == "测试产品"
            assert result["product_name"] == "测试产品"
            assert result["price"] == 100.0

        def test_product_to_dict_without_name(self, service):
            """测试没有 name 字段的产品"""
            mock_product = Mock()
            mock_product.id = 1
            mock_product.price = 100.0

            result = service._product_to_dict(mock_product)

            assert result["id"] == 1
            assert result["price"] == 100.0
            assert "product_name" not in result


class TestProductsServiceIntegration:
    """产品库服务集成测试"""

    @pytest.fixture
    def mock_db_session(self):
        """创建 Mock 数据库会话"""
        db = MagicMock()
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        db.query = MagicMock()
        return db

    @patch('app.services.products_service.get_db')
    def test_full_crud_workflow(self, mock_get_db):
        """测试完整的 CRUD 工作流"""
        service = ProductsService()
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db

        mock_product = Mock()
        mock_product.id = 1
        mock_product.name = "测试产品"
        mock_product.price = 100.0

        mock_db.query.return_value.filter.return_value.first.return_value = mock_product

        create_data = {
            "product_name": "测试产品",
            "price": 100.0
        }

        create_result = service.create_product(create_data)
        assert create_result["success"] is True

        get_result = service.get_product(1)
        assert get_result["success"] is True

        update_data = {
            "price": 150.0
        }

        update_result = service.update_product(1, update_data)
        assert update_result["success"] is True

        delete_result = service.delete_product(1)
        assert delete_result["success"] is True

    @patch('app.services.products_service.get_db')
    def test_search_and_filter_workflow(self, mock_get_db):
        """测试搜索和过滤工作流"""
        service = ProductsService()
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db

        mock_product = Mock()
        mock_product.id = 1
        mock_product.name = "测试产品"
        mock_product.price = 100.0

        mock_db.query.return_value.filter.return_value.count.return_value = 1
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = [mock_product]

        result = service.get_products(keyword="测试", page=1, per_page=20)

        assert result["success"] is True
        assert result["total"] == 1
        assert len(result["data"]) == 1
