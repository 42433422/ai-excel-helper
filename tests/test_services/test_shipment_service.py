"""
发货单服务与文档生成适配器测试
"""

from unittest.mock import MagicMock, patch

import pytest

from app.application.shipment_app_service import ShipmentApplicationService
from app.domain.shipment.aggregates import ShipmentItem, Shipment
from app.domain.value_objects import ContactInfo, Quantity, Money
from app.infrastructure.documents.shipment_document_generator_impl import (
    LegacyShipmentDocumentGenerator,
)


class DummyRepo:
    """简单内存仓储，用于 ApplicationService 单元测试。"""

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


class TestShipmentApplicationService:
    """ApplicationService 层用例测试。"""

    def test_create_shipment_success(self):
        repo = DummyRepo()
        app_service = ShipmentApplicationService(repository=repo, document_generator=None, record_store=None)

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
        repo = DummyRepo()
        app_service = ShipmentApplicationService(repository=repo, document_generator=None, record_store=None)

        result = app_service.create_shipment(
            unit_name="测试单位",
            items_data=[],
            contact_person="张三",
            contact_phone="13800138000",
        )

        assert result["success"] is False
        assert "无效" in result["message"]

    def test_generate_shipment_document_calls_record_store(self):
        repo = DummyRepo()
        dummy_doc_gen = MagicMock()
        dummy_doc_gen.generate.return_value = {
            "success": True,
            "doc_name": "test.xlsx",
            "file_path": "/tmp/test.xlsx",
            "purchase_unit": "测试单位",
            "unit_id": 1,
        }
        dummy_store = MagicMock()

        app_service = ShipmentApplicationService(
            repository=repo,
            document_generator=dummy_doc_gen,
            record_store=dummy_store,
        )

        result = app_service.generate_shipment_document(
            unit_name="测试单位",
            products=[{"product_name": "产品A", "quantity": 1}],
        )

        assert result["success"] is True
        dummy_doc_gen.generate.assert_called_once()
        dummy_store.record_document_generation.assert_called_once()


class TestLegacyShipmentDocumentGenerator:
    """Legacy 文档生成适配器测试（mock legacy 依赖）。"""

    @patch("app.infrastructure.documents.shipment_document_generator_impl.load_legacy_shipment_document_generator")
    @patch("app.infrastructure.documents.shipment_document_generator_impl.resolve_purchase_unit")
    def test_generate_success_with_valid_products(self, mock_resolve_unit, mock_loader):
        # 配置单位解析
        resolved = MagicMock()
        resolved.unit_name = "测试单位"
        resolved.contact_person = "张三"
        resolved.contact_phone = "13800138000"
        resolved.address = "地址"
        resolved.id = 1
        mock_resolve_unit.return_value = resolved

        # 配置 legacy 生成器
        fake_doc = MagicMock()
        fake_doc.to_dict.return_value = {
            "filename": "test.xlsx",
            "filepath": "/tmp/test.xlsx",
            "order_number": "ORD1",
            "total_amount": 100.0,
            "total_quantity": 60.0,
        }
        ShipmentDocumentGenerator = MagicMock()
        ShipmentDocumentGenerator.return_value.generate_document.return_value = fake_doc
        PurchaseUnitInfo = MagicMock()
        loader_ns = MagicMock()
        loader_ns.ShipmentDocumentGenerator = ShipmentDocumentGenerator
        loader_ns.PurchaseUnitInfo = PurchaseUnitInfo
        mock_loader.return_value = loader_ns

        gen = LegacyShipmentDocumentGenerator()
        products = [
            {
                "product_name": "产品A",
                "model_number": "9803",
                "quantity_tins": 3,
                "tin_spec": 20.0,
                "unit_price": 10.0,
            }
        ]

        result = gen.generate(unit_name="测试单位", products=products)

        assert result["success"] is True
        assert result["doc_name"] == "test.xlsx"
        ShipmentDocumentGenerator.assert_called_once()

    @patch("app.infrastructure.documents.shipment_document_generator_impl.resolve_purchase_unit")
    def test_generate_fail_when_unit_not_resolved(self, mock_resolve_unit):
        mock_resolve_unit.return_value = None
        gen = LegacyShipmentDocumentGenerator()
        result = gen.generate(unit_name="未知单位", products=[])
        assert result["success"] is False
        assert "未找到购买单位" in result["message"]


class TestShipmentAppServiceGenerate:
    """ShipmentApplicationService.generate_shipment_document 路径测试。"""

    @patch("app.infrastructure.documents.shipment_document_generator_impl.load_legacy_shipment_document_generator")
    @patch("app.infrastructure.documents.shipment_document_generator_impl.resolve_purchase_unit")
    @patch("app.infrastructure.persistence.shipment_record_store_impl.resolve_purchase_unit")
    def test_generate_document_success(
        self, mock_record_resolve, mock_doc_resolve, mock_loader
    ):
        resolved = MagicMock()
        resolved.unit_name = "测试单位"
        resolved.id = 1
        resolved.contact_person = "张三"
        resolved.contact_phone = "13800138000"
        resolved.address = "地址"
        mock_doc_resolve.return_value = resolved
        mock_record_resolve.return_value = resolved

        fake_doc = MagicMock()
        fake_doc.to_dict.return_value = {
            "filename": "test.xlsx",
            "filepath": "/tmp/test.xlsx",
        }
        gen_cls = MagicMock()
        gen_cls.return_value.generate_document.return_value = fake_doc
        loader_ns = MagicMock()
        loader_ns.ShipmentDocumentGenerator = gen_cls
        mock_loader.return_value = loader_ns

        repo = DummyRepo()
        app_service = ShipmentApplicationService(
            repository=repo,
            document_generator=LegacyShipmentDocumentGenerator(),
            record_store=MagicMock(),
        )
        result = app_service.generate_shipment_document(
            unit_name="测试单位",
            products=[{"product_name": "产品A", "quantity": 1}],
        )

        assert result["success"] is True
        assert result["doc_name"] == "test.xlsx"

