# -*- coding: utf-8 -*-
"""
客户 Schema

客户相关的 Pydantic 模型定义。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class CustomerCreate(BaseModel):
    customer_code: Optional[str] = Field(None, description="客户编码")
    name: str = Field(..., min_length=1, max_length=200, description="客户名称")
    contact_person: Optional[str] = Field(None, max_length=100, description="联系人")
    phone: Optional[str] = Field(None, max_length=50, description="电话")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    address: Optional[str] = Field(None, max_length=500, description="地址")
    customer_type: str = Field("普通客户", max_length=50, description="客户类型")
    credit_level: Optional[str] = Field(None, max_length=50, description="信用等级")
    payment_terms: Optional[str] = Field(None, max_length=200, description="付款条款")
    description: Optional[str] = Field(None, max_length=1000, description="描述信息")
    is_active: int = Field(1, ge=0, le=1)

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('客户名称不能为空')
        return v.strip()

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            if '@' not in v:
                raise ValueError('邮箱格式不正确')
        return v


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    customer_type: Optional[str] = Field(None, max_length=50)
    credit_level: Optional[str] = Field(None, max_length=50)
    payment_terms: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[int] = Field(None, ge=0, le=1)


class CustomerResponse(BaseModel):
    id: int
    customer_code: str
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    customer_type: str
    credit_level: Optional[str] = None
    payment_terms: Optional[str] = None
    description: Optional[str] = None
    is_active: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    success: bool = True
    data: List[CustomerResponse]
    total: int
    page: int
    per_page: int
    count: int
