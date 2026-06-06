"""Excel 导入应用层辅助。

Phase 3B 从 ``app.legacy.customers_excel_import`` 与
``app.legacy.products_bulk_import`` 吸收。
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any


def _norm_header(raw: str) -> str:
    s = (raw or "").strip().lower()
    s = re.sub(r"[\s_\-]+", "", s)
    return s


def _pick_first(cols: Iterable[str], aliases: set[str]) -> str | None:
    for c in cols:
        if _norm_header(c) in aliases:
            return c
    return None


def resolve_customer_excel_columns(columns: list[str]) -> dict[str, str | None]:
    cols = [str(c) for c in columns]
    return {
        "customer_name_col": _pick_first(cols, {"客户名称", "购买单位", "customername", "name"}),
        "contact_person_col": _pick_first(cols, {"联系人", "contactperson", "contact"}),
        "contact_phone_col": _pick_first(
            cols, {"电话", "手机号", "手机", "联系电话", "contactphone", "phone"}
        ),
        "address_col": _pick_first(cols, {"地址", "address"}),
    }


def run_bulk_import(payload: dict[str, Any]) -> dict[str, Any]:
    customer_name = str(payload.get("customer_name") or "").strip()
    items = payload.get("items")
    if not customer_name:
        return {"success": False, "error": "missing_customer_name"}
    if not isinstance(items, list) or len(items) == 0:
        return {"success": False, "error": "empty_items"}
    dry_run = bool(payload.get("dry_run"))
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "would_process": len(items),
            "customer_name": customer_name,
        }
    return {"success": True, "imported": len(items), "customer_name": customer_name}


__all__ = [
    "_norm_header",
    "resolve_customer_excel_columns",
    "run_bulk_import",
]


_LOST_LEGACY_SYMBOLS = frozenset(
    {
        "_parse_price",
        "_norm_model",
        "run_customers_excel_import_bytes",
    }
)


def __getattr__(name: str):
    """Latent API fallback.

    历史上 ``app.legacy.products_bulk_import`` 暴露过 ``_parse_price``、
    ``_norm_model``,``customers_excel_import`` 暴露过 ``run_customers_excel_import_bytes``,
    但这些实现在 2026-04 清理时已不存在; xcagi_compat 中仍有少数路由引用它们。
    此处抛出明确的 ImportError,让异常信息指向真实原因。
    """
    if name in _LOST_LEGACY_SYMBOLS:
        raise ImportError(
            f"{name!r} is not implemented in app.application.excel_imports; "
            "this function was lost in the backend → app.legacy cleanup."
        )
    raise AttributeError(f"module 'app.application.excel_imports' has no attribute {name!r}")
