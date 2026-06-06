"""
产品域（ProductNeuroDomain）

产品领域事件：创建、更新、价格变动、删除
"""

import logging
from decimal import Decimal

from app.neuro_bus.domains.base import DomainChannel, NeuroDomain, get_domain_registry
from app.neuro_bus.events.base import EventPriority
from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

logger = logging.getLogger(__name__)


class ProductNeuroDomain(NeuroDomain):
    """
    产品神经域

    事件：
    - product.created
    - product.updated
    - product.price_changed
    - product.deleted
    - product.archived
    """

    domain_name = "product"
    default_channel = DomainChannel.STANDARD

    def __init__(self, bus=None):
        super().__init__(bus)
        self._setup_handlers()

    def _setup_handlers(self):
        @self.on("product.price_changed", priority=2)
        async def on_price_changed(event):
            product_id = event.payload.get("product_id")
            old_price = event.payload.get("old_price")
            new_price = event.payload.get("new_price")
            logger.info(f"Price changed: {product_id} {old_price} -> {new_price}")
            bump_domain_handler_metric("product.price_changed")

    async def initialize(self):
        logger.info("ProductNeuroDomain initialized")

    async def shutdown(self):
        logger.info("ProductNeuroDomain shutdown")

    def emit_product_created(
        self,
        product_id: str,
        name: str,
        category: str,
        initial_price: Decimal,
    ) -> bool:
        return self.emit(
            "product.created",
            priority=EventPriority.NORMAL,
            payload={
                "product_id": product_id,
                "name": name,
                "category": category,
                "initial_price": str(initial_price),
            },
        )

    def emit_price_changed(
        self,
        product_id: str,
        old_price: Decimal,
        new_price: Decimal,
        reason: str = "",
    ) -> bool:
        return self.emit(
            "product.price_changed",
            priority=EventPriority.NORMAL,
            payload={
                "product_id": product_id,
                "old_price": str(old_price),
                "new_price": str(new_price),
                "reason": reason,
            },
        )


_product_domain: ProductNeuroDomain | None = None


def get_product_domain() -> ProductNeuroDomain:
    global _product_domain
    if _product_domain is None:
        _product_domain = ProductNeuroDomain()
        get_domain_registry().register(_product_domain)
    return _product_domain
