"""
应用服务层测试
"""

import pytest
from unittest.mock import MagicMock, patch
from app.application.shipment_app_service import ShipmentApplicationService
from app.domain.shipment.aggregates import Shipment, ShipmentItem
from app.domain.value_objects import Money, Quantity, ContactInfo


class DummyRepository:
    """简单内存仓储"""

    def __init__(self):
        self._items = {}
        self._id = 1

    def save(self, shipment: Shipment) -> Shipment:
        if shipment.id is None:
            shipment.id = self._id
            self._id += 1
        self._items[shipment.id] = shipment
        return shipment

    def find_by_id(self, shipment_id: int):
        return self._items.get(shipment_id)

    def find_all(self, page: int = 1, per_page: int = 20):
        return list(self._items.values())

    def find_by_unit(self, unit_name: str):
        return [s for s in self._items.values() if s.purchase_unit_name == unit_name]

    def count(self) -> int:
        return len(self._items)

    def delete(self, shipment_id: int) -> bool:
        return self._items.pop(shipment_id, None) is not None


class DummyDocumentGenerator:
    """简单文档生成器 mock"""

    def __init__(self, success: bool = True):
        self._success = success
        self.call_count = 0

    def generate(self, unit_name: str, products: list, **kwargs) -> dict:
        self.call_count += 1
        if self._success:
            return {
                "success": True,
                "doc_name": f"{unit_name}_shipment.xlsx",
                "file_path": f"/tmp/{unit_name}_shipment.xlsx",
                "purchase_unit": unit_name,
                "unit_id": 1,
            }
        return {
            "success": False,
            "message": "生成失败",
        }


class DummyRecordStore:
    """简单记录存储 mock"""

    def __init__(self):
        self.recorded = []

    def record_document_generation(self, **kwargs):
        self.recorded.append(kwargs)


class TestShipmentApplicationServiceCreate:
    """创建发货单测试"""

    def test_create_shipment_success(self):
        repo = DummyRepository()
        app_service = ShipmentApplicationService(
            repository=repo,
            document_generator=None,
            record_store=None,
        )

        items = [
            {
                "product_name": "产品A",
                "model_number": "9803",
                "quantity_tins": 3,
                "tin_spec": 20.0,
                "unit_price": 10.0,
                "amount": 600.0,
            }
        ]

        result = app_service.create_shipment(
            unit_name="测试单位",
            items_data=items,
            contact_person="张三",
            contact_phone="13800138000",
        )

        assert result["success"] is True
        shipment_dict = result["shipment"]
        assert shipment_dict["purchase_unit"] == "测试单位"
        assert len(shipment_dict["items"]) == 1
        assert shipment_dict["total_quantity_tins"] == 3

    def test_create_shipment_invalid_no_items(self):
        repo = DummyRepository()
        app_service = ShipmentApplicationService(
            repository=repo,
            document_generator=None,
            record_store=None,
        )

        result = app_service.create_shipment(
            unit_name="测试单位",
            items_data=[],
            contact_person="张三",
            contact_phone="13800138000",
        )

        assert result["success"] is False
        assert "无效" in result["message"]

    def test_create_shipment_invalid_no_unit_name(self):
        repo = DummyRepository()
        app_service = ShipmentApplicationService(
            repository=repo,
            document_generator=None,
            record_store=None,
        )

        items = [{"product_name": "产品A", "quantity_tins": 1}]
        result = app_service.create_shipment(
            unit_name="",
            items_data=items,
        )

        assert result["success"] is False

    def test_create_shipment_with_multiple_items(self):
        repo = DummyRepository()
        app_service = ShipmentApplicationService(
            repository=repo,
            document_generator=None,
            record_store=None,
        )

        items = [
            {
                "product_name": "产品A",
                "quantity_tins": 3,
                "tin_spec": 20.0,
                "unit_price": 10.0,
                "amount": 600.0,
            },
            {
                "product_name": "产品B",
                "quantity_tins": 2,
                "tin_spec": 10.0,
                "unit_price": 20.0,
                "amount": 400.0,
            },
        ]

        result = app_service.create_shipment(
            unit_name="测试单位",
            items_data=items,
        )

        assert result["success"] is True
        shipment_dict = result["shipment"]
        assert len(shipment_dict["items"]) == 2
        assert shipment_dict["total_quantity_tins"] == 5
        assert shipment_dict["total_quantity_kg"] == 80.0


class TestShipmentApplicationServiceGenerate:
    """生成发货单文档测试"""

    def test_generate_shipment_document_success(self):
        repo = DummyRepository()
        doc_gen = DummyDocumentGenerator(success=True)
        record_store = DummyRecordStore()

        app_service = ShipmentApplicationService(
            repository=repo,
            document_generator=doc_gen,
            record_store=record_store,
        )

        products = [
            {"product_name": "产品A", "quantity_tins": 1, "tin_spec": 20.0}
        ]

        result = app_service.generate_shipment_document(
            unit_name="测试单位",
            products=products,
            template_name=None,
        )

        assert result["success"] is True
        assert "doc_name" in result
        assert doc_gen.call_count == 1
        assert len(record_store.recorded) == 1

    def test_generate_shipment_document_fail(self):
        repo = DummyRepository()
        doc_gen = DummyDocumentGenerator(success=False)
        record_store = DummyRecordStore()

        app_service = ShipmentApplicationService(
            repository=repo,
            document_generator=doc_gen,
            record_store=record_store,
        )

        products = [{"product_name": "产品A", "quantity_tins": 1}]

        result = app_service.generate_shipment_document(
            unit_name="测试单位",
            products=products,
        )

        assert result["success"] is False
        assert "message" in result


class TestShipmentApplicationServiceList:
    """列表查询测试"""

    def test_list_shipments(self):
        repo = DummyRepository()
        app_service = ShipmentApplicationService(
            repository=repo,
            document_generator=None,
            record_store=None,
        )

        repo.save(Shipment.create(unit_name="单位A"))
        repo.save(Shipment.create(unit_name="单位B"))

        result = app_service.list_shipments(page=1, per_page=20)

        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) == 2

    def test_get_shipment_by_id(self):
        repo = DummyRepository()
        app_service = ShipmentApplicationService(
            repository=repo,
            document_generator=None,
            record_store=None,
        )

        saved = repo.save(Shipment.create(unit_name="测试单位"))

        result = app_service.get_shipment(shipment_id=saved.id)

        assert result is not None
        assert result.purchase_unit_name == "测试单位"

    def test_get_shipment_not_found(self):
        repo = DummyRepository()
        app_service = ShipmentApplicationService(
            repository=repo,
            document_generator=None,
            record_store=None,
        )

        result = app_service.get_shipment(shipment_id=999)

        assert result is None


class TestShipmentApplicationServiceDelete:
    """删除发货单测试"""

    def test_delete_shipment_success(self):
        repo = DummyRepository()
        app_service = ShipmentApplicationService(
            repository=repo,
            document_generator=None,
            record_store=None,
        )

        saved = repo.save(Shipment.create(unit_name="测试单位"))

        result = app_service.delete_shipment(shipment_id=saved.id)

        assert result["success"] is True
        assert repo.count() == 0

    def test_delete_shipment_not_found(self):
        repo = DummyRepository()
        app_service = ShipmentApplicationService(
            repository=repo,
            document_generator=None,
            record_store=None,
        )

        result = app_service.delete_shipment(shipment_id=999)

        assert result["success"] is False