"""
微信域（WechatNeuroDomain）

微信集成事件：消息、菜单点击、支付回调
"""

import logging

from app.neuro_bus.domains.base import DomainChannel, NeuroDomain, get_domain_registry
from app.neuro_bus.events.base import EventPriority
from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

logger = logging.getLogger(__name__)


class WechatNeuroDomain(NeuroDomain):
    """
    微信神经域

    事件：
    - wechat.message.received
    - wechat.menu.click
    - wechat.payment.callback
    - wechat.user.subscribe
    - wechat.user.unsubscribe
    """

    domain_name = "wechat"
    default_channel = DomainChannel.STANDARD

    def __init__(self, bus=None):
        super().__init__(bus)
        self._setup_handlers()

    def _setup_handlers(self):
        @self.on("wechat.message.received", priority=1)
        async def on_message(event):
            msg_type = event.payload.get("msg_type")
            from_user = event.payload.get("from_user")
            logger.info(f"WeChat message: type={msg_type}, from={from_user}")
            from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

            bump_domain_handler_metric("wechat.message.received")

        @self.on("wechat.payment.callback", priority=0, channel=DomainChannel.RELIABLE)
        async def on_payment(event):
            order_id = event.payload.get("order_id")
            status = event.payload.get("status")
            logger.info(f"WeChat payment: order={order_id}, status={status}")
            bump_domain_handler_metric("wechat.payment.callback")

    async def initialize(self):
        logger.info("WechatNeuroDomain initialized")

    async def shutdown(self):
        logger.info("WechatNeuroDomain shutdown")

    def emit_message_received(
        self,
        msg_id: str,
        msg_type: str,
        from_user: str,
        content: str,
        timestamp: int,
    ) -> bool:
        return self.emit(
            "wechat.message.received",
            priority=EventPriority.HIGH,
            payload={
                "msg_id": msg_id,
                "msg_type": msg_type,
                "from_user": from_user,
                "content": content,
                "timestamp": timestamp,
            },
        )

    def emit_payment_callback(
        self,
        order_id: str,
        transaction_id: str,
        status: str,
        amount: float,
    ) -> bool:
        return self.emit(
            "wechat.payment.callback",
            priority=EventPriority.HIGH,
            payload={
                "order_id": order_id,
                "transaction_id": transaction_id,
                "status": status,
                "amount": amount,
            },
        )


_wechat_domain: WechatNeuroDomain | None = None


def get_wechat_domain() -> WechatNeuroDomain:
    global _wechat_domain
    if _wechat_domain is None:
        _wechat_domain = WechatNeuroDomain()
        get_domain_registry().register(_wechat_domain)
    return _wechat_domain
