# -*- coding: utf-8 -*-
import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class MaterialCreate(BaseModel):
    material_code: Optional[str] = Field(None, description="原材料编码，不传则自动生成")
    name: str = Field(..., min_length=1, max_length=200, description="原材料名称")
    category: Optional[str] = Field(None, max_length=100, description="分类")
    specification: Optional[str] = Field(None, max_length=500, description="规格型号")
    unit: str = Field("个", max_length=50, description="单位")
    quantity: float = Field(0, ge=0, description="数量")
    unit_price: float = Field(0, ge=0, description="单价")
    supplier: Optional[str] = Field(None, max_length=200, description="供应商")
    warehouse_location: Optional[str] = Field(None, max_length=200, description="仓库位置")
    min_stock: float = Field(0, ge=0, description="最低库存")
    max_stock: float = Field(0, ge=0, description="最高库存")
    description: Optional[str] = Field(None, max_length=1000, description="描述信息")

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('原材料名称不能为空')
        return v.strip()

    @field_validator('material_code')
    @classmethod
    def validate_material_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            if not re.match(r'^[A-Za-z0-9\-_]+$', v):
                raise ValueError('原材料编码只能包含字母、数字、连字符和下划线')
        return v


class MaterialUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    specification: Optional[str] = Field(None, max_length=500)
    unit: Optional[str] = Field(None, max_length=50)
    quantity: Optional[float] = Field(None, ge=0)
    unit_price: Optional[float] = Field(None, ge=0)
    supplier: Optional[str] = Field(None, max_length=200)
    warehouse_location: Optional[str] = Field(None, max_length=200)
    min_stock: Optional[float] = Field(None, ge=0)
    max_stock: Optional[float] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=1000)

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError('原材料名称不能为空')
            return v.strip()
        return v


class MaterialResponse(BaseModel):
    id: int
    material_code: str
    name: str
    category: Optional[str] = None
    specification: Optional[str] = None
    unit: str
    quantity: float
    unit_price: float
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


class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int


class MaterialListResponse(BaseModel):
    success: bool = True
    data: List[MaterialResponse]
    total: int
    page: int
    per_page: int
    count: int
