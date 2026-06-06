"""
订单域（OrderNeuroDomain）

订单领域事件：创建、更新、支付、发货、完成
"""

import logging
from decimal import Decimal

from app.neuro_bus.domains.base import DomainChannel, NeuroDomain, get_domain_registry
from app.neuro_bus.events.base import EventPriority
from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

logger = logging.getLogger(__name__)


class OrderNeuroDomain(NeuroDomain):
    """
    订单神经域

    事件：
    - order.created
    - order.updated
    - order.paid
    - order.shipped
    - order.completed
    - order.cancelled
    - order.refunded
    """

    domain_name = "order"
    default_channel = DomainChannel.RELIABLE

    def __init__(self, bus=None):
        super().__init__(bus)
        self._setup_handlers()

    def _setup_handlers(self):
        """设置默认处理器"""

        @self.on("order.created", priority=1, channel=DomainChannel.RELIABLE)
        async def on_order_created(event):
            order_id = event.payload.get("order_id")
            logger.info(f"Order created: {order_id}")
            bump_domain_handler_metric("order.created")

        @self.on("order.paid", priority=0, channel=DomainChannel.RELIABLE)
        async def on_order_paid(event):
            order_id = event.payload.get("order_id")
            amount = event.payload.get("amount")
            logger.info(f"Order paid: {order_id}, amount={amount}")
            from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

            bump_domain_handler_metric("order.paid")

        @self.on("order.shipped", priority=1, channel=DomainChannel.STANDARD)
        async def on_order_shipped(event):
            order_id = event.payload.get("order_id")
            shipment_id = event.payload.get("shipment_id")
            logger.info(f"Order shipped: {order_id}, shipment={shipment_id}")
            bump_domain_handler_metric("order.shipped")

    async def initialize(self):
        logger.info("OrderNeuroDomain initialized")

    async def shutdown(self):
        logger.info("OrderNeuroDomain shutdown")

    def emit_order_created(
        self,
        order_id: str,
        customer_id: str,
        items: list,
        total_amount: Decimal,
    ) -> bool:
        return self.emit(
            "order.created",
            priority=EventPriority.HIGH,
            payload={
                "order_id": order_id,
                "customer_id": customer_id,
                "items": items,
                "total_amount": str(total_amount),
                "item_count": len(items),
            },
        )

    def emit_order_paid(self, order_id: str, amount: Decimal, payment_method: str) -> bool:
        return self.emit(
            "order.paid",
            priority=EventPriority.HIGH,
            payload={
                "order_id": order_id,
                "amount": str(amount),
                "payment_method": payment_method,
            },
        )


_order_domain: OrderNeuroDomain | None = None


def get_order_domain() -> OrderNeuroDomain:
    global _order_domain
    if _order_domain is None:
        _order_domain = OrderNeuroDomain()
        get_domain_registry().register(_order_domain)
    return _order_domain
