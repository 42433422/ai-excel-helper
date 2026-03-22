"""
Composition Root / 装配入口

用于把应用层（Use Case）与基础设施实现绑定起来，避免 application 反向依赖 infrastructure。
"""

from __future__ import annotations

import os
from functools import lru_cache

from app.application.ai_chat_app_service import AIChatApplicationService
from app.application.customer_app_service import CustomerApplicationService
from app.application.file_analysis_app_service import FileAnalysisService
from app.application.shipment_app_service import ShipmentApplicationService
from app.application.template_app_service import TemplateApplicationService
from app.application.unit_products_import_app_service import UnitProductsImportService
from app.application.wechat_contact_app_service import WechatContactApplicationService
from app.infrastructure.documents.shipment_document_generator_impl import (
    LegacyShipmentDocumentGenerator,
)
from app.infrastructure.persistence.purchase_unit_query_impl import SQLAlchemyPurchaseUnitQuery
from app.infrastructure.persistence.shipment_record_command_impl import (
    SQLAlchemyShipmentRecordCommand,
)
from app.infrastructure.persistence.shipment_record_query_impl import SQLAlchemyShipmentRecordQuery
from app.infrastructure.persistence.shipment_record_store_impl import SQLAlchemyShipmentRecordStore
from app.infrastructure.persistence.wechat_contact_store_impl import SQLAlchemyWechatContactStore
from app.infrastructure.repositories.shipment_repository_impl import SQLAlchemyShipmentRepository
from app.infrastructure.templates.template_store_impl import FileSystemTemplateStore
from app.services.extract_log_service import ExtractLogService
from app.services.materials_service import MaterialsService
from app.services.product_import_service import ProductImportService
from app.services.products_service import ProductsService


@lru_cache(maxsize=1)
def get_shipment_app_service() -> ShipmentApplicationService:
    return ShipmentApplicationService(
        repository=SQLAlchemyShipmentRepository(),
        document_generator=LegacyShipmentDocumentGenerator(),
        record_store=SQLAlchemyShipmentRecordStore(),
        record_query=SQLAlchemyShipmentRecordQuery(),
        record_command=SQLAlchemyShipmentRecordCommand(),
        purchase_unit_query=SQLAlchemyPurchaseUnitQuery(),
    )


@lru_cache(maxsize=1)
def get_template_app_service() -> TemplateApplicationService:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(base_dir)
    return TemplateApplicationService(FileSystemTemplateStore(base_dir=base_dir))


@lru_cache(maxsize=1)
def get_wechat_contact_app_service() -> WechatContactApplicationService:
    return WechatContactApplicationService(store=SQLAlchemyWechatContactStore())


@lru_cache(maxsize=1)
def get_materials_service() -> MaterialsService:
    from app.infrastructure.persistence.material_repository_impl import SQLAlchemyMaterialRepository
    service = MaterialsService()
    service.set_repository(SQLAlchemyMaterialRepository())
    return service


@lru_cache(maxsize=1)
def get_products_service() -> ProductsService:
    from app.infrastructure.persistence.product_repository_impl import SQLAlchemyProductRepository
    service = ProductsService()
    service.set_repository(SQLAlchemyProductRepository())
    return service


@lru_cache(maxsize=1)
def get_customer_app_service() -> CustomerApplicationService:
    return CustomerApplicationService()


@lru_cache(maxsize=1)
def get_extract_log_service() -> ExtractLogService:
    return ExtractLogService()


@lru_cache(maxsize=1)
def get_product_import_service() -> ProductImportService:
    return ProductImportService()


@lru_cache(maxsize=1)
def get_ai_chat_app_service() -> AIChatApplicationService:
    return AIChatApplicationService()


@lru_cache(maxsize=1)
def get_file_analysis_service() -> FileAnalysisService:
    return FileAnalysisService()


@lru_cache(maxsize=1)
def get_unit_products_import_service() -> UnitProductsImportService:
    return UnitProductsImportService()
