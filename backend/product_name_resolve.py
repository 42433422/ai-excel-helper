"""
按「品名」提示词在 products 主数据中解析型号（与销售合同 ``name_hint`` 对齐逻辑一致）。

用于前端口语订货、仅中文品名无型号时的批量对齐；**唯一**命中才视为解析成功，
多条同名/子串命中时返回 ``ambiguous`` 供 UI 或人工选择。
"""

from __future__ import annotations

import logging
from typing import Any

from backend.sales_contract_product_match import name_compatible_with_row

logger = logging.getLogger(__name__)


def _compact_name(value: Any) -> str:
    return "".join(str(value or "").strip().lower().split())


def _slim_product_row(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": p.get("id"),
        "model_number": str(p.get("model_number") or "").strip(),
        "name": str(p.get("name") or "").strip(),
        "specification": str(p.get("specification") or p.get("spec") or "").strip(),
        "unit": str(p.get("unit") or "").strip(),
        "price": p.get("price", 0),
    }


def _rows_matching_name_hint(name_hint: str, all_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nh = (name_hint or "").strip()
    if len(_compact_name(nh)) < 2:
        return []
    matches: list[dict[str, Any]] = []
    for p in all_rows:
        if name_compatible_with_row(nh, p):
            matches.append(p)
    return matches


def resolve_product_name_hints(
    hints: list[str],
    *,
    purchase_unit: str | None = None,
    max_candidates: int = 8,
) -> list[dict[str, Any]]:
    """
    对每个 ``hint`` 返回一条结果描述：
    ``{ "hint", "status": "unique"|"ambiguous"|"none", "product"?, "candidates"? }``
    """
    try:
        # 延迟导入：避免 ``xcagi_compat`` 装载路由时与本模块形成环依赖
        from backend.routers.xcagi_compat import _load_products_all_for_export

        rows = _load_products_all_for_export(keyword=None, unit=(purchase_unit or None))
    except Exception as e:
        logger.warning("resolve_product_name_hints: load products failed: %s", e)
        rows = []

    all_rows = list(rows or [])
    seen: set[str] = set()
    ordered_hints: list[str] = []
    for h in hints or []:
        t = str(h or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        ordered_hints.append(t)

    out: list[dict[str, Any]] = []
    for hint in ordered_hints:
        matches = _rows_matching_name_hint(hint, all_rows)
        if len(matches) == 1:
            out.append({"hint": hint, "status": "unique", "product": _slim_product_row(matches[0])})
        elif len(matches) > 1:
            cands = [_slim_product_row(p) for p in matches[:max_candidates]]
            out.append({"hint": hint, "status": "ambiguous", "candidates": cands})
        else:
            out.append({"hint": hint, "status": "none"})
    return out
