# -*- coding: utf-8 -*-
"""
Schema 导出模块

所有 Pydantic Schema 模型的统一导出。
"""

from app.schemas.auth_schema import (
    ErrorResponse,
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
    UserInfo,
)
from app.schemas.common_schema import ErrorResponse as CommonErrorResponse
from app.schemas.common_schema import (
    PaginationMeta,
    SuccessResponse,
)
from app.schemas.customer_schema import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
)
from app.schemas.material_schema import (
    MaterialCreate,
    MaterialListResponse,
    MaterialResponse,
    MaterialUpdate,
)
from app.schemas.product_schema import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.schemas.shipment_schema import (
    ShipmentCreate,
    ShipmentDetailResponse,
    ShipmentItemCreate,
    ShipmentItemResponse,
    ShipmentListResponse,
    ShipmentResponse,
    ShipmentUpdate,
)

__all__ = [
    # Material
    "MaterialCreate",
    "MaterialUpdate",
    "MaterialResponse",
    "MaterialListResponse",
    # Product
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductListResponse",
    # Customer
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    "CustomerListResponse",
    # Shipment
    "ShipmentCreate",
    "ShipmentUpdate",
    "ShipmentResponse",
    "ShipmentDetailResponse",
    "ShipmentListResponse",
    "ShipmentItemCreate",
    "ShipmentItemResponse",
    # Auth
    "LoginRequest",
    "LoginResponse",
    "TokenRefreshRequest",
    "TokenRefreshResponse",
    "UserInfo",
    "PasswordChangeRequest",
    "ErrorResponse",
    # Common
    "SuccessResponse",
    "PaginationMeta",
    "CommonErrorResponse",
]
