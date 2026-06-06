"""
库存域（InventoryNeuroDomain）

库存领域事件：变动、预警、盘点
"""

import logging

from app.neuro_bus.domains.base import DomainChannel, NeuroDomain, get_domain_registry
from app.neuro_bus.events.base import EventPriority
from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

logger = logging.getLogger(__name__)


class InventoryNeuroDomain(NeuroDomain):
    """
    库存神经域

    事件：
    - inventory.changed
    - inventory.low_stock
    - inventory.out_of_stock
    - inventory.restocked
    - inventory.counted
    """

    domain_name = "inventory"
    default_channel = DomainChannel.STANDARD

    def __init__(self, bus=None):
        super().__init__(bus)
        self._setup_handlers()

    def _setup_handlers(self):
        @self.on("inventory.low_stock", priority=2, channel=DomainChannel.CRITICAL)
        async def on_low_stock(event):
            product_id = event.payload.get("product_id")
            current = event.payload.get("current_quantity")
            logger.warning(f"Low stock alert: product={product_id}, qty={current}")
            bump_domain_handler_metric("inventory.low_stock")

        @self.on("inventory.out_of_stock", priority=0, channel=DomainChannel.CRITICAL)
        async def on_out_of_stock(event):
            product_id = event.payload.get("product_id")
            logger.error(f"Out of stock: product={product_id}")
            bump_domain_handler_metric("inventory.out_of_stock")

    async def initialize(self):
        logger.info("InventoryNeuroDomain initialized")

    async def shutdown(self):
        logger.info("InventoryNeuroDomain shutdown")

    def emit_stock_changed(
        self,
        product_id: str,
        warehouse_id: str,
        delta: int,
        reason: str,
        new_quantity: int,
    ) -> bool:
        return self.emit(
            "inventory.changed",
            priority=EventPriority.NORMAL,
            payload={
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "delta": delta,
                "reason": reason,
                "new_quantity": new_quantity,
            },
        )

    def emit_low_stock(
        self,
        product_id: str,
        current_quantity: int,
        threshold: int,
    ) -> bool:
        return self.emit(
            "inventory.low_stock",
            priority=EventPriority.HIGH,
            payload={
                "product_id": product_id,
                "current_quantity": current_quantity,
                "threshold": threshold,
            },
        )


_inventory_domain: InventoryNeuroDomain | None = None


def get_inventory_domain() -> InventoryNeuroDomain:
    global _inventory_domain
    if _inventory_domain is None:
        _inventory_domain = InventoryNeuroDomain()
        get_domain_registry().register(_inventory_domain)
    return _inventory_domain
