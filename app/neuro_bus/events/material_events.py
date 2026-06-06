"""
Material 领域事件定义

包含物料管理的所有领域事件。
"""

from dataclasses import dataclass

from app.neuro_bus.events.base import EventPriority, NeuroEvent


@dataclass
class MaterialCreatedEvent(NeuroEvent):
    """物料创建事件"""

    event_type: str = "material.created"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["material_id", "material_name", "material_code"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"MaterialCreatedEvent 缺少必要字段: {field}")


@dataclass
class MaterialUpdatedEvent(NeuroEvent):
    """物料更新事件"""

    event_type: str = "material.updated"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        if "material_id" not in self.payload:
            raise ValueError("MaterialUpdatedEvent 缺少必要字段: material_id")


@dataclass
class MaterialStockInEvent(NeuroEvent):
    """物料入库事件"""

    event_type: str = "material.stock_in"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["material_id", "warehouse_id", "quantity", "batch_no"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"MaterialStockInEvent 缺少必要字段: {field}")


@dataclass
class MaterialStockOutEvent(NeuroEvent):
    """物料出库事件"""

    event_type: str = "material.stock_out"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["material_id", "warehouse_id", "quantity", "usage_purpose"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"MaterialStockOutEvent 缺少必要字段: {field}")


@dataclass
class MaterialLowStockAlertEvent(NeuroEvent):
    """物料库存预警事件"""

    event_type: str = "material.low_stock_alert"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["material_id", "current_stock", "safety_stock"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"MaterialLowStockAlertEvent 缺少必要字段: {field}")


@dataclass
class MaterialSupplierChangedEvent(NeuroEvent):
    """物料供应商变更事件"""

    event_type: str = "material.supplier_changed"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["material_id", "old_supplier", "new_supplier"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"MaterialSupplierChangedEvent 缺少必要字段: {field}")
