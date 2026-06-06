"""
Shipment 领域事件定义

包含发货单生命周期中的所有领域事件。
"""

from dataclasses import dataclass

from app.neuro_bus.events.base import EventPriority, NeuroEvent


@dataclass
class ShipmentCreatedEvent(NeuroEvent):
    """发货单创建事件"""

    event_type: str = "shipment.created"
    priority: EventPriority = EventPriority.HIGH  # 创建是高频核心操作

    def __post_init__(self):
        super().__post_init__()
        required = ["shipment_id", "unit_name"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"ShipmentCreatedEvent 缺少必要字段: {field}")


@dataclass
class ShipmentItemAddedEvent(NeuroEvent):
    """发货单添加产品事件"""

    event_type: str = "shipment.item_added"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["shipment_id", "product_id", "quantity"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"ShipmentItemAddedEvent 缺少必要字段: {field}")


@dataclass
class ShipmentPrintedEvent(NeuroEvent):
    """发货单打印事件"""

    event_type: str = "shipment.printed"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        if "shipment_id" not in self.payload:
            raise ValueError("ShipmentPrintedEvent 缺少必要字段: shipment_id")


@dataclass
class ShipmentCancelledEvent(NeuroEvent):
    """发货单取消事件"""

    event_type: str = "shipment.cancelled"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        if "shipment_id" not in self.payload:
            raise ValueError("ShipmentCancelledEvent 缺少必要字段: shipment_id")


@dataclass
class ShipmentDeletedEvent(NeuroEvent):
    """发货单删除事件"""

    event_type: str = "shipment.deleted"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        if "shipment_id" not in self.payload:
            raise ValueError("ShipmentDeletedEvent 缺少必要字段: shipment_id")


@dataclass
class ShipmentExportedEvent(NeuroEvent):
    """发货单导出事件"""

    event_type: str = "shipment.exported"
    priority: EventPriority = EventPriority.LOW  # 导出是后台操作

    def __post_init__(self):
        super().__post_init__()
        if "file_path" not in self.payload:
            raise ValueError("ShipmentExportedEvent 缺少必要字段: file_path")


# 发货单相关库存事件
@dataclass
class ShipmentInventoryDeductedEvent(NeuroEvent):
    """发货单库存扣减事件"""

    event_type: str = "shipment.inventory_deducted"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["shipment_id", "items"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"ShipmentInventoryDeductedEvent 缺少必要字段: {field}")
