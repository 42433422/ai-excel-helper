"""Domain layer: aggregates, value objects, domain services, and ports."""

from __future__ import annotations

import importlib
from typing import Any

# Lazy submodules avoid import cycles and keep ``import app.domain`` lightweight.
_PUBLIC = frozenset(
    {
        "approval",
        "context",
        "customer",
        "neuro",
        "ports",
        "product",
        "services",
        "shipment",
        "value_objects",
    }
)

__all__ = tuple(sorted(_PUBLIC))


def __getattr__(name: str) -> Any:
    if name in _PUBLIC:
        return importlib.import_module(f"app.domain.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
