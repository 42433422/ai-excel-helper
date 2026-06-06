"""
Order 领域事件定义

包含订单生命周期中的所有领域事件。
"""

from dataclasses import dataclass

from app.neuro_bus.events.base import EventPriority, NeuroEvent


@dataclass
class OrderSubmittedEvent(NeuroEvent):
    """订单提交事件"""

    event_type: str = "order.submitted"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["order_id", "customer_id", "items"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"OrderSubmittedEvent 缺少必要字段: {field}")


@dataclass
class OrderPaidEvent(NeuroEvent):
    """订单支付事件"""

    event_type: str = "order.paid"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["order_id", "payment_id", "amount"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"OrderPaidEvent 缺少必要字段: {field}")


@dataclass
class OrderPaymentFailedEvent(NeuroEvent):
    """订单支付失败事件"""

    event_type: str = "order.payment_failed"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        if "order_id" not in self.payload:
            raise ValueError("OrderPaymentFailedEvent 缺少必要字段: order_id")


@dataclass
class OrderFulfilledEvent(NeuroEvent):
    """订单履行完成事件"""

    event_type: str = "order.fulfilled"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        if "order_id" not in self.payload:
            raise ValueError("OrderFulfilledEvent 缺少必要字段: order_id")


@dataclass
class OrderShippedEvent(NeuroEvent):
    """订单发货事件"""

    event_type: str = "order.shipped"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["order_id", "shipment_id", "tracking_number"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"OrderShippedEvent 缺少必要字段: {field}")


@dataclass
class OrderCancelledEvent(NeuroEvent):
    """订单取消事件"""

    event_type: str = "order.cancelled"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        if "order_id" not in self.payload:
            raise ValueError("OrderCancelledEvent 缺少必要字段: order_id")


@dataclass
class OrderRefundedEvent(NeuroEvent):
    """订单退款事件"""

    event_type: str = "order.refunded"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["order_id", "refund_id", "refund_amount"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"OrderRefundedEvent 缺少必要字段: {field}")


@dataclass
class OrderItemUpdatedEvent(NeuroEvent):
    """订单项更新事件"""

    event_type: str = "order.item_updated"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["order_id", "item_id", "changes"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"OrderItemUpdatedEvent 缺少必要字段: {field}")


@dataclass
class OrderStatusChangedEvent(NeuroEvent):
    """订单状态变更事件"""

    event_type: str = "order.status_changed"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["order_id", "old_status", "new_status"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"OrderStatusChangedEvent 缺少必要字段: {field}")
