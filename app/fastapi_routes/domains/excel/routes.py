"""Migrated from legacy_excel.py (v10)."""

from __future__ import annotations

import logging
import os
import uuid

from fastapi import APIRouter, Body, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.utils.path_utils import get_upload_dir

logger = logging.getLogger(__name__)

router = APIRouter(tags=["legacy-excel"], deprecated=True)


@router.post("/api/ai/parse-single")
def ai_parse_single(body: dict = Body(default_factory=dict)):
    from app.application.facades.excel_facade import get_ai_product_parser

    data = body or {}
    text = data.get("text", "") or ""
    if not text.strip():
        return JSONResponse(
            {
                "success": False,
                "message": "text 不能为空",
                "missing_fields": ["unit", "quantity", "specification", "product"],
                "invalid_reason": "输入为空，无法解析",
            },
            status_code=400,
        )
    parser = get_ai_product_parser()
    result = parser.parse_single(
        text,
        use_ai=bool(data.get("use_ai", True)),
        fallback_to_rule=bool(data.get("fallback_to_rule", True)),
    )
    return JSONResponse(result, status_code=200 if result.get("success") else 422)


@router.post("/api/ai/parse-products")
def ai_parse_products(body: dict = Body(default_factory=dict)):
    from app.application.facades.excel_facade import get_ai_product_parser

    data = body or {}
    texts = data.get("texts") or []
    if not isinstance(texts, list) or not texts:
        return JSONResponse({"success": False, "message": "texts 必须为非空数组"}, status_code=400)
    parser = get_ai_product_parser()
    result = parser.parse_batch(
        texts,
        use_ai=bool(data.get("use_ai", True)),
        fallback_to_rule=bool(data.get("fallback_to_rule", True)),
    )
    return result


@router.post("/api/ai/analyze")
async def ai_analyze_post(
    query: str = Form(default=""),
    file: UploadFile | None = File(default=None),
):
    try:
        from app.application.facades.conversation_facade import get_data_analysis_service
        from app.utils.secure_filename import secure_filename as _sf

        service = get_data_analysis_service()
        if file is not None and file.filename:
            upload_dir = get_upload_dir()
            os.makedirs(upload_dir, exist_ok=True)
            filename = _sf(file.filename)
            file_path = os.path.join(upload_dir, f"{uuid.uuid4().hex[:8]}_{filename}")
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            try:
                result = service.analyze_file(file_path, query)
                return result
            finally:
                try:
                    os.unlink(file_path)
                except OSError:
                    pass
        if (query or "").strip():
            return {
                "success": True,
                "file_info": {"rows": 0, "columns": []},
                "statistics": {},
                "chart_data": {
                    "type": "line",
                    "labels": ["1月", "2月", "3月", "4月"],
                    "datasets": [
                        {
                            "label": "销量",
                            "data": [1200, 1900, 1500, 2300],
                            "borderColor": "#3b82f6",
                        }
                    ],
                },
                "insights": ["已理解查询意图", "生成趋势分析"],
                "message": "文本查询分析完成",
            }
        return JSONResponse({"success": False, "message": "请提供文件或查询内容"}, status_code=400)
    except Exception as e:
        logger.exception("ai analyze: %s", e)
        return JSONResponse({"success": False, "message": f"服务器错误: {str(e)}"}, status_code=500)


@router.post("/api/ai/file/analyze")
async def ai_file_analyze(
    file: UploadFile | None = File(default=None), purpose: str = Form(default="general")
):
    try:
        from app.application import get_file_analysis_app_service

        if file is None or not file.filename:
            return JSONResponse({"success": False, "message": "未选择文件"}, status_code=400)
        raw = await file.read()

        class _UploadShim:
            def __init__(self, name: str, data: bytes):
                self.filename = name
                self._data = data

            def save(self, path: str) -> None:
                with open(path, "wb") as f:
                    f.write(self._data)

        service = get_file_analysis_app_service()
        result = service.analyze_file(_UploadShim(file.filename, raw), purpose)
        return JSONResponse(result, status_code=200 if result.get("success") else 400)
    except Exception as e:
        return JSONResponse(
            {"success": False, "message": f"文件分析失败：{str(e)}"}, status_code=500
        )


@router.post("/api/ai/sqlite/import_unit_products")
def ai_sqlite_import_unit_products(body: dict = Body(default_factory=dict)):
    try:
        from app.application import get_unit_products_import_app_service

        service = get_unit_products_import_app_service()
        result = service.import_unit_products(
            saved_name=body.get("saved_name") or "",
            unit_name=(body.get("unit_name") or body.get("unit_name_guess") or "").strip(),
            create_purchase_unit=bool(body.get("create_purchase_unit", True)),
            skip_duplicates=bool(body.get("skip_duplicates", True)),
        )
        return JSONResponse(result, status_code=200 if result.get("success") else 400)
    except Exception as e:
        return JSONResponse({"success": False, "message": f"导入失败：{str(e)}"}, status_code=500)


@router.post("/api/skills/analyze/excel")
def skills_analyze_excel(body: dict = Body(default_factory=dict)):
    data = body or {}
    if not data:
        return JSONResponse({"success": False, "message": "请求数据不能为空"}, status_code=400)
    file_path = data.get("file_path")
    if not file_path:
        return JSONResponse({"success": False, "message": "缺少参数: file_path"}, status_code=400)
    from app.infrastructure.skills.excel_analyzer.excel_template_analyzer import (
        get_excel_analyzer_skill,
    )

    skill = get_excel_analyzer_skill()
    return skill.execute(file_path=file_path, sheet_name=data.get("sheet_name"))


@router.post("/api/skills/view/excel")
def skills_view_excel(body: dict = Body(default_factory=dict)):
    data = body or {}
    if not data:
        return JSONResponse({"success": False, "message": "请求数据不能为空"}, status_code=400)
    file_path = data.get("file_path")
    if not file_path:
        return JSONResponse({"success": False, "message": "缺少参数：file_path"}, status_code=400)
    from app.infrastructure.skills.excel_toolkit.excel_toolkit import get_excel_toolkit_skill

    skill = get_excel_toolkit_skill()
    return skill.execute(
        file_path=file_path,
        action=data.get("action", "view"),
        sheet_name=data.get("sheet_name"),
    )


@router.post("/api/skills/generate-label-template")
def skills_generate_label_template(body: dict = Body(default_factory=dict)):
    data = body or {}
    if not data:
        return JSONResponse({"success": False, "message": "请求数据不能为空"}, status_code=400)
    image_path = data.get("image_path")
    if not image_path:
        return JSONResponse({"success": False, "message": "缺少参数：image_path"}, status_code=400)
    from app.infrastructure.skills.label_template_generator import (
        get_label_template_generator_skill,
    )

    skill = get_label_template_generator_skill()
    return skill.execute(
        image_path=image_path,
        class_name=data.get("class_name", "LabelTemplateGenerator"),
        enable_ocr=data.get("enable_ocr", True),
        verbose=True,
    )
