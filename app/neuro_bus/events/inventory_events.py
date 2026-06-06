"""
Inventory 领域事件定义

包含库存管理中的所有领域事件。
"""

from dataclasses import dataclass

from app.neuro_bus.events.base import EventPriority, NeuroEvent


@dataclass
class InventoryStockChangedEvent(NeuroEvent):
    """库存变动事件"""

    event_type: str = "inventory.stock_changed"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["product_id", "warehouse_id", "quantity_delta", "reason"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"InventoryStockChangedEvent 缺少必要字段: {field}")


@dataclass
class InventoryLowStockAlertEvent(NeuroEvent):
    """库存不足预警事件"""

    event_type: str = "inventory.low_stock_alert"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["product_id", "current_stock", "threshold"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"InventoryLowStockAlertEvent 缺少必要字段: {field}")


@dataclass
class InventoryStockInEvent(NeuroEvent):
    """入库事件"""

    event_type: str = "inventory.stock_in"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["product_id", "warehouse_id", "quantity", "batch_no"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"InventoryStockInEvent 缺少必要字段: {field}")


@dataclass
class InventoryStockOutEvent(NeuroEvent):
    """出库事件"""

    event_type: str = "inventory.stock_out"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["product_id", "warehouse_id", "quantity", "reference_id"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"InventoryStockOutEvent 缺少必要字段: {field}")


@dataclass
class InventoryTransferEvent(NeuroEvent):
    """库存调拨事件"""

    event_type: str = "inventory.transfer"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["product_id", "from_warehouse", "to_warehouse", "quantity"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"InventoryTransferEvent 缺少必要字段: {field}")


@dataclass
class InventoryCheckCompletedEvent(NeuroEvent):
    """库存盘点完成事件"""

    event_type: str = "inventory.check_completed"
    priority: EventPriority = EventPriority.LOW

    def __post_init__(self):
        super().__post_init__()
        required = ["warehouse_id", "check_date", "differences"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"InventoryCheckCompletedEvent 缺少必要字段: {field}")
