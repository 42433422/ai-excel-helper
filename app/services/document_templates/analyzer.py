from __future__ import annotations

import logging
import os
import re
import threading
import uuid
import zipfile
from xml.etree import ElementTree as ET

from app.http.json_response import json_response
from app.services.document_templates.renderer import (
    _extract_excel_grid_preview,
    _extract_structured_excel_preview,
)
from app.services.document_templates.variables import (
    _get_template_scope_required_terms,
    _validate_required_terms,
)
from app.template_analysis_progress import (
    clear_template_analysis_progress,
    set_template_analysis_progress,
)

logger = logging.getLogger(__name__)

analysis_progress = {}
progress_lock = threading.Lock()


def _safe_remove(path: str) -> None:
    """删除已上传的临时/持久文件（失败路径清理用）。"""
    try:
        if path and os.path.isfile(path):
            os.remove(path)
    except OSError as e:
        logger.warning("删除上传文件失败: %s, %s", path, e)


def _cleanup_progress_tracking(task_id: str) -> None:
    with progress_lock:
        if task_id in analysis_progress:
            del analysis_progress[task_id]
    clear_template_analysis_progress(task_id)


def _j(data: dict, status: int = 200):
    return json_response(data, status)


def _update_progress(task_id: str, percent: int, step: int, message: str):
    completed = False
    with progress_lock:
        if task_id in analysis_progress:
            analysis_progress[task_id].update(
                {"percent": percent, "step": step, "message": message}
            )
            completed = bool(analysis_progress[task_id].get("completed"))
    set_template_analysis_progress(
        task_id,
        percent=percent,
        step=step,
        message=message,
        completed=completed,
    )


def _mark_progress_completed(task_id: str, percent: int, step: int, message: str) -> None:
    with progress_lock:
        if task_id in analysis_progress:
            analysis_progress[task_id].update(
                {"percent": percent, "step": step, "message": message, "completed": True}
            )
    set_template_analysis_progress(
        task_id, percent=percent, step=step, message=message, completed=True
    )


def analyze_template_with_upload(file, template_name: str = "", template_scope: str = ""):
    return _analyze_template_with_upload_inner(file, template_name, template_scope)


def _analyze_template_with_upload_inner(file, template_name: str, template_scope: str):
    try:
        logger.info("收到 analyze 请求（headless），filename=%s", getattr(file, "filename", None))

        if file is None:
            logger.error("没有上传文件")
            return _j({"success": False, "message": "没有上传文件"}, 400)
        logger.info(f"文件名：{file.filename}, 模板名：{template_name}")

        if file.filename == "":
            logger.error("文件名为空")
            return _j({"success": False, "message": "文件名为空"}, 400)
        file_ext = os.path.splitext(file.filename)[1].lower()

        upload_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "uploads", "templates"
        )
        os.makedirs(upload_dir, exist_ok=True)

        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)

        task_id = uuid.uuid4().hex
        with progress_lock:
            analysis_progress[task_id] = {
                "percent": 0,
                "step": 1,
                "message": "准备上传文件...",
                "completed": False,
            }
        set_template_analysis_progress(
            task_id, percent=0, step=1, message="准备上传文件...", completed=False
        )

        if file_ext in [".xlsx", ".xls"]:
            return _analyze_excel_template(
                file_path, template_name, file.filename, task_id, template_scope
            )
        if file_ext == ".docx":
            return _analyze_word_template(
                file_path, template_name, file.filename, task_id, template_scope
            )
        if file_ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
            return _analyze_label_template(file_path, template_name, file.filename, task_id)

        _cleanup_progress_tracking(task_id)
        _safe_remove(file_path)
        return _j({"success": False, "message": f"不支持的文件类型：{file_ext}"}, 400)

    except Exception as e:
        logger.error(f"分析模板失败：{e}")
        import traceback

        traceback.print_exc()

        return _j({"success": False, "message": f"分析失败：{str(e)}"}, 500)


def _analyze_excel_template(
    file_path: str,
    template_name: str,
    original_filename: str,
    task_id: str,
    template_scope: str = "",
):
    try:
        from app.infrastructure.skills.excel_analyzer.excel_template_analyzer import (
            get_excel_analyzer_skill,
        )

        _update_progress(task_id, 10, 1, "文件上传成功")

        skill = get_excel_analyzer_skill()

        _update_progress(task_id, 50, 2, "分析 Excel 结构...")

        analyze_result = skill.execute(file_path=file_path, sheet_name="出货")

        if not analyze_result.get("success"):
            _cleanup_progress_tracking(task_id)
            _safe_remove(file_path)
            return _j(
                {"success": False, "message": analyze_result.get("error", "Excel 分析失败")},
                500,
            )

        cells = analyze_result.get("cells", {})
        editable_entries = analyze_result.get("editable_ranges", [])
        merged_cells = analyze_result.get("merged_cells", [])
        structure = analyze_result.get("structure", {})

        structured = _extract_structured_excel_preview(file_path, sheet_name="出货", sample_limit=8)
        grid_preview = _extract_excel_grid_preview(
            file_path, sheet_name="出货", max_rows=18, max_cols=12
        )
        fields = structured.get("fields") or []

        if not fields:
            for _, cell_info in list(cells.items())[:25]:
                if cell_info.get("value") and cell_info.get("purpose") != " 系统保留":
                    fields.append(
                        {
                            "label": str(cell_info.get("value", "")),
                            "value": "",
                            "type": "dynamic",
                        }
                    )

        valid, missing_terms = _validate_required_terms(cells, fields, template_scope)
        if not valid:
            _cleanup_progress_tracking(task_id)
            _safe_remove(file_path)
            return _j(
                {
                    "success": False,
                    "message": "模板缺少必备词条，请补全后重试",
                    "required_terms": _get_template_scope_required_terms().get(template_scope, []),
                    "missing_terms": missing_terms,
                },
                400,
            )

        sample_rows = structured.get("sample_rows") or []

        name = (
            template_name
            if template_name
            else original_filename.replace(".xlsx", "").replace(".xls", "")
        )

        _mark_progress_completed(task_id, 100, 3, "分析完成！")

        return _j(
            {
                "success": True,
                "task_id": task_id,
                "template_name": name,
                "template_type": "excel",
                "fields": fields,
                "preview_data": {
                    "cells": cells,
                    "editable_ranges": editable_entries,
                    "merged_cells": merged_cells,
                    "sample_rows": sample_rows,
                    "structure": structure,
                    "sheet_name": structured.get("sheet_name") or "出货",
                    "grid_preview": grid_preview,
                    "file_path": file_path,
                    "original_filename": original_filename,
                },
            }
        )
    except Exception as e:
        logger.error(f"分析 Excel 模板失败：{e}")
        import traceback

        traceback.print_exc()
        _cleanup_progress_tracking(task_id)
        _safe_remove(file_path)

        return _j({"success": False, "message": f"分析 Excel 失败：{str(e)}"}, 500)


_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W_T = f"{{{_W_NS}}}t"


def _collect_docx_part_text(xml_bytes: bytes) -> str:
    """拼接 OOXML 中 w:t 文本（忽略复杂域，占位符通常落在 w:t 中）。"""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return ""
    parts: list[str] = []
    for node in root.iter(_W_T):
        if node.text:
            parts.append(node.text)
        if node.tail:
            parts.append(node.tail)
    return "".join(parts)


def _list_docx_xml_parts(names: list[str]) -> list[str]:
    pat = re.compile(r"^word/(document\.xml|header\d+\.xml|footer\d+\.xml)$")
    out = [n for n in names if pat.match(n)]
    if "word/document.xml" in names and "word/document.xml" not in out:
        out.append("word/document.xml")
    return sorted(set(out))


def _extract_word_placeholder_fields(file_path: str) -> tuple[list[dict], list[str], str]:
    """从 .docx 正文中提取占位符，生成与 Excel 分析一致的 fields 结构。"""
    patterns = (
        re.compile(r"\{\{\s*([^}]+?)\s*\}\}"),
        re.compile(r"\{\%\s*([^\%]+?)\s*\%\}"),
        re.compile(r"\$\{\s*([^}]+?)\s*\}"),
        re.compile(r"\[\[\s*([^\]]+?)\s*\]\]"),
    )
    blobs: list[str] = []
    with zipfile.ZipFile(file_path, "r") as zf:
        for part in _list_docx_xml_parts(zf.namelist()):
            try:
                blobs.append(_collect_docx_part_text(zf.read(part)))
            except (KeyError, OSError, ET.ParseError) as e:
                logger.debug("跳过 docx 部件 %s: %s", part, e)
    full_text = "\n".join(blobs)
    raw_tokens: list[str] = []
    for pat in patterns:
        for m in pat.finditer(full_text):
            token = str(m.group(1) or "").strip()
            if token and token not in raw_tokens:
                raw_tokens.append(token)
    fields: list[dict] = []
    for token in raw_tokens:
        fields.append({"label": token, "value": "", "type": "dynamic"})
    return fields, raw_tokens, full_text


def _analyze_word_template(
    file_path: str,
    template_name: str,
    original_filename: str,
    task_id: str,
    template_scope: str = "",
):
    try:
        _update_progress(task_id, 15, 1, "文件上传成功")
        _update_progress(task_id, 45, 2, "解析 Word 占位符...")

        fields, raw_placeholders, full_text = _extract_word_placeholder_fields(file_path)
        if not fields:
            _cleanup_progress_tracking(task_id)
            _safe_remove(file_path)
            return _j(
                {
                    "success": False,
                    "message": (
                        "未能从 Word 中识别占位符。请在正文、页眉或页脚中使用 "
                        "{{字段名}}、${字段名}、{% 字段名 %} 或 [[字段名]] 等形式后再上传。"
                    ),
                },
                400,
            )

        valid, missing_terms = _validate_required_terms({}, fields, template_scope)
        if not valid:
            _cleanup_progress_tracking(task_id)
            _safe_remove(file_path)
            return _j(
                {
                    "success": False,
                    "message": "模板缺少必备词条，请补全占位符后重试",
                    "required_terms": _get_template_scope_required_terms().get(template_scope, []),
                    "missing_terms": missing_terms,
                },
                400,
            )

        name = (
            template_name
            if template_name
            else original_filename.replace(".docx", "").replace(".doc", "")
        )

        snippet = full_text.strip().replace("\n", " ")
        if len(snippet) > 400:
            snippet = snippet[:400] + "…"

        _mark_progress_completed(task_id, 100, 3, "分析完成！")

        return _j(
            {
                "success": True,
                "task_id": task_id,
                "template_name": name,
                "template_type": "word",
                "fields": fields,
                "preview_data": {
                    "file_path": file_path,
                    "original_filename": original_filename,
                    "placeholders": raw_placeholders,
                    "text_snippet": snippet,
                },
            }
        )
    except Exception as e:
        logger.error(f"分析 Word 模板失败：{e}")
        import traceback

        traceback.print_exc()
        _cleanup_progress_tracking(task_id)
        _safe_remove(file_path)

        return _j({"success": False, "message": f"分析 Word 失败：{str(e)}"}, 500)


def _analyze_label_template(
    file_path: str, template_name: str, original_filename: str, task_id: str
):
    try:
        from app.services.skills.label_template_generator.label_template_generator import (
            LabelTemplateGeneratorSkill,
        )

        _update_progress(task_id, 10, 1, "文件上传成功")

        skill = LabelTemplateGeneratorSkill()

        _update_progress(task_id, 25, 2, "检测表格网格...")

        ocr_result = skill.execute(
            image_path=file_path,
            class_name=(
                template_name.replace(" ", "") + "Generator" if template_name else "LabelGenerator"
            ),
            enable_ocr=True,
            verbose=True,
        )

        _update_progress(task_id, 75, 3, "OCR 识别文字...")

        _update_progress(task_id, 90, 4, "分析字段...")

        logger.info(f"OCR 识别结果：{ocr_result}")

        if ocr_result.get("success"):
            fields = []

            image_analysis = ocr_result.get("analysis", {})
            ocr_data = ocr_result.get("ocr_result", {})

            if ocr_data and ocr_data.get("fields"):
                ocr_fields = ocr_data["fields"]
                logger.info(f"OCR 提取到 {len(ocr_fields)} 个字段")

                import uuid

                for field in ocr_fields:
                    logger.info(f"字段：{field}")
                    fields.append(
                        {
                            "id": uuid.uuid4().hex,
                            "label": field.get("label", ""),
                            "value": field.get("value", ""),
                            "type": "fixed" if field.get("type") == "fixed_label" else "dynamic",
                            "position": field.get("position", {}),
                            "confidence": field.get("confidence", 0),
                        }
                    )
            else:
                logger.warning("OCR 未提取到字段，使用默认字段")
                fields = [
                    {"label": "品名", "value": "示例产品", "type": "fixed"},
                    {"label": "货号", "value": "00000", "type": "dynamic"},
                    {"label": "颜色", "value": "黑色", "type": "dynamic"},
                    {"label": "码段", "value": "00000", "type": "dynamic"},
                    {"label": "等级", "value": "合格品", "type": "fixed"},
                    {"label": "执行标准", "value": "QB/Txxxx-xxxx", "type": "fixed"},
                    {"label": "统一零售价", "value": "¥0", "type": "dynamic"},
                ]

            name = (
                template_name
                if template_name
                else original_filename.replace(
                    "." + original_filename.rsplit(".", maxsplit=1)[-1], ""
                )
            )

            _mark_progress_completed(task_id, 100, 4, "分析完成！")

            preview_data = {
                "image_path": file_path,
                "original_filename": original_filename,
                "image_size": image_analysis.get("size", {}),
                "colors": image_analysis.get("colors", {}),
                "ocr_fields": fields,
            }

            if ocr_data and ocr_data.get("grid"):
                preview_data["grid"] = ocr_data["grid"]
                logger.info(f"网格信息：{ocr_data['grid']}")
            else:
                logger.warning("未找到网格信息")

            return _j(
                {
                    "success": True,
                    "task_id": task_id,
                    "template_name": name,
                    "template_type": "label",
                    "fields": fields,
                    "generated_code": ocr_result.get("code", ""),
                    "preview_data": preview_data,
                }
            )
        else:
            _cleanup_progress_tracking(task_id)
            _safe_remove(file_path)
            return _j({"success": False, "message": ocr_result.get("error", "标签生成失败")}, 500)
    except Exception as e:
        logger.error(f"分析标签模板失败：{e}")
        import traceback

        traceback.print_exc()
        _cleanup_progress_tracking(task_id)
        _safe_remove(file_path)

        return _j({"success": False, "message": f"分析标签失败：{str(e)}"}, 500)
