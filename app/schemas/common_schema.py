from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: str | None = None
    details: list[dict[str, Any]] | None = None


class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "操作成功"
    data: Any | None = None


class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int
