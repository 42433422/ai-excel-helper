"""
Code-first bounded context manifest: BC id, event prefixes, domain aggregates (paths), handler modules.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoundedContextMeta:
    context_id: str
    event_prefixes: tuple[str, ...]
    aggregate_paths: tuple[str, ...]
    handler_module: str


BOUNDED_CONTEXTS: tuple[BoundedContextMeta, ...] = (
    BoundedContextMeta(
        context_id="shipment",
        event_prefixes=("shipment.",),
        aggregate_paths=("app.domain.shipment.aggregates",),
        handler_module="app.neuro_bus.domains.shipment_domain_handlers",
    ),
    BoundedContextMeta(
        context_id="order",
        event_prefixes=("order.",),
        aggregate_paths=("app.domain.order",),
        handler_module="app.neuro_bus.domains.order_domain_handlers",
    ),
    BoundedContextMeta(
        context_id="inventory",
        event_prefixes=("inventory.",),
        aggregate_paths=("app.domain.inventory", "app.services.inventory_service"),
        handler_module="app.neuro_bus.domains.inventory_domain_handlers",
    ),
    BoundedContextMeta(
        context_id="product",
        event_prefixes=("product.",),
        aggregate_paths=("app.domain.product",),
        handler_module="app.neuro_bus.domains.product_domain_handlers",
    ),
    BoundedContextMeta(
        context_id="customer",
        event_prefixes=("customer.",),
        aggregate_paths=("app.domain.customer",),
        handler_module="app.neuro_bus.domains.customer_domain_handlers",
    ),
    BoundedContextMeta(
        context_id="intent",
        event_prefixes=("intent.",),
        aggregate_paths=("app.domain.services.intent",),
        handler_module="app.neuro_bus.domains.intent_domain",
    ),
)


def contexts_by_id() -> dict[str, BoundedContextMeta]:
    return {m.context_id: m for m in BOUNDED_CONTEXTS}
