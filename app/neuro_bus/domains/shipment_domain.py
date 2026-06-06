"""出货域（ShipmentNeuroDomain）：与 ``shipment_domain_handlers`` 事件名对齐的域级订阅与指标。"""

from __future__ import annotations

import logging

from app.neuro_bus.domains.base import DomainChannel, NeuroDomain, get_domain_registry
from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

logger = logging.getLogger(__name__)


class ShipmentNeuroDomain(NeuroDomain):
    domain_name = "shipment"
    default_channel = DomainChannel.STANDARD

    def __init__(self, bus=None):
        super().__init__(bus)
        self._setup_handlers()

    def register(self):
        """出货事件多由兼容层以扁平 ``subscribe`` 注册；此处也用扁平订阅以免 ``metadata.domain`` 未设置时收不到事件。"""
        if self._registered:
            logger.warning("Domain [%s] already registered", self.domain_name)
            return
        for handler_def in self._handlers:
            self._bus.subscribe(
                handler_def.event_type,
                handler_def.handler,
                priority=handler_def.priority,
            )
        self._registered = True
        logger.info(
            "Domain [%s] registered (flat) with %d handlers", self.domain_name, len(self._handlers)
        )

    def _setup_handlers(self):
        @self.on("shipment.created", priority=2, channel=DomainChannel.STANDARD)
        async def on_shipment_created(event):
            logger.debug(
                "[ShipmentNeuroDomain] shipment.created %s", event.payload.get("shipment_id")
            )
            bump_domain_handler_metric("shipment.created")

        @self.on("shipment.item_added", priority=2, channel=DomainChannel.STANDARD)
        async def on_item_added(event):
            bump_domain_handler_metric("shipment.item_added")

        @self.on("shipment.printed", priority=3, channel=DomainChannel.STANDARD)
        async def on_printed(event):
            bump_domain_handler_metric("shipment.printed")

        @self.on("shipment.cancelled", priority=3, channel=DomainChannel.STANDARD)
        async def on_cancelled(event):
            bump_domain_handler_metric("shipment.cancelled")

        @self.on("shipment.deleted", priority=3, channel=DomainChannel.STANDARD)
        async def on_deleted(event):
            bump_domain_handler_metric("shipment.deleted")

        @self.on("shipment.exported", priority=3, channel=DomainChannel.STANDARD)
        async def on_exported(event):
            bump_domain_handler_metric("shipment.exported")

        @self.on("shipment.inventory_deducted", priority=2, channel=DomainChannel.STANDARD)
        async def on_inv_deducted(event):
            bump_domain_handler_metric("shipment.inventory_deducted")

    async def initialize(self):
        logger.debug("ShipmentNeuroDomain initialized")

    async def shutdown(self):
        logger.debug("ShipmentNeuroDomain shutdown")


_shipment_domain: ShipmentNeuroDomain | None = None


def get_shipment_domain() -> ShipmentNeuroDomain:
    global _shipment_domain
    if _shipment_domain is None:
        _shipment_domain = ShipmentNeuroDomain()
        get_domain_registry().register(_shipment_domain)
    return _shipment_domain
