"""
发货单领域聚合测试
"""

import pytest
from datetime import datetime
from app.domain.shipment.aggregates import ShipmentItem, Shipment
from app.domain.value_objects import Money, Quantity, ContactInfo, OrderNumber


class TestShipmentItem:
    """ShipmentItem 实体测试"""

    def test_create_shipment_item_success(self):
        item = ShipmentItem(
            product_name="产品A",
            model_number="9803",
            quantity=Quantity.from_tins_and_spec(3, 20.0),
            unit_price=Money(100.0),
            amount=Money(600.0),
        )
        assert item.product_name == "产品A"
        assert item.model_number == "9803"
        assert item.quantity.tins == 3
        assert item.quantity.kg == 60.0

    def test_create_shipment_item_empty_name_raises_error(self):
        with pytest.raises(ValueError, match="产品名称不能为空"):
            ShipmentItem(product_name="")

    def test_calculate_amount(self):
        item = ShipmentItem(
            product_name="产品A",
            quantity=Quantity.from_tins_and_spec(3, 20.0),
            unit_price=Money(10.0),
        )
        amount = item.calculate_amount()
        assert amount.amount == 60.0

    def test_shipment_item_to_dict(self):
        item = ShipmentItem(
            id=1,
            product_name="产品A",
            model_number="9803",
            quantity=Quantity.from_tins_and_spec(3, 20.0),
            unit_price=Money(100.0),
            amount=Money(600.0),
        )
        d = item.to_dict()
        assert d["product_name"] == "产品A"
        assert d["model_number"] == "9803"
        assert d["quantity_tins"] == 3
        assert d["quantity_kg"] == 60.0
        assert d["spec_per_tin"] == 20.0
        assert d["unit_price"] == 100.0
        assert d["amount"] == 600.0

    def test_shipment_item_from_dict(self):
        data = {
            "id": 1,
            "product_name": "产品A",
            "model_number": "9803",
            "quantity_tins": 3,
            "tin_spec": 20.0,
            "unit_price": 100.0,
            "amount": 600.0,
        }
        item = ShipmentItem.from_dict(data)
        assert item.product_name == "产品A"
        assert item.quantity.tins == 3
        assert item.unit_price.amount == 100.0


class TestShipment:
    """Shipment 聚合根测试"""

    def test_create_shipment(self):
        shipment = Shipment.create(unit_name="测试单位")
        assert shipment.purchase_unit_name == "测试单位"
        assert shipment.status == "pending"
        assert len(shipment.items) == 0

    def test_create_shipment_with_contact_info(self):
        contact = ContactInfo(person="张三", phone="13800138000", address="测试地址")
        shipment = Shipment.create(unit_name="测试单位", contact_info=contact)
        assert shipment.contact_info.person == "张三"
        assert shipment.contact_info.phone == "13800138000"

    def test_create_shipment_empty_name_raises_error(self):
        with pytest.raises(ValueError, match="购买单位不能为空"):
            Shipment(purchase_unit_name="")

    def test_add_item(self):
        shipment = Shipment.create(unit_name="测试单位")
        item = ShipmentItem(
            product_name="产品A",
            quantity=Quantity.from_tins_and_spec(3, 20.0),
            unit_price=Money(10.0),
        )
        shipment.add_item(item)
        assert len(shipment.items) == 1
        assert shipment.total_quantity.tins == 3

    def test_add_multiple_items_recalculates_totals(self):
        shipment = Shipment.create(unit_name="测试单位")
        item1 = ShipmentItem(
            product_name="产品A",
            quantity=Quantity.from_tins_and_spec(3, 20.0),
            unit_price=Money(10.0),
            amount=Money(600.0),
        )
        item2 = ShipmentItem(
            product_name="产品B",
            quantity=Quantity.from_tins_and_spec(2, 10.0),
            unit_price=Money(20.0),
            amount=Money(400.0),
        )
        shipment.add_item(item1)
        shipment.add_item(item2)
        assert len(shipment.items) == 2
        assert shipment.total_quantity.tins == 5
        assert shipment.total_amount.amount == 1000.0

    def test_remove_item(self):
        shipment = Shipment.create(unit_name="测试单位")
        item = ShipmentItem(
            product_name="产品A",
            quantity=Quantity.from_tins_and_spec(3, 20.0),
            unit_price=Money(10.0),
        )
        shipment.add_item(item)
        removed = shipment.remove_item(0)
        assert len(shipment.items) == 0
        assert removed.product_name == "产品A"

    def test_remove_item_invalid_index(self):
        shipment = Shipment.create(unit_name="测试单位")
        with pytest.raises(IndexError, match="索引超出范围"):
            shipment.remove_item(0)

    def test_mark_as_printed(self):
        shipment = Shipment.create(unit_name="测试单位")
        shipment.mark_as_printed(printer_name="TSC打印机")
        assert shipment.status == "printed"
        assert shipment.printer_name == "TSC打印机"
        assert shipment.printed_at is not None

    def test_cancel(self):
        shipment = Shipment.create(unit_name="测试单位")
        shipment.cancel()
        assert shipment.status == "cancelled"

    def test_is_valid(self):
        shipment = Shipment.create(unit_name="测试单位")
        assert shipment.is_valid() is False
        item = ShipmentItem(
            product_name="产品A",
            quantity=Quantity.from_tins_and_spec(1, 10.0),
            unit_price=Money(10.0),
        )
        shipment.add_item(item)
        assert shipment.is_valid() is True

    def test_shipment_to_dict(self):
        shipment = Shipment.create(unit_name="测试单位")
        item = ShipmentItem(
            product_name="产品A",
            quantity=Quantity.from_tins_and_spec(3, 20.0),
            unit_price=Money(10.0),
            amount=Money(600.0),
        )
        shipment.add_item(item)
        d = shipment.to_dict()
        assert d["purchase_unit"] == "测试单位"
        assert len(d["items"]) == 1
        assert d["total_quantity_tins"] == 3
        assert d["status"] == "pending"