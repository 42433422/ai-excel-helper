"""
Payment 领域事件定义

包含支付生命周期中的所有领域事件。
"""

from dataclasses import dataclass

from app.neuro_bus.events.base import EventPriority, NeuroEvent


@dataclass
class PaymentCreatedEvent(NeuroEvent):
    """支付创建事件"""

    event_type: str = "payment.created"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["payment_id", "order_id", "amount", "payment_method"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"PaymentCreatedEvent 缺少必要字段: {field}")


@dataclass
class PaymentCompletedEvent(NeuroEvent):
    """支付完成事件"""

    event_type: str = "payment.completed"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["payment_id", "transaction_id", "paid_amount"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"PaymentCompletedEvent 缺少必要字段: {field}")


@dataclass
class PaymentFailedEvent(NeuroEvent):
    """支付失败事件"""

    event_type: str = "payment.failed"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["payment_id", "error_code", "error_message"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"PaymentFailedEvent 缺少必要字段: {field}")


@dataclass
class PaymentRefundedEvent(NeuroEvent):
    """支付退款事件"""

    event_type: str = "payment.refunded"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["payment_id", "refund_id", "refund_amount", "reason"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"PaymentRefundedEvent 缺少必要字段: {field}")


@dataclass
class PaymentMethodChangedEvent(NeuroEvent):
    """支付方式变更事件"""

    event_type: str = "payment.method_changed"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["payment_id", "old_method", "new_method"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"PaymentMethodChangedEvent 缺少必要字段: {field}")


@dataclass
class PaymentNotificationSentEvent(NeuroEvent):
    """支付通知发送事件"""

    event_type: str = "payment.notification_sent"
    priority: EventPriority = EventPriority.LOW

    def __post_init__(self):
        super().__post_init__()
        required = ["payment_id", "notification_type", "recipient"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"PaymentNotificationSentEvent 缺少必要字段: {field}")
