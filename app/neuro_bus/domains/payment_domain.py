"""
支付域（PaymentNeuroDomain）

支付领域事件：创建、处理、完成、退款
"""

import logging
from decimal import Decimal
from typing import Any

from app.neuro_bus.domains.base import DomainChannel, NeuroDomain, get_domain_registry
from app.neuro_bus.events.base import EventPriority
from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

logger = logging.getLogger(__name__)


class PaymentNeuroDomain(NeuroDomain):
    """
    支付神经域

    事件：
    - payment.created
    - payment.processing
    - payment.completed
    - payment.failed
    - payment.refunded
    - payment.disputed
    """

    domain_name = "payment"
    default_channel = DomainChannel.CRITICAL

    def __init__(self, bus=None):
        super().__init__(bus)
        self._total_amount = Decimal("0")
        self._transaction_count = 0
        self._failed_count = 0
        self._setup_handlers()

    def _setup_handlers(self):
        @self.on("payment.completed", priority=0, channel=DomainChannel.CRITICAL)
        async def on_completed(event):
            self._transaction_count += 1
            amount = Decimal(event.payload.get("amount", "0"))
            self._total_amount += amount
            logger.info(f"Payment completed: amount={amount}")
            bump_domain_handler_metric("payment.completed")

        @self.on("payment.failed", priority=0, channel=DomainChannel.CRITICAL)
        async def on_failed(event):
            self._failed_count += 1
            error = event.payload.get("error")
            logger.error(f"Payment failed: {error}")
            bump_domain_handler_metric("payment.failed")

    async def initialize(self):
        logger.info("PaymentNeuroDomain initialized")

    async def shutdown(self):
        logger.info("PaymentNeuroDomain shutdown")

    def emit_payment_created(
        self,
        payment_id: str,
        order_id: str,
        amount: Decimal,
        currency: str,
        method: str,
        customer_id: str,
    ) -> bool:
        return self.emit(
            "payment.created",
            priority=EventPriority.HIGH,
            payload={
                "payment_id": payment_id,
                "order_id": order_id,
                "amount": str(amount),
                "currency": currency,
                "method": method,
                "customer_id": customer_id,
            },
        )

    def emit_payment_completed(
        self,
        payment_id: str,
        transaction_id: str,
        amount: Decimal,
        processed_at: str,
    ) -> bool:
        return self.emit(
            "payment.completed",
            priority=EventPriority.HIGH,
            payload={
                "payment_id": payment_id,
                "transaction_id": transaction_id,
                "amount": str(amount),
                "processed_at": processed_at,
            },
        )

    def emit_payment_failed(
        self,
        payment_id: str,
        error: str,
        error_code: str,
        retryable: bool = False,
    ) -> bool:
        return self.emit(
            "payment.failed",
            priority=EventPriority.HIGH,
            payload={
                "payment_id": payment_id,
                "error": error,
                "error_code": error_code,
                "retryable": retryable,
            },
        )

    def emit_payment_refunded(
        self,
        payment_id: str,
        refund_id: str,
        amount: Decimal,
        reason: str,
    ) -> bool:
        return self.emit(
            "payment.refunded",
            priority=EventPriority.HIGH,
            payload={
                "payment_id": payment_id,
                "refund_id": refund_id,
                "amount": str(amount),
                "reason": reason,
            },
        )

    def get_stats(self) -> dict[str, Any]:
        base = super().get_stats()
        return {
            **base,
            "transactions": self._transaction_count,
            "failed": self._failed_count,
            "total_amount": str(self._total_amount),
            "success_rate": (self._transaction_count - self._failed_count)
            / max(self._transaction_count, 1),
        }


_payment_domain: PaymentNeuroDomain | None = None


def get_payment_domain() -> PaymentNeuroDomain:
    global _payment_domain
    if _payment_domain is None:
        _payment_domain = PaymentNeuroDomain()
        get_domain_registry().register(_payment_domain)
    return _payment_domain
