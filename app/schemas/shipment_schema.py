"""
发货单 Schema

发货单相关的 Pydantic 模型定义。
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ShipmentItemCreate(BaseModel):
    product_id: int = Field(..., description="产品ID")
    product_name: str | None = None
    quantity: float = Field(..., gt=0, description="数量")
    unit_price: float | None = Field(None, ge=0, description="单价")
    discount: float | None = Field(0, ge=0, le=1, description="折扣")


class ShipmentItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str | None = None
    quantity: float
    unit_price: float
    discount: float
    subtotal: float

    class Config:
        from_attributes = True


class ShipmentCreate(BaseModel):
    shipment_number: str | None = Field(None, description="发货单号")
    customer_id: int = Field(..., description="客户ID")
    customer_name: str | None = None
    warehouse_id: int | None = Field(None, description="仓库ID")
    shipment_date: datetime | None = None
    items: list[ShipmentItemCreate] = Field(..., min_length=1, description="发货明细")
    total_amount: float | None = Field(0, ge=0, description="总金额")
    discount_amount: float | None = Field(0, ge=0, description="折扣金额")
    final_amount: float | None = Field(0, ge=0, description="最终金额")
    remarks: str | None = Field(None, max_length=500, description="备注")
    status: str = Field("pending", max_length=50, description="状态")

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, v: list) -> list:
        if not v or len(v) == 0:
            raise ValueError("发货明细不能为空")
        return v


class ShipmentUpdate(BaseModel):
    shipment_date: datetime | None = None
    items: list[ShipmentItemCreate] | None = None
    total_amount: float | None = Field(None, ge=0)
    discount_amount: float | None = Field(None, ge=0)
    final_amount: float | None = Field(None, ge=0)
    remarks: str | None = Field(None, max_length=500)
    status: str | None = Field(None, max_length=50)


class ShipmentResponse(BaseModel):
    id: int
    shipment_number: str
    customer_id: int
    customer_name: str | None = None
    warehouse_id: int | None = None
    shipment_date: datetime | None = None
    total_amount: float
    discount_amount: float
    final_amount: float
    remarks: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShipmentDetailResponse(ShipmentResponse):
    items: list[ShipmentItemResponse] = []


class ShipmentListResponse(BaseModel):
    success: bool = True
    data: list[ShipmentResponse]
    total: int
    page: int
    per_page: int
    count: int
