"""
基础设施层测试
"""

import pytest
from unittest.mock import MagicMock, patch
from app.infrastructure.documents.shipment_document_generator_impl import LegacyShipmentDocumentGenerator


class TestLegacyShipmentDocumentGenerator:
    """发货单文档生成器测试"""

    @patch("app.infrastructure.documents.shipment_document_generator_impl.resolve_purchase_unit")
    @patch("app.infrastructure.documents.shipment_document_generator_impl.load_legacy_shipment_document_generator")
    def test_generate_success(self, mock_loader, mock_resolve):
        resolved = MagicMock()
        resolved.unit_name = "测试单位"
        resolved.contact_person = "张三"
        resolved.contact_phone = "13800138000"
        resolved.address = "地址"
        resolved.id = 1
        mock_resolve.return_value = resolved

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
        loader_ns = MagicMock()
        loader_ns.ShipmentDocumentGenerator = ShipmentDocumentGenerator
        mock_loader.return_value = loader_ns

        gen = LegacyShipmentDocumentGenerator()
        result = gen.generate(unit_name="测试单位", products=[])

        assert result["success"] is True

    @patch("app.infrastructure.documents.shipment_document_generator_impl.resolve_purchase_unit")
    def test_generate_unit_not_found(self, mock_resolve):
        mock_resolve.return_value = None
        gen = LegacyShipmentDocumentGenerator()
        result = gen.generate(unit_name="未知单位", products=[])
        assert result["success"] is False