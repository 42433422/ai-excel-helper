# -*- coding: utf-8 -*-
"""
认证 Schema

认证相关的 Pydantic 模型定义。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100, description="用户名")
    password: str = Field(..., min_length=1, max_length=200, description="密码")
    remember_me: bool = Field(False, description="记住我")

    @field_validator('username')
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('用户名不能为空')
        return v.strip()


class LoginResponse(BaseModel):
    success: bool = True
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 3600
    user: Optional["UserInfo"] = None
    message: str = "登录成功"


class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="刷新令牌")


class TokenRefreshResponse(BaseModel):
    success: bool = True
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    message: str = "Token刷新成功"


class UserInfo(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    roles: list[str] = []
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError('密码长度至少6位')
        return v


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None
