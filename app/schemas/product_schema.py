# -*- coding: utf-8 -*-
"""
产品 Schema

产品相关的 Pydantic 模型定义。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ProductCreate(BaseModel):
    product_code: Optional[str] = Field(None, description="产品编码")
    name: str = Field(..., min_length=1, max_length=200, description="产品名称")
    category: Optional[str] = Field(None, max_length=100, description="分类")
    specification: Optional[str] = Field(None, max_length=500, description="规格型号")
    unit: str = Field("个", max_length=50, description="单位")
    quantity: float = Field(0, ge=0, description="库存数量")
    unit_price: float = Field(0, ge=0, description="单价")
    cost_price: Optional[float] = Field(None, ge=0, description="成本价")
    supplier: Optional[str] = Field(None, max_length=200, description="供应商")
    warehouse_location: Optional[str] = Field(None, max_length=200, description="仓库位置")
    min_stock: float = Field(0, ge=0, description="最低库存")
    max_stock: float = Field(0, ge=0, description="最高库存")
    description: Optional[str] = Field(None, max_length=1000, description="描述信息")
    is_active: int = Field(1, ge=0, le=1, description="是否激活")

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('产品名称不能为空')
        return v.strip()


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    specification: Optional[str] = Field(None, max_length=500)
    unit: Optional[str] = Field(None, max_length=50)
    quantity: Optional[float] = Field(None, ge=0)
    unit_price: Optional[float] = Field(None, ge=0)
    cost_price: Optional[float] = Field(None, ge=0)
    supplier: Optional[str] = Field(None, max_length=200)
    warehouse_location: Optional[str] = Field(None, max_length=200)
    min_stock: Optional[float] = Field(None, ge=0)
    max_stock: Optional[float] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[int] = Field(None, ge=0, le=1)


class ProductResponse(BaseModel):
    id: int
    product_code: str
    name: str
    category: Optional[str] = None
    specification: Optional[str] = None
    unit: str
    quantity: float
    unit_price: float
    cost_price: Optional[float] = None
    supplier: Optional[str] = None
    warehouse_location: Optional[str] = None
    min_stock: float
    max_stock: float
    description: Optional[str] = None
    is_active: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    success: bool = True
    data: List[ProductResponse]
    total: int
    page: int
    per_page: int
    count: int
