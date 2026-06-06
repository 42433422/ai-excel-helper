"""Structured error codes for the FHD platform.

Replaces bare `except Exception` with domain-specific error types,
enabling precise frontend UI responses and alerting.
"""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_PERMISSION_DENIED = "AUTH_PERMISSION_DENIED"
    PAYMENT_ORDER_NOT_FOUND = "PAYMENT_ORDER_NOT_FOUND"
    PAYMENT_AMOUNT_MISMATCH = "PAYMENT_AMOUNT_MISMATCH"
    PAYMENT_WALLET_INSUFFICIENT_BALANCE = "PAYMENT_WALLET_INSUFFICIENT_BALANCE"
    PAYMENT_WALLET_RECHARGE_BLOCKED = "PAYMENT_WALLET_RECHARGE_BLOCKED"
    PAYMENT_ORDER_ALREADY_REFUNDED = "PAYMENT_ORDER_ALREADY_REFUNDED"
    DB_CONNECTION_FAILED = "DB_CONNECTION_FAILED"
    DB_QUERY_FAILED = "DB_QUERY_FAILED"
    DB_TABLE_NOT_FOUND = "DB_TABLE_NOT_FOUND"
    LLM_SERVICE_UNAVAILABLE = "LLM_SERVICE_UNAVAILABLE"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_READ_ERROR = "FILE_READ_ERROR"
    FILE_WRITE_ERROR = "FILE_WRITE_ERROR"
    MOD_NOT_FOUND = "MOD_NOT_FOUND"
    MOD_INSTALL_FAILED = "MOD_INSTALL_FAILED"
    CACHE_UNAVAILABLE = "CACHE_UNAVAILABLE"
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """Structured application error with error code and HTTP status."""

    def __init__(
        self,
        code: ErrorCode,
        message: str = "",
        status_code: int = 500,
        detail: dict | None = None,
    ):
        self.code = code
        self.message = message or code.value
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)

    def to_dict(self, *, request_id: str = "") -> dict:
        return {
            "ok": False,
            "error_code": self.code.value,
            "message": self.message,
            "request_id": request_id,
            **self.detail,
        }


class AuthError(AppError):
    def __init__(
        self,
        code: ErrorCode = ErrorCode.AUTH_TOKEN_INVALID,
        message: str = "",
        detail: dict | None = None,
    ):
        super().__init__(code, message, status_code=401, detail=detail)


class PermissionError(AppError):
    def __init__(
        self,
        code: ErrorCode = ErrorCode.AUTH_PERMISSION_DENIED,
        message: str = "",
        detail: dict | None = None,
    ):
        super().__init__(code, message, status_code=403, detail=detail)


class PaymentError(AppError):
    def __init__(
        self, code: ErrorCode, message: str = "", status_code: int = 400, detail: dict | None = None
    ):
        super().__init__(code, message, status_code=status_code, detail=detail)


class DatabaseError(AppError):
    def __init__(
        self,
        code: ErrorCode = ErrorCode.DB_QUERY_FAILED,
        message: str = "",
        detail: dict | None = None,
    ):
        super().__init__(code, message, status_code=503, detail=detail)


class LLMError(AppError):
    def __init__(
        self,
        code: ErrorCode = ErrorCode.LLM_SERVICE_UNAVAILABLE,
        message: str = "",
        detail: dict | None = None,
    ):
        super().__init__(code, message, status_code=503, detail=detail)
