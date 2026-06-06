"""
产品 Schema

产品相关的 Pydantic 模型定义。
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ProductCreate(BaseModel):
    product_code: str | None = Field(None, description="产品编码")
    name: str = Field(..., min_length=1, max_length=200, description="产品名称")
    category: str | None = Field(None, max_length=100, description="分类")
    specification: str | None = Field(None, max_length=500, description="规格型号")
    unit: str = Field("个", max_length=50, description="单位")
    quantity: float = Field(0, ge=0, description="库存数量")
    unit_price: float = Field(0, ge=0, description="单价")
    cost_price: float | None = Field(None, ge=0, description="成本价")
    supplier: str | None = Field(None, max_length=200, description="供应商")
    warehouse_location: str | None = Field(None, max_length=200, description="仓库位置")
    min_stock: float = Field(0, ge=0, description="最低库存")
    max_stock: float = Field(0, ge=0, description="最高库存")
    description: str | None = Field(None, max_length=1000, description="描述信息")
    is_active: int = Field(1, ge=0, le=1, description="是否激活")

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("产品名称不能为空")
        return v.strip()


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    category: str | None = Field(None, max_length=100)
    specification: str | None = Field(None, max_length=500)
    unit: str | None = Field(None, max_length=50)
    quantity: float | None = Field(None, ge=0)
    unit_price: float | None = Field(None, ge=0)
    cost_price: float | None = Field(None, ge=0)
    supplier: str | None = Field(None, max_length=200)
    warehouse_location: str | None = Field(None, max_length=200)
    min_stock: float | None = Field(None, ge=0)
    max_stock: float | None = Field(None, ge=0)
    description: str | None = Field(None, max_length=1000)
    is_active: int | None = Field(None, ge=0, le=1)


class ProductResponse(BaseModel):
    id: int
    product_code: str
    name: str
    category: str | None = None
    specification: str | None = None
    unit: str
    quantity: float
    unit_price: float
    cost_price: float | None = None
    supplier: str | None = None
    warehouse_location: str | None = None
    min_stock: float
    max_stock: float
    description: str | None = None
    is_active: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    success: bool = True
    data: list[ProductResponse]
    total: int
    page: int
    per_page: int
    count: int
