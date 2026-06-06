# -*- coding: utf-8 -*-
"""里程碑 L+：Mod 侧仓储适配器（显式类型 + 透明委托，可整体替换 inner）。"""

from __future__ import annotations

from typing import Any

PROVIDER_ID = "mod:xcagi-erp-domain-bridge"
ADAPTER_KIND = "mod_delegated"
ADAPTER_KIND_SESSION = "mod_session_facade"
DELEGATE_PRODUCTS = "host.SQLAlchemyProductRepository"
DELEGATE_SHIPMENT = "host.SQLAlchemyShipmentRepository"
DELEGATE_CUSTOMERS_SESSION = "host.app.db.SessionLocal"


def repository_adapter_meta(adapter_class: str) -> dict[str, str]:
    return {
        "provider_id": PROVIDER_ID,
        "adapter_kind": ADAPTER_KIND,
        "adapter_class": adapter_class,
    }


class ModProductRepositoryAdapter:
    """L+ 产品仓储：包装宿主 SQLAlchemy 实现，保留 ProductRepository 端口。"""

    provider_id = PROVIDER_ID
    adapter_kind = ADAPTER_KIND
    delegate = DELEGATE_PRODUCTS

    def __init__(self, inner: Any | None = None) -> None:
        if inner is None:
            from app.infrastructure.persistence.product_repository_impl import (
                SQLAlchemyProductRepository,
            )

            inner = SQLAlchemyProductRepository()
        self._inner = inner

    def meta(self) -> dict[str, str]:
        return repository_adapter_meta(type(self).__name__)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class ModShipmentRepositoryAdapter:
    """L+ 出货仓储：包装宿主 SQLAlchemy 实现。"""

    provider_id = PROVIDER_ID
    adapter_kind = ADAPTER_KIND
    delegate = DELEGATE_SHIPMENT

    def __init__(self, inner: Any | None = None) -> None:
        if inner is None:
            from app.infrastructure.repositories.shipment_repository_impl import (
                SQLAlchemyShipmentRepository,
            )

            inner = SQLAlchemyShipmentRepository()
        self._inner = inner

    def meta(self) -> dict[str, str]:
        return repository_adapter_meta(type(self).__name__)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class ModCustomersSessionAdapter:
    """L++ 客户域 session：经 Mod 边界解析，仍委托宿主 mod-aware SessionLocal。"""

    provider_id = PROVIDER_ID
    adapter_kind = ADAPTER_KIND_SESSION
    delegate = DELEGATE_CUSTOMERS_SESSION

    def meta(self) -> dict[str, str]:
        return repository_adapter_meta(type(self).__name__)

    def resolve(self):
        """与宿主 ``get_customers_session`` 一致：返回已打开的 ORM session。"""
        from app.db import SessionLocal

        return SessionLocal()


def list_adapter_classes() -> list[str]:
    return [
        ModProductRepositoryAdapter.__name__,
        ModShipmentRepositoryAdapter.__name__,
        ModCustomersSessionAdapter.__name__,
    ]
