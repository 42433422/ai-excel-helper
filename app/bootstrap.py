"""
Composition Root / 装配入口

应用服务与基础设施的默认装配。与 ``app.di.registry.ServiceContainer`` 对齐：
发货与客户 / AI 聊天等「重型」单例由注册表持有；本模块保留若干 ``lru_cache`` 装配
（模板、材质、产品等），并逐步与 ``get_service_registry()`` 收敛。
"""

from __future__ import annotations

import os
from functools import lru_cache

from app.application.shipment_app_service import ShipmentApplicationService
from app.application.template_app_service import TemplateApplicationService
from app.services.extract_log_service import ExtractLogService
from app.services.materials_service import MaterialsService
from app.services.product_import_service import ProductImportService
from app.services.products_service import ProductsService

# Intent recognition is now provided by domain layer - see get_intent_recognition_service()
# in app/domain/services/intent_recognition_service.py


def get_shipment_application_service_core() -> ShipmentApplicationService:
    """Direct shipment application service (no NeuroBus). Handlers must use this to avoid recursion."""
    from app.di.registry import get_service_registry

    return get_service_registry().shipment_application_service_core


def _get_shipment_app_service_event_primary():
    from app.di.registry import get_service_registry

    return get_service_registry().shipment_event_primary_facade


def get_shipment_app_service():
    """
    Default entry for routes. When ``XCAGI_EVENT_PRIMARY`` or ``XCAGI_EVENT_PRIMARY_SHIPMENT``
    is set, returns the event-primary facade; otherwise the core service.
    """
    from app.contexts.flags import is_event_primary_enabled

    if is_event_primary_enabled("shipment"):
        return _get_shipment_app_service_event_primary()
    return get_shipment_application_service_core()


@lru_cache(maxsize=1)
def get_template_app_service() -> TemplateApplicationService:
    from app.infrastructure.templates.template_store_impl import FileSystemTemplateStore

    base_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(base_dir)
    return TemplateApplicationService(FileSystemTemplateStore(base_dir=base_dir))


def get_wechat_contact_app_service():
    from app.application.wechat_contact_app_service import get_wechat_contact_app_service as g

    return g()


@lru_cache(maxsize=1)
def get_materials_service() -> MaterialsService:
    from app.infrastructure.persistence.material_repository_impl import SQLAlchemyMaterialRepository

    service = MaterialsService()
    service.set_repository(SQLAlchemyMaterialRepository())
    return service


@lru_cache(maxsize=1)
def get_products_service() -> ProductsService:
    from app.mod_sdk.erp_repository_registry import resolve_products_repository

    service = ProductsService()
    repo, _provider = resolve_products_repository()
    service.set_repository(repo)
    return service


def get_customer_app_service():
    from app.application.customer_app_service import get_customer_app_service as g

    return g()


@lru_cache(maxsize=1)
def get_extract_log_service() -> ExtractLogService:
    return ExtractLogService()


@lru_cache(maxsize=1)
def get_product_import_service() -> ProductImportService:
    return ProductImportService()


def get_ai_chat_app_service():
    from app.application.ai_chat_app_service import get_ai_chat_app_service as g

    return g()


def get_file_analysis_service():
    from app.application.file_analysis_app_service import get_file_analysis_app_service as g

    return g()


def get_unit_products_import_service():
    from app.application.unit_products_import_app_service import (
        get_unit_products_import_app_service as g,
    )

    return g()
