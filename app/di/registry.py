"""
Process-wide service registry (composition root).

Replaces scattered ``global _foo_service`` singletons with one replaceable container.
Tests: ``set_service_registry(CustomServiceContainer(...))`` or ``reset_service_registry()``.
"""

from __future__ import annotations

import threading
from typing import Any, Optional

_lock = threading.RLock()
_registry: Optional["ServiceContainer"] = None


class ServiceContainer:
    """Lazily constructed application and infrastructure services (single process)."""

    __slots__ = (
        "_session_service",
        "_auth_service",
        "_user_service",
        "_user_preference_service",
        "_customer_application_service",
        "_ai_chat_application_service",
        "_unit_products_import_application_service",
        "_file_analysis_application_service",
        "_wechat_contact_store",
        "_wechat_contact_application_service",
        "_shipment_application_service_core",
        "_shipment_event_primary_facade",
    )

    def __init__(self) -> None:
        self._session_service = None
        self._auth_service = None
        self._user_service = None
        self._user_preference_service = None
        self._customer_application_service = None
        self._ai_chat_application_service = None
        self._unit_products_import_application_service = None
        self._file_analysis_application_service = None
        self._wechat_contact_store = None
        self._wechat_contact_application_service = None
        self._shipment_application_service_core = None
        self._shipment_event_primary_facade = None

    # --- core HTTP / session services ---

    @property
    def session_service(self) -> Any:
        if self._session_service is None:
            from app.services.session_service import SessionService

            self._session_service = SessionService()
        return self._session_service

    @property
    def auth_service(self) -> Any:
        if self._auth_service is None:
            from app.services.auth_service import AuthService

            self._auth_service = AuthService()
        return self._auth_service

    @property
    def user_service(self) -> Any:
        if self._user_service is None:
            from app.services.user_service import UserService

            self._user_service = UserService()
        return self._user_service

    @property
    def user_preference_service(self) -> Any:
        if self._user_preference_service is None:
            from app.services.user_preference_service import UserPreferenceService

            self._user_preference_service = UserPreferenceService()
        return self._user_preference_service

    # --- application services (formerly module-level singletons) ---

    @property
    def customer_application_service(self) -> Any:
        if self._customer_application_service is None:
            from app.application.customer_app_service import CustomerApplicationService

            self._customer_application_service = CustomerApplicationService()
        return self._customer_application_service

    def invalidate_customer_application_service(self) -> None:
        self._customer_application_service = None

    @property
    def ai_chat_application_service(self) -> Any:
        if self._ai_chat_application_service is None:
            from app.application.ai_chat_app_service import AIChatApplicationService

            self._ai_chat_application_service = AIChatApplicationService()
        return self._ai_chat_application_service

    @property
    def unit_products_import_application_service(self) -> Any:
        if self._unit_products_import_application_service is None:
            from app.application.unit_products_import_app_service import UnitProductsImportService

            self._unit_products_import_application_service = UnitProductsImportService()
        return self._unit_products_import_application_service

    @property
    def file_analysis_application_service(self) -> Any:
        if self._file_analysis_application_service is None:
            from app.application.file_analysis_app_service import FileAnalysisService

            self._file_analysis_application_service = FileAnalysisService()
        return self._file_analysis_application_service

    @property
    def wechat_contact_application_service(self) -> Any:
        if self._wechat_contact_application_service is None:
            from app.application.wechat_contact_app_service import WechatContactApplicationService
            from app.infrastructure.persistence.wechat_contact_store_impl import (
                SQLAlchemyWechatContactStore,
            )

            if self._wechat_contact_store is None:
                self._wechat_contact_store = SQLAlchemyWechatContactStore()
            self._wechat_contact_application_service = WechatContactApplicationService(
                self._wechat_contact_store
            )
        return self._wechat_contact_application_service

    def invalidate_wechat_contact_application_service(self) -> None:
        self._wechat_contact_application_service = None
        self._wechat_contact_store = None

    # --- shipment (full infra wiring; parity with former bootstrap lru_cache) ---

    @property
    def shipment_application_service_core(self) -> Any:
        if self._shipment_application_service_core is None:
            from app.application.shipment_app_service import ShipmentApplicationService
            from app.infrastructure.documents.shipment_document_generator_impl import (
                LegacyShipmentDocumentGenerator,
            )
            from app.infrastructure.persistence.purchase_unit_query_impl import (
                SQLAlchemyPurchaseUnitQuery,
            )
            from app.infrastructure.persistence.shipment_record_command_impl import (
                SQLAlchemyShipmentRecordCommand,
            )
            from app.infrastructure.persistence.shipment_record_query_impl import (
                SQLAlchemyShipmentRecordQuery,
            )
            from app.infrastructure.persistence.shipment_record_store_impl import (
                SQLAlchemyShipmentRecordStore,
            )
            from app.mod_sdk.erp_repository_registry import resolve_shipment_repository

            shipment_repo, _provider = resolve_shipment_repository()

            self._shipment_application_service_core = ShipmentApplicationService(
                repository=shipment_repo,
                document_generator=LegacyShipmentDocumentGenerator(),
                record_store=SQLAlchemyShipmentRecordStore(),
                record_query=SQLAlchemyShipmentRecordQuery(),
                record_command=SQLAlchemyShipmentRecordCommand(),
                purchase_unit_query=SQLAlchemyPurchaseUnitQuery(),
            )
        return self._shipment_application_service_core

    @property
    def shipment_event_primary_facade(self) -> Any:
        if self._shipment_event_primary_facade is None:
            from app.application.facades.shipment_event_primary import (
                ShipmentApplicationServiceEventPrimary,
            )

            self._shipment_event_primary_facade = ShipmentApplicationServiceEventPrimary(
                self.shipment_application_service_core
            )
        return self._shipment_event_primary_facade

    def invalidate_shipment_wiring(self) -> None:
        """Clear shipment singletons (tests / hot-reload hooks)."""
        self._shipment_application_service_core = None
        self._shipment_event_primary_facade = None


def get_service_registry() -> ServiceContainer:
    global _registry
    with _lock:
        if _registry is None:
            _registry = ServiceContainer()
        return _registry


def set_service_registry(container: Optional[ServiceContainer]) -> None:
    """Replace the entire registry (tests). Pass ``None`` to drop the current container."""
    global _registry
    with _lock:
        _registry = container


def reset_service_registry() -> None:
    """Drop the registry so the next ``get_service_registry()`` builds a fresh container."""
    set_service_registry(None)
