# -*- coding: utf-8 -*-
"""
应用层端口接口

定义仓储和服务的抽象接口。
"""

from app.application.ports.extract_log_store import ExtractLogStorePort
from app.application.ports.file_analysis import FileAnalysisPort
from app.application.ports.material_repository import MaterialRepository
from app.application.ports.product_repository import ProductRepository
from app.application.ports.purchase_unit_query import PurchaseUnitQueryPort
from app.application.ports.shipment_document_generator import ShipmentDocumentGeneratorPort
from app.application.ports.shipment_record_command import ShipmentRecordCommandPort
from app.application.ports.shipment_record_query import ShipmentRecordQueryPort
from app.application.ports.shipment_record_store import ShipmentRecordStorePort
from app.application.ports.shipment_repository import ShipmentRepository
from app.application.ports.template_store import TemplateStorePort
from app.application.ports.wechat_contact_store import WechatContactStorePort

__all__ = [
    "MaterialRepository",
    "ProductRepository",
    "ShipmentRepository",
    "ShipmentDocumentGeneratorPort",
    "ShipmentRecordCommandPort",
    "ShipmentRecordQueryPort",
    "ShipmentRecordStorePort",
    "PurchaseUnitQueryPort",
    "TemplateStorePort",
    "WechatContactStorePort",
    "ExtractLogStorePort",
    "FileAnalysisPort",
]
