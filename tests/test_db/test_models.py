"""
DB Models 测试
"""

import pytest
from app.db.models.customer import Customer
from app.db.models.product import Product
from app.db.models.shipment import ShipmentRecord


class TestCustomerModel:
    """客户模型测试"""

    def test_customer_class_exists(self):
        assert Customer is not None
        assert hasattr(Customer, "__tablename__")

    def test_customer_columns_exist(self):
        assert hasattr(Customer, "id")
        assert hasattr(Customer, "unit_name")
        assert hasattr(Customer, "contact")
        assert hasattr(Customer, "phone")


class TestProductModel:
    """产品模型测试"""

    def test_product_class_exists(self):
        assert Product is not None
        assert hasattr(Product, "__tablename__")

    def test_product_columns_exist(self):
        assert hasattr(Product, "id")
        assert hasattr(Product, "name")
        assert hasattr(Product, "price")
        assert hasattr(Product, "model_number")


class TestShipmentRecordModel:
    """发货记录模型测试"""

    def test_shipment_record_class_exists(self):
        assert ShipmentRecord is not None
        assert hasattr(ShipmentRecord, "__tablename__")

    def test_shipment_record_columns_exist(self):
        assert hasattr(ShipmentRecord, "id")
        assert hasattr(ShipmentRecord, "unit_name")
        assert hasattr(ShipmentRecord, "status")