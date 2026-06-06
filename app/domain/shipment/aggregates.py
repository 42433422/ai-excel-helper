"""
出货单 (Shipment) 聚合根 — 领域边界说明
=========================================

## Order（订单）vs Shipment（出货单）— 概念边界

本业务中两个概念经常混用，明确定义如下：

**Shipment（出货单 / 发货单）**  ← 本模块管理
- 代表「一次向客户（购买单位）的实际发货动作」
- 由 AI 助手或操作员录入，核心字段：purchase_unit、product_name、quantity、amount
- 生命周期：pending → printed → completed/cancelled
- 实体表：shipment_records；聚合根：Shipment（本文件）
- 对应 API：/api/shipment/*、/api/orders/*（前端历史命名）

**Order（采购订单 / 购买订单）**  ← app/domain/... 待建
- 代表「向供应商下达的采购意向」
- 由采购管理模块录入，核心字段：supplier、total_amount、status
- 生命周期：draft → approved → inbound → completed
- 实体表：purchase_orders；应用服务：purchase_app_service_v2
- 对应 API：/api/purchase/orders/*

## 历史混淆来源
前端路由 /api/orders/* 在 shipment_orders.py 中注册，实际操作的是 ShipmentRecord，
而非 purchase_orders 表。这是历史遗留命名，后续迁移计划：
- Phase 5：将前端"订单"页面明确拆分为「出货单」和「采购单」两个独立页面

## 当前规则
- 代码中 "order_number" 字段指出货单编号（YY-MM-NNNNN 格式），非采购订单号
- 采购订单号字段为 PurchaseOrder.order_no
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.shipment.legacy_vo import ContactInfo, Money, OrderNumber, Quantity


@dataclass
class ShipmentItem:
    """发货单项实体（出货明细行）"""

    id: int | None = None
    product_name: str = ""
    model_number: str = ""
    quantity: Quantity = field(default_factory=lambda: Quantity(0, 0))
    unit_price: Money = field(default_factory=lambda: Money(0))
    amount: Money = field(default_factory=lambda: Money(0))
    raw_data: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.product_name:
            raise ValueError("产品名称不能为空")

    def calculate_amount(self) -> Money:
        self.amount = self.unit_price * (self.quantity.kg / 10.0) if self.quantity.kg else Money(0)
        return self.amount

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_name": self.product_name,
            "model_number": self.model_number,
            "quantity_tins": self.quantity.tins,
            "quantity_kg": self.quantity.kg,
            "spec_per_tin": self.quantity.spec_per_tin,
            "unit_price": self.unit_price.amount,
            "amount": self.amount.amount,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShipmentItem":
        quantity = Quantity.from_tins_and_spec(
            tins=data.get("quantity_tins", 0),
            spec_per_tin=data.get("tin_spec", data.get("spec_per_tin", 10.0)),
        )
        unit_price = Money(data.get("unit_price", 0))
        amount = Money(data.get("amount", 0))

        return cls(
            id=data.get("id"),
            product_name=data.get("product_name", data.get("name", "")),
            model_number=data.get("model_number", ""),
            quantity=quantity,
            unit_price=unit_price,
            amount=amount,
            raw_data=data,
        )


@dataclass
class Shipment:
    """发货单聚合根（对应 shipment_records 表）。

    注意命名：前端 /api/orders/* 路由对应此聚合，非采购订单（PurchaseOrder）。
    见本文件头部边界说明。
    """

    id: int | None = None
    order_number: OrderNumber = field(default_factory=OrderNumber.generate)
    purchase_unit_name: str = ""
    contact_info: ContactInfo = field(default_factory=lambda: ContactInfo("", ""))
    items: list[ShipmentItem] = field(default_factory=list)
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    printed_at: datetime | None = None
    printer_name: str | None = None
    raw_text: str | None = None
    total_amount: Money = field(default_factory=lambda: Money(0))
    total_quantity: Quantity = field(default_factory=lambda: Quantity(0, 0))

    def __post_init__(self):
        if not self.purchase_unit_name:
            raise ValueError("购买单位不能为空")

    def add_item(self, item: ShipmentItem) -> None:
        self.items.append(item)
        self._recalculate_totals()
        self.updated_at = datetime.now()

    def remove_item(self, index: int) -> ShipmentItem:
        if 0 <= index < len(self.items):
            removed = self.items.pop(index)
            self._recalculate_totals()
            self.updated_at = datetime.now()
            return removed
        raise IndexError("索引超出范围")

    def _recalculate_totals(self) -> None:
        total = Money(0)
        total_tins = 0
        total_kg = 0.0

        for item in self.items:
            total = total + item.amount
            total_tins += item.quantity.tins
            total_kg += item.quantity.kg

        self.total_amount = total
        self.total_quantity = Quantity(total_tins, total_kg)

    def mark_as_printed(self, printer_name: str = "") -> None:
        self.status = "printed"
        self.printed_at = datetime.now()
        self.printer_name = printer_name
        self.updated_at = datetime.now()

    def cancel(self) -> None:
        self.status = "cancelled"
        self.updated_at = datetime.now()

    def is_valid(self) -> bool:
        return bool(self.purchase_unit_name) and len(self.items) > 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_number": str(self.order_number),
            "purchase_unit": self.purchase_unit_name,
            "contact_person": self.contact_info.person,
            "contact_phone": self.contact_info.phone,
            "contact_address": self.contact_info.address,
            "items": [item.to_dict() for item in self.items],
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "printed_at": self.printed_at.isoformat() if self.printed_at else None,
            "printer_name": self.printer_name,
            "total_amount": self.total_amount.amount,
            "total_quantity_tins": self.total_quantity.tins,
            "total_quantity_kg": self.total_quantity.kg,
        }

    @classmethod
    def create(cls, unit_name: str, contact_info: ContactInfo = None) -> "Shipment":
        return cls(
            order_number=OrderNumber.generate(),
            purchase_unit_name=unit_name,
            contact_info=contact_info or ContactInfo("", ""),
        )
