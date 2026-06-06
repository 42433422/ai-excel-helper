"""Workflow tools application facade (Phase 4B absorbed)."""

from __future__ import annotations

from app.application.tools.exports import handle_price_list_export  # noqa: F401
from app.application.tools.workflow import (  # noqa: F401
    execute_workflow_tool,
    get_workflow_tool_registry,
    handle_excel_analysis,
    resolve_safe_excel_path,
    run_natural_language_pandas,
)

__all__ = [
    "execute_workflow_tool",
    "get_workflow_tool_registry",
    "handle_excel_analysis",
    "handle_price_list_export",
    "resolve_safe_excel_path",
    "run_natural_language_pandas",
]


_LOST_LEGACY_SYMBOLS = frozenset(
    {
        "flatten_tool_result_dict_for_client",
        "get_last_tool_result",
    }
)


def __getattr__(name: str):
    if name in _LOST_LEGACY_SYMBOLS:
        raise ImportError(
            f"{name!r} is not implemented in app.application.tools; "
            "this function was lost in the backend → app.legacy cleanup."
        )
    raise AttributeError(f"module 'app.application.tools' has no attribute {name!r}")
