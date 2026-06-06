"""
客户 Schema

客户相关的 Pydantic 模型定义。
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CustomerCreate(BaseModel):
    customer_code: str | None = Field(None, description="客户编码")
    name: str = Field(..., min_length=1, max_length=200, description="客户名称")
    contact_person: str | None = Field(None, max_length=100, description="联系人")
    phone: str | None = Field(None, max_length=50, description="电话")
    email: str | None = Field(None, max_length=100, description="邮箱")
    address: str | None = Field(None, max_length=500, description="地址")
    customer_type: str = Field("普通客户", max_length=50, description="客户类型")
    credit_level: str | None = Field(None, max_length=50, description="信用等级")
    payment_terms: str | None = Field(None, max_length=200, description="付款条款")
    description: str | None = Field(None, max_length=1000, description="描述信息")
    is_active: int = Field(1, ge=0, le=1)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("客户名称不能为空")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is not None and v.strip():
            if "@" not in v:
                raise ValueError("邮箱格式不正确")
        return v


class CustomerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    contact_person: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=100)
    address: str | None = Field(None, max_length=500)
    customer_type: str | None = Field(None, max_length=50)
    credit_level: str | None = Field(None, max_length=50)
    payment_terms: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=1000)
    is_active: int | None = Field(None, ge=0, le=1)


class CustomerResponse(BaseModel):
    id: int
    customer_code: str
    name: str
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    customer_type: str
    credit_level: str | None = None
    payment_terms: str | None = None
    description: str | None = None
    is_active: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    success: bool = True
    data: list[CustomerResponse]
    total: int
    page: int
    per_page: int
    count: int
