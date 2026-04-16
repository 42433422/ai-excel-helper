"""
Unified template handler for Word (.docx) and Excel (.xlsx) templates.
Provides automatic template type detection and unified processing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from backend.word_template import (
    handle_word_template,
    get_word_tool_registry,
    resolve_safe_word_path,
)
from backend.excel_template import (
    handle_excel_template,
    get_excel_template_tool_registry,
    resolve_safe_excel_path,
)


_ALLOWED_EXTENSIONS = {".docx", ".xlsx", ".xlsm"}


def detect_template_type(file_path: str) -> str | None:
    """
    Detect template type based on file extension.
    Returns: "word", "excel", or None if unsupported.
    """
    suffix = Path(file_path).suffix.lower()
    if suffix == ".docx":
        return "word"
    if suffix in (".xlsx", ".xlsm"):
        return "excel"
    return None


def resolve_template_path(workspace_root: str, file_path: str, template_type: str) -> Path:
    """
    Resolve file_path to an absolute path based on template type.
    """
    if template_type == "word":
        return resolve_safe_word_path(workspace_root, file_path)
    elif template_type == "excel":
        return resolve_safe_excel_path(workspace_root, file_path)
    else:
        raise ValueError(f"Unsupported template type: {template_type}")


def handle_template(
    arguments: Mapping[str, Any],
    workspace_root: str | None = None,
) -> dict[str, Any]:
    """
    Unified entry point for all template operations.
    Automatically detects template type and dispatches to appropriate handler.

    Actions: parse, fill, export, cleanup
    """
    file_path = arguments.get("file_path")
    action = (arguments.get("action") or "").lower()

    if action == "cleanup":
        from backend.word_template import cleanup_price_data as word_cleanup
        from backend.excel_template import cleanup_price_data as excel_cleanup

        raw_data = arguments.get("raw_data") or arguments.get("records") or []
        customer_name = arguments.get("customer_name")
        quote_date = arguments.get("quote_date")

        word_result = word_cleanup(raw_data, customer_name, quote_date)
        excel_result = excel_cleanup(raw_data, customer_name, quote_date)

        if excel_result.get("unmatched_products") or word_result.get("unmatched_products"):
            return excel_result

        return word_result

    if not file_path:
        return {"error": "missing_file_path"}

    root = workspace_root or ""
    template_type = detect_template_type(file_path)

    if not template_type:
        return {
            "error": "unsupported_template_type",
            "file_path": file_path,
            "supported_types": ["docx", "xlsx", "xlsm"],
        }

    try:
        resolve_template_path(root, file_path, template_type)
    except (OSError, ValueError, PermissionError) as e:
        return {"error": "path_resolution_failed", "message": str(e)}

    if template_type == "word":
        result = handle_word_template(arguments, workspace_root=workspace_root)
        if isinstance(result, dict):
            result["template_color"] = "blue"
            result["template_type"] = "word"
        return result
    elif template_type == "excel":
        result = handle_excel_template(arguments, workspace_root=workspace_root)
        if isinstance(result, dict):
            result["template_color"] = "green"
            result["template_type"] = "excel"
        return result

    return {"error": "unknown_error"}


def get_template_tool_registry() -> list[dict[str, Any]]:
    """
    Get combined tool registry for both Word and Excel templates.
    Used for LLM tool registration.
    """
    return get_word_tool_registry() + get_excel_template_tool_registry()
