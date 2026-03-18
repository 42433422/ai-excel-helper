"""
产品导入服务单元测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from app.services.product_import_service import ProductImportService


class TestProductImportService:
    """产品导入服务测试"""

    @pytest.fixture
    def service(self):
        """创建产品导入服务实例"""
        return ProductImportService()

    class TestCleanData:
        """clean_data 方法测试"""

        def test_clean_data_strip_whitespace(self, service):
            """测试去除字符串两端空格"""
            data = [
                {"product_code": "  P001  ", "product_name": "  产品A  "},
                {"product_code": "P002", "product_name": "产品B"},
            ]
            result = service.clean_data(data)

            assert result[0]["product_code"] == "P001"
            assert result[0]["product_name"] == "产品A"
            assert result[1]["product_code"] == "P002"
            assert result[1]["product_name"] == "产品B"

        def test_clean_data_handle_empty_string(self, service):
            """测试处理空字符串为 None"""
            data = [
                {"product_code": "", "product_name": "产品A"},
                {"product_code": "P002", "product_name": ""},
                {"product_code": None, "product_name": "产品C"},
            ]
            result = service.clean_data(data)

            assert result[0]["product_code"] is None
            assert result[1]["product_name"] is None
            assert result[2]["product_code"] is None

        def test_clean_data_preserve_non_strings(self, service):
            """测试保留非字符串类型"""
            data = [
                {"product_code": "P001", "price": 100, "active": True},
                {"product_code": "P002", "price": 99.99, "active": False},
            ]
            result = service.clean_data(data)

            assert result[0]["price"] == 100
            assert result[0]["active"] is True
            assert result[1]["price"] == 99.99
            assert result[1]["active"] is False

        def test_clean_data_empty_list(self, service):
            """测试空列表"""
            result = service.clean_data([])
            assert result == []

    class TestValidateData:
        """validate_data 方法测试"""

        def test_validate_data_valid(self, service):
            """测试有效数据"""
            data = [
                {"product_code": "P001", "product_name": "产品A", "unit_price": 100},
                {"product_code": "P002", "product_name": "产品B", "unit_price": "50"},
            ]
            valid, invalid = service.validate_data(data)

            assert len(valid) == 2
            assert len(invalid) == 0

        def test_validate_data_missing_code_and_name(self, service):
            """测试产品编码和名称都为空"""
            data = [
                {"product_code": "", "product_name": "", "unit_price": 100},
                {"product_code": None, "product_name": None, "unit_price": 50},
            ]
            valid, invalid = service.validate_data(data)

            assert len(valid) == 0
            assert len(invalid) == 2
            assert "产品编码或产品名称不能同时为空" in invalid[0]["errors"]

        def test_validate_data_price_format(self, service):
            """测试价格格式验证"""
            data = [
                {"product_code": "P001", "product_name": "产品A", "unit_price": -10},
                {"product_code": "P002", "product_name": "产品B", "unit_price": "invalid"},
                {"product_code": "P003", "product_name": "产品C", "unit_price": 50},
            ]
            valid, invalid = service.validate_data(data)

            assert len(valid) == 1
            assert len(invalid) == 2

        def test_validate_data_partial_valid(self, service):
            """测试部分有效数据"""
            data = [
                {"product_code": "P001", "product_name": "产品A", "unit_price": 100},
                {"product_code": "", "product_name": "", "unit_price": 50},
            ]
            valid, invalid = service.validate_data(data)

            assert len(valid) == 1
            assert len(invalid) == 1

    class TestCheckDuplicates:
        """check_duplicates 方法测试"""

        @patch('app.services.product_import_service.Product')
        @patch('app.services.product_import_service.get_db')
        def test_check_duplicates_with_duplicates(self, mock_get_db, mock_product_class, service):
            """测试有重复产品"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_existing = Mock()
            mock_existing.id = 1

            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_existing,
                mock_existing,
            ]

            data = [
                {"product_code": "P001", "product_name": "产品A", "specification": "规格1"},
                {"product_code": "P002", "product_name": "产品B"},
            ]

            new_data, duplicates = service.check_duplicates(data, skip_duplicates=True)

            assert len(duplicates) == 2
            assert len(new_data) == 0

        @patch('app.services.product_import_service.Product')
        @patch('app.services.product_import_service.get_db')
        def test_check_duplicates_no_duplicates(self, mock_get_db, mock_product_class, service):
            """测试无重复产品"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_db.query.return_value.filter.return_value.first.return_value = None

            data = [
                {"product_code": "P001", "product_name": "产品A"},
                {"product_code": "P002", "product_name": "产品B"},
            ]

            new_data, duplicates = service.check_duplicates(data, skip_duplicates=True)

            assert len(new_data) == 2
            assert len(duplicates) == 0

        def test_check_duplicates_empty_data(self, service):
            """测试空数据"""
            new_data, duplicates = service.check_duplicates([], skip_duplicates=True)

            assert new_data == []
            assert duplicates == []

    class TestImportData:
        """import_data 方法测试"""

        @patch('app.services.product_import_service.Product')
        @patch('app.services.product_import_service.get_db')
        def test_import_data_normal(self, mock_get_db, mock_product_class, service):
            """测试正常导入"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            data = [
                {"product_code": "P001", "product_name": "产品A", "unit_price": 100, "unit": "个"},
            ]

            result = service.import_data(data, skip_duplicates=True, validate_before_import=True)

            assert result['imported'] == 1
            assert result['skipped'] == 0
            assert result['failed'] == 0

        @patch('app.services.product_import_service.Product')
        @patch('app.services.product_import_service.get_db')
        def test_import_data_skip_duplicates(self, mock_get_db, mock_product_class, service):
            """测试跳过重复产品"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db

            mock_existing = Mock()
            mock_existing.id = 1
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_existing,
                mock_existing,
            ]

            data = [
                {"product_code": "P001", "product_name": "产品A", "unit_price": 100},
                {"product_code": "P002", "product_name": "产品B", "unit_price": 50},
            ]

            result = service.import_data(data, skip_duplicates=True, validate_before_import=True)

            assert result['imported'] == 0
            assert result['skipped'] == 2

        def test_import_data_validation_failed(self, service):
            """测试数据验证失败"""
            data = [
                {"product_code": "", "product_name": "", "unit_price": 100},
            ]

            result = service.import_data(data, skip_duplicates=False, validate_before_import=True)

            assert result['imported'] == 0
            assert result['failed'] == 1

        def test_import_data_empty_data(self, service):
            """测试空数据处理"""
            result = service.import_data([], skip_duplicates=True, validate_before_import=True)

            assert result['imported'] == 0
            assert result['skipped'] == 0
            assert result['failed'] == 0

        @patch('app.services.product_import_service.Product')
        @patch('app.services.product_import_service.get_db')
        def test_import_data_batch_import(self, mock_get_db, mock_product_class, service):
            """测试批量导入"""
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            data = [
                {"product_code": f"P00{i}", "product_name": f"产品{i}", "unit_price": 100 * i, "unit": "个"}
                for i in range(1, 6)
            ]

            result = service.import_data(data, skip_duplicates=True, validate_before_import=True)

            assert result['imported'] == 5
            assert result['failed'] == 0


class TestProductImportServiceIntegration:
    """产品导入服务集成测试"""

    @pytest.fixture
    def mock_db_session(self):
        """创建 Mock 数据库会话"""
        db = MagicMock()
        db.add = Mock()
        db.commit = Mock()
        db.query = MagicMock()
        return db

    @pytest.fixture
    def sample_product_data(self):
        """示例产品数据"""
        return [
            {"product_code": "P001", "product_name": "产品A", "unit_price": 100, "unit": "个", "specification": "规格1"},
            {"product_code": "P002", "product_name": "产品B", "unit_price": 200, "unit": "箱", "specification": "规格2"},
            {"product_code": "P003", "product_name": "产品C", "unit_price": 150, "unit": "个"},
        ]

    @patch('app.services.product_import_service.Product')
    @patch('app.services.product_import_service.get_db')
    def test_full_import_workflow(self, mock_get_db, mock_product_class, sample_product_data):
        """测试完整导入工作流"""
        service = ProductImportService()

        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.import_data(
            sample_product_data,
            skip_duplicates=False,
            validate_before_import=True,
            clean_data=True
        )

        assert result['imported'] == 3
        assert result['skipped'] == 0
        assert result['failed'] == 0

    @patch('app.services.product_import_service.Product')
    @patch('app.services.product_import_service.get_db')
    def test_import_with_validation_and_duplicates(self, mock_get_db, mock_product_class):
        """测试带验证和重复检查的导入"""
        service = ProductImportService()

        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db

        mock_existing = Mock()
        mock_existing.id = 1
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_existing,
            mock_existing,
        ]

        data = [
            {"product_code": "P001", "product_name": "产品A", "unit_price": 100},
            {"product_code": "P002", "product_name": "产品B", "unit_price": 50},
        ]

        result = service.import_data(
            data,
            skip_duplicates=True,
            validate_before_import=True,
            clean_data=True
        )

        assert result['imported'] == 0
        assert result['skipped'] == 2

    @patch('app.services.product_import_service.Product')
    @patch('app.services.product_import_service.get_db')
    def test_import_without_validation(self, mock_get_db, mock_product_class):
        """测试不验证直接导入"""
        service = ProductImportService()

        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db

        data = [
            {"product_code": "", "product_name": "", "unit_price": 100},
        ]

        result = service.import_data(
            data,
            skip_duplicates=False,
            validate_before_import=False,
            clean_data=True
        )

        assert result['imported'] == 1

    def test_clean_validate_workflow(self):
        """测试清洗和验证工作流"""
        service = ProductImportService()

        data = [
            {"product_code": "  P001  ", "product_name": "产品A", "unit_price": 100},
            {"product_code": "", "product_name": "", "unit_price": -10},
        ]

        cleaned = service.clean_data(data)
        valid, invalid = service.validate_data(cleaned)

        assert len(cleaned) == 2
        assert cleaned[0]["product_code"] == "P001"
        assert len(valid) == 1
        assert len(invalid) == 1
