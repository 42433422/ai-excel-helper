"""Composition-root style service registry (test-replaceable, single process scope)."""

from app.di.registry import (
    ServiceContainer,
    get_service_registry,
    reset_service_registry,
    set_service_registry,
)

__all__ = [
    "ServiceContainer",
    "get_service_registry",
    "reset_service_registry",
    "set_service_registry",
]
