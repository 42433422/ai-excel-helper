"""
应用服务层测试

测试应用服务的功能
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.application.product_app_service import ProductApplicationService
from app.application.material_app_service import MaterialApplicationService
from app.application.extract_log_app_service import ExtractLogApplicationService
from app.application.customer_app_service import CustomerApplicationService
from app.application.shipment_app_service import ShipmentApplicationService
from app.domain.services.intent_recognition_service import IntentRecognitionService
from app.domain.services.product_import_validator import ProductImportValidator, ValidationResult
from app.domain.services.shipment_rules_engine import ShipmentRulesEngine
from app.domain.services.pricing_engine import PricingEngine, CustomerType


class TestProductApplicationService:
    """测试产品应用服务"""

    def test_get_products(self):
        """测试获取产品列表"""
        mock_products_service = Mock()
        mock_products_service.get_products.return_value = {
            "success": True,
            "data": [],
            "total": 0
        }

        service = ProductApplicationService(products_service=mock_products_service)
        result = service.get_products()

        assert result["success"] is True
        mock_products_service.get_products.assert_called_once()

    def test_create_product_validation(self):
        """测试创建产品验证"""
        mock_products_service = Mock()
        service = ProductApplicationService(products_service=mock_products_service)

        result = service.create_product({"name": ""})
        assert result["success"] is False
        assert "不能为空" in result["message"]

    def test_get_product_statistics(self):
        """测试获取产品统计"""
        mock_products_service = Mock()
        mock_products_service.get_products.return_value = {"total": 10}

        service = ProductApplicationService(products_service=mock_products_service)
        result = service.get_product_statistics()

        assert result["success"] is True
        assert result["data"]["total_products"] == 10


class TestMaterialApplicationService:
    """测试原材料应用服务"""

    def test_get_materials(self):
        """测试获取原材料列表"""
        mock_repository = Mock()
        mock_repository.find_all.return_value = {
            "success": True,
            "data": [],
            "total": 0
        }

        service = MaterialApplicationService(repository=mock_repository)
        result = service.get_materials()

        assert result["success"] is True
        mock_repository.find_all.assert_called_once()

    def test_create_material_validation(self):
        """测试创建原材料验证"""
        mock_repository = Mock()
        service = MaterialApplicationService(repository=mock_repository)

        result = service.create_material({"name": ""})
        assert result["success"] is False
        assert "不能为空" in result["message"]

    def test_create_material_negative_price(self):
        """测试创建原材料负数价格验证"""
        mock_repository = Mock()
        service = MaterialApplicationService(repository=mock_repository)

        result = service.create_material({"name": "测试", "price": -100})
        assert result["success"] is False
        assert "负数" in result["message"]

    def test_get_material_not_found(self):
        """测试获取不存在的原材料"""
        mock_repository = Mock()
        mock_repository.find_by_id.return_value = None

        service = MaterialApplicationService(repository=mock_repository)
        result = service.get_material(999)

        assert result["success"] is False
        assert "不存在" in result["message"]

    def test_delete_material_success(self):
        """测试删除原材料成功"""
        mock_repository = Mock()
        mock_repository.delete.return_value = True

        service = MaterialApplicationService(repository=mock_repository)
        result = service.delete_material(1)

        assert result["success"] is True
        assert "成功" in result["message"]

    def test_delete_material_failure(self):
        """测试删除原材料失败"""
        mock_repository = Mock()
        mock_repository.delete.return_value = False

        service = MaterialApplicationService(repository=mock_repository)
        result = service.delete_material(1)

        assert result["success"] is False
        assert "失败" in result["message"]

    def test_batch_delete_materials(self):
        """测试批量删除原材料"""
        mock_repository = Mock()
        mock_repository.batch_delete.return_value = 3

        service = MaterialApplicationService(repository=mock_repository)
        result = service.batch_delete_materials([1, 2, 3])

        assert result["success"] is True
        assert result["deleted_count"] == 3

    def test_get_low_stock_materials(self):
        """测试获取低库存原材料"""
        mock_repository = Mock()
        mock_repository.find_low_stock.return_value = [
            {"name": "原材料A", "quantity": 5}
        ]

        service = MaterialApplicationService(repository=mock_repository)
        result = service.get_low_stock_materials(threshold=10)

        assert result["success"] is True
        assert len(result["data"]) == 1


class TestExtractLogApplicationService:
    """测试提取日志应用服务"""

    def test_get_extract_logs(self):
        """测试获取提取日志列表"""
        mock_store = Mock()
        mock_store.find_all.return_value = {
            "success": True,
            "data": [],
            "total": 0
        }

        service = ExtractLogApplicationService(store=mock_store)
        result = service.get_extract_logs()

        assert result["success"] is True
        mock_store.find_all.assert_called_once()

    def test_get_extract_log_not_found(self):
        """测试获取不存在的日志"""
        mock_store = Mock()
        mock_store.find_by_id.return_value = None

        service = ExtractLogApplicationService(store=mock_store)
        result = service.get_extract_log(999)

        assert result["success"] is False
        assert "不存在" in result["message"]

    def test_create_extract_log(self):
        """测试创建提取日志"""
        mock_store = Mock()
        mock_store.create.return_value = {
            "success": True,
            "log_id": 1
        }

        service = ExtractLogApplicationService(store=mock_store)
        result = service.create_extract_log({"file_name": "test.xlsx"})

        assert result["success"] is True
        assert result["log_id"] == 1

    def test_delete_extract_log(self):
        """测试删除提取日志"""
        mock_store = Mock()
        mock_store.delete.return_value = {"success": True}

        service = ExtractLogApplicationService(store=mock_store)
        result = service.delete_extract_log(1)

        assert result["success"] is True

    def test_clear_old_logs(self):
        """测试清理旧日志"""
        mock_store = Mock()
        mock_store.clear_old.return_value = {
            "success": True,
            "deleted_count": 5
        }

        service = ExtractLogApplicationService(store=mock_store)
        result = service.clear_old_logs(days=30)

        assert result["success"] is True
        assert result["deleted_count"] == 5


class TestCustomerApplicationService:
    """测试客户应用服务"""

    def test_get_all_customers(self):
        """测试获取所有客户"""
        with patch('app.application.customer_app_service._get_customers_engine'):
            with patch('app.application.customer_app_service._CustomersSessionLocal'):
                service = CustomerApplicationService()
                session_mock = MagicMock()
                query_mock = MagicMock()
                query_mock.count.return_value = 0
                query_mock.order_by.return_value = query_mock
                query_mock.offset.return_value = query_mock
                query_mock.limit.return_value = query_mock
                query_mock.all.return_value = []

                with patch.object(service, '_get_session', return_value=session_mock):
                    session_mock.query.return_value = query_mock
                    result = service.get_all()

                    assert result["success"] is True


class TestIntentRecognitionService:
    """测试意图识别领域服务"""

    def test_recognize_shipment_intent(self):
        """测试识别发货意图"""
        service = IntentRecognitionService()
        intent, confidence, params = service.recognize("我想开一个发货单")

        assert intent.value == "shipment"
        assert confidence > 0

    def test_recognize_product_intent(self):
        """测试识别产品意图"""
        service = IntentRecognitionService()
        intent, confidence, params = service.recognize("产品型号")

        assert intent.value == "product"
        assert confidence > 0

    def test_recognize_unknown_intent(self):
        """测试识别未知意图"""
        service = IntentRecognitionService()
        intent, confidence, params = service.recognize("今天天气怎么样")

        assert intent.value == "unknown"


class TestProductImportValidator:
    """测试产品导入验证领域服务"""

    def test_validate_valid_products(self):
        """测试验证有效产品"""
        validator = ProductImportValidator()
        products = [
            {"name": "产品A", "price": 100},
            {"name": "产品B", "price": 200}
        ]

        result = validator.validate(products)
        assert result.is_valid is True

    def test_validate_empty_products(self):
        """测试验证空产品列表"""
        validator = ProductImportValidator()
        result = validator.validate([])
        assert result.is_valid is False

    def test_validate_missing_name(self):
        """测试验证缺少名称"""
        validator = ProductImportValidator()
        products = [{"price": 100}]

        result = validator.validate(products)
        assert result.is_valid is False
        assert any("名称" in e.message for e in result.errors)

    def test_validate_negative_price(self):
        """测试验证负数价格"""
        validator = ProductImportValidator()
        products = [{"name": "产品", "price": -100}]

        result = validator.validate(products)
        assert result.is_valid is False
        assert any("负数" in e.message for e in result.errors)


class TestShipmentRulesEngine:
    """测试发货规则引擎"""

    def test_validate_valid_shipment(self):
        """测试验证有效发货单"""
        engine = ShipmentRulesEngine()
        data = {
            "unit_name": "测试单位",
            "items": [{"name": "产品", "quantity": 10, "price": 100}]
        }

        result = engine.validate(data)
        assert result.is_valid is True

    def test_validate_empty_unit(self):
        """测试验证空单位"""
        engine = ShipmentRulesEngine()
        data = {
            "unit_name": "",
            "items": [{"name": "产品", "quantity": 10}]
        }

        result = engine.validate(data)
        assert result.is_valid is False

    def test_validate_empty_items(self):
        """测试验证空项目"""
        engine = ShipmentRulesEngine()
        data = {
            "unit_name": "测试单位",
            "items": []
        }

        result = engine.validate(data)
        assert result.is_valid is False

    def test_calculate_total(self):
        """测试计算总金额"""
        engine = ShipmentRulesEngine()
        data = {
            "items": [
                {"quantity": 2, "price": 100},
                {"quantity": 3, "price": 50}
            ]
        }

        total = engine.calculate_total(data)
        assert total == 350


class TestPricingEngine:
    """测试定价引擎"""

    def test_calculate_retail_price(self):
        """测试计算零售价格"""
        engine = PricingEngine()
        result = engine.calculate_price(100, 1, CustomerType.RETAIL)

        assert result.base_price == 100
        assert result.total == 113

    def test_calculate_vip_discount(self):
        """测试计算 VIP 折扣"""
        engine = PricingEngine()
        result = engine.calculate_price(1000, 10, CustomerType.VIP)

        assert result.discount > 0
        assert result.total < 10000

    def test_calculate_distributor_discount(self):
        """测试计算经销商折扣"""
        engine = PricingEngine()
        result = engine.calculate_price(2000, 10, CustomerType.DISTRIBUTOR)

        assert result.discount > 0

    def test_get_volume_tier(self):
        """测试获取批量等级"""
        engine = PricingEngine()

        assert engine.get_volume_tier(100) == "tier_3"
        assert engine.get_volume_tier(50) == "tier_4"
        assert engine.get_volume_tier(10) == "standard"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
