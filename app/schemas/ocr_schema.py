"""OCR API response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common_schema import ErrorResponse


class OcrRecognizeResponse(BaseModel):
    success: bool = True
    message: str = ""
    text: str = ""
    data: dict[str, Any] | None = None


class OcrExtractResponse(BaseModel):
    success: bool = True
    message: str = "提取成功"
    data: dict[str, Any] | None = None


class OcrAnalyzeResponse(BaseModel):
    success: bool = True
    message: str = "分析成功"
    data: dict[str, Any] | None = None


class OcrRecognizeAndExtractResponse(BaseModel):
    success: bool = True
    message: str = "识别和提取成功"
    text: str = ""
    data: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None


class OcrTestResponse(BaseModel):
    success: bool = True
    message: str = "OCR服务运行正常"
    active_backend: str = Field(default="unknown")


class OcrErrorResponse(ErrorResponse):
    pass
