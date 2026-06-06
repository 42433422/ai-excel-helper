"""
模板与 Excel 预览辅助（从归档 templates 迁移）。

本包将原 ``document_templates_service.py`` 拆分为四个子模块：
- variables: 词条/作用域/验证逻辑
- renderer: Excel 预览/渲染函数
- crud: 模板 CRUD 操作
- analyzer: 模板分析逻辑

所有公共符号在此重新导出，确保现有导入路径不变。
"""

from __future__ import annotations

from app.services.document_templates.analyzer import (
    analysis_progress,
    analyze_template_with_upload,
    progress_lock,
)
from app.services.document_templates.crud import (
    _build_template_payload_from_row,
    _ensure_template_tables_ready,
    _j,
    _normalize_db_template_id,
    create_template_with_payload,
    update_template_with_payload,
)
from app.services.document_templates.renderer import (
    _extract_excel_all_sheets_preview,
    _extract_excel_grid_preview,
    _extract_excel_grid_style_cache,
    _extract_logical_tables_from_sheet,
    _extract_structured_excel_preview,
    _is_unreadable_workbook_error,
    _list_excel_sheet_names,
    _parse_json_dict,
    _parse_json_list,
)
from app.services.document_templates.variables import (
    _DEFAULT_TEMPLATE_SCOPE_RULES,
    _TERM_EQUIVALENTS,
    _build_scope_template_type_map,
    _get_equivalent_normalized_terms,
    _get_template_scope_required_terms,
    _has_equivalent_term,
    _infer_business_scope,
    _load_template_scope_required_terms,
    _normalize_term,
    _validate_required_terms,
)

__all__ = [
    "_DEFAULT_TEMPLATE_SCOPE_RULES",
    "_TERM_EQUIVALENTS",
    "_build_scope_template_type_map",
    "_build_template_payload_from_row",
    "_ensure_template_tables_ready",
    "_extract_excel_all_sheets_preview",
    "_extract_excel_grid_preview",
    "_extract_excel_grid_style_cache",
    "_extract_logical_tables_from_sheet",
    "_extract_structured_excel_preview",
    "_get_equivalent_normalized_terms",
    "_get_template_scope_required_terms",
    "_has_equivalent_term",
    "_infer_business_scope",
    "_is_unreadable_workbook_error",
    "_j",
    "_list_excel_sheet_names",
    "_load_template_scope_required_terms",
    "_normalize_db_template_id",
    "_normalize_term",
    "_parse_json_dict",
    "_parse_json_list",
    "_validate_required_terms",
    "analysis_progress",
    "analyze_template_with_upload",
    "create_template_with_payload",
    "progress_lock",
    "update_template_with_payload",
]
