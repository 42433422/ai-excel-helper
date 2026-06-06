"""OCR API（继承自归档 ocr 蓝图的端点契约）。"""

from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import APIRouter, Body, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.ocr_schema import (
    OcrAnalyzeResponse,
    OcrExtractResponse,
    OcrRecognizeAndExtractResponse,
    OcrRecognizeResponse,
    OcrTestResponse,
)
from app.utils.upload_helpers import save_upload_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ocr", tags=["ocr"])

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff", "webp"}


@lru_cache(maxsize=1)
def _get_ocr_service():
    from app.application.facades.ocr_facade import get_ocr_service as _get

    return _get()


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


async def _resolve_ocr_path(
    file_path: str | None,
    image: UploadFile | None,
) -> str | None:
    if image is not None and image.filename:
        return await save_upload_file(image, subdir="ocr")
    return file_path


@router.post("/recognize", response_model=OcrRecognizeResponse)
async def ocr_recognize(
    file_path: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
):
    try:
        resolved_path = await _resolve_ocr_path(file_path, image)
        if not resolved_path:
            return JSONResponse(
                {"success": False, "message": "请提供图像文件或文件路径"}, status_code=400
            )

        service = _get_ocr_service()
        result = service.recognize_file(resolved_path)
        status_code = 200 if result.get("success") else 400
        return JSONResponse(result, status_code=status_code)
    except Exception as e:
        logger.exception("OCR识别失败: %s", e)
        return JSONResponse({"success": False, "message": f"识别失败: {str(e)}"}, status_code=500)


@router.post("/extract", response_model=OcrExtractResponse)
def ocr_extract(data: dict = Body(default_factory=dict)):
    try:
        text = data.get("text", "")
        if not text:
            return JSONResponse({"success": False, "message": "文本不能为空"}, status_code=400)
        service = _get_ocr_service()
        result = service.extract_structured_data(text)
        return OcrExtractResponse(data=result)
    except Exception as e:
        logger.exception("提取结构化数据失败: %s", e)
        return JSONResponse({"success": False, "message": f"提取失败: {str(e)}"}, status_code=500)


@router.post("/analyze", response_model=OcrAnalyzeResponse)
def ocr_analyze(data: dict = Body(default_factory=dict)):
    try:
        text = data.get("text", "")
        if not text:
            return JSONResponse({"success": False, "message": "文本不能为空"}, status_code=400)
        service = _get_ocr_service()
        result = service.analyze_text(text)
        return OcrAnalyzeResponse(data=result)
    except Exception as e:
        logger.exception("分析文本失败: %s", e)
        return JSONResponse({"success": False, "message": f"分析失败: {str(e)}"}, status_code=500)


@router.post("/recognize-and-extract", response_model=OcrRecognizeAndExtractResponse)
async def ocr_recognize_and_extract(
    file_path: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
):
    try:
        resolved_path = await _resolve_ocr_path(file_path, image)
        if not resolved_path:
            return JSONResponse(
                {"success": False, "message": "请提供图像文件或文件路径"}, status_code=400
            )

        service = _get_ocr_service()
        recognize_result = service.recognize_file(resolved_path)
        if not recognize_result.get("success"):
            return JSONResponse(recognize_result, status_code=400)

        text = recognize_result.get("text", "")
        structured_data = service.extract_structured_data(text)
        analysis = service.analyze_text(text)

        return OcrRecognizeAndExtractResponse(
            text=text,
            data=structured_data,
            analysis=analysis,
        )
    except Exception as e:
        logger.exception("OCR识别和提取失败: %s", e)
        return JSONResponse({"success": False, "message": f"处理失败: {str(e)}"}, status_code=500)


@router.get("/test", response_model=OcrTestResponse)
def ocr_test():
    try:
        svc = _get_ocr_service()
        backend = svc.get_active_ocr_backend()
    except Exception:
        backend = "unknown"
    return OcrTestResponse(active_backend=backend)
