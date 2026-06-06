"""FastAPI ``Depends`` helpers bound to ``request.app.state.services``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Request

if TYPE_CHECKING:
    from app.di.registry import ServiceContainer


def get_service_container(request: Request) -> "ServiceContainer":
    c = getattr(request.app.state, "services", None)
    if c is None:
        from app.di.registry import get_service_registry

        return get_service_registry()
    return c


ServiceContainerDep = Annotated["ServiceContainer", get_service_container]
