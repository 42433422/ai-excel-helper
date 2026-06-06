"""
Customer 领域事件定义

包含客户生命周期中的所有领域事件。
"""

from dataclasses import dataclass

from app.neuro_bus.events.base import EventPriority, NeuroEvent


@dataclass
class CustomerRegisteredEvent(NeuroEvent):
    """客户注册事件"""

    event_type: str = "customer.registered"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["customer_id", "contact_info"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"CustomerRegisteredEvent 缺少必要字段: {field}")


@dataclass
class CustomerUpdatedEvent(NeuroEvent):
    """客户信息更新事件"""

    event_type: str = "customer.updated"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        if "customer_id" not in self.payload:
            raise ValueError("CustomerUpdatedEvent 缺少必要字段: customer_id")


@dataclass
class CustomerDeactivatedEvent(NeuroEvent):
    """客户停用事件"""

    event_type: str = "customer.deactivated"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        if "customer_id" not in self.payload:
            raise ValueError("CustomerDeactivatedEvent 缺少必要字段: customer_id")


@dataclass
class CustomerPurchaseUnitBoundEvent(NeuroEvent):
    """客户绑定购买单位事件"""

    event_type: str = "customer.purchase_unit_bound"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["customer_id", "purchase_unit"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"CustomerPurchaseUnitBoundEvent 缺少必要字段: {field}")


@dataclass
class CustomerPreferenceUpdatedEvent(NeuroEvent):
    """客户偏好更新事件"""

    event_type: str = "customer.preference_updated"
    priority: EventPriority = EventPriority.LOW

    def __post_init__(self):
        super().__post_init__()
        if "customer_id" not in self.payload:
            raise ValueError("CustomerPreferenceUpdatedEvent 缺少必要字段: customer_id")


@dataclass
class CustomerCreditLimitChangedEvent(NeuroEvent):
    """客户信用额度变更事件"""

    event_type: str = "customer.credit_limit_changed"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["customer_id", "old_limit", "new_limit"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"CustomerCreditLimitChangedEvent 缺少必要字段: {field}")
