"""
客户域（CustomerNeuroDomain）

客户领域事件：注册、登录、资料更新
"""

import logging

from app.neuro_bus.domains.base import DomainChannel, NeuroDomain, get_domain_registry
from app.neuro_bus.events.base import EventPriority
from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

logger = logging.getLogger(__name__)


class CustomerNeuroDomain(NeuroDomain):
    """
    客户神经域

    事件：
    - customer.registered
    - customer.login
    - customer.logout
    - customer.profile_updated
    - customer.level_changed
    """

    domain_name = "customer"
    default_channel = DomainChannel.STANDARD

    def __init__(self, bus=None):
        super().__init__(bus)
        self._setup_handlers()

    def _setup_handlers(self):
        @self.on("customer.registered", priority=1)
        async def on_registered(event):
            customer_id = event.payload.get("customer_id")
            logger.info(f"Customer registered: {customer_id}")
            bump_domain_handler_metric("customer.registered")

        @self.on("customer.login", priority=2)
        async def on_login(event):
            customer_id = event.payload.get("customer_id")
            logger.info(f"Customer login: {customer_id}")
            bump_domain_handler_metric("customer.login")

    async def initialize(self):
        logger.info("CustomerNeuroDomain initialized")

    async def shutdown(self):
        logger.info("CustomerNeuroDomain shutdown")

    def emit_customer_registered(
        self,
        customer_id: str,
        name: str,
        phone: str,
        source: str = "",
    ) -> bool:
        return self.emit(
            "customer.registered",
            priority=EventPriority.NORMAL,
            payload={
                "customer_id": customer_id,
                "name": name,
                "phone": phone,
                "source": source,
            },
        )

    def emit_customer_login(
        self,
        customer_id: str,
        device: str = "",
        ip: str = "",
    ) -> bool:
        return self.emit(
            "customer.login",
            priority=EventPriority.HIGH,
            payload={
                "customer_id": customer_id,
                "device": device,
                "ip": ip,
                "timestamp": __import__("time").time(),
            },
        )


_customer_domain: CustomerNeuroDomain | None = None


def get_customer_domain() -> CustomerNeuroDomain:
    global _customer_domain
    if _customer_domain is None:
        _customer_domain = CustomerNeuroDomain()
        get_domain_registry().register(_customer_domain)
    return _customer_domain
