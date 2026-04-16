"""
销售合同草稿行与主数据产品对齐。

借鉴 ``XCAGI/app/domain/shipment/shipment_product_parser.match_product``：
型号精确（忽略空格/中划线）→ 同型号多行时用语义名称消歧（与发货单「编号+名称」一致）
→ 无型号时仅按名称唯一命中；同型号无法消歧时取首条（与 shipment 一致）。
"""

from __future__ import annotations

import re
from typing import Any, Callable, Mapping

_ModelIndex = dict[str, dict[str, Any]]
_ResolveModelFn = Callable[[str, _ModelIndex], str]


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_model_token(value: Any) -> str:
    return normalize_text(value).replace(" ", "").replace("-", "")


def specification_to_numeric_kg(value: Any) -> float | None:
    """从规格串中取首个数字（如 18KG/桶 → 18），备用于扩展消歧。"""
    s = str(value or "").strip()
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _compact_name(value: Any) -> str:
    return "".join(str(value or "").strip().lower().split())


def name_compatible_with_row(name_hint: str, row: Mapping[str, Any]) -> bool:
    nh = _compact_name(name_hint)
    pn = _compact_name(row.get("name") or "")
    if not nh or not pn:
        return False
    if nh == pn:
        return True
    if len(nh) >= 3 and (nh in pn or pn in nh):
        return True
    return False


def _rows_with_same_normalized_model(norm: str, all_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not norm:
        return []
    return [p for p in all_rows if normalize_model_token(p.get("model_number")) == norm]


def match_product_row_for_sales_contract(
    *,
    name_hint: str | None,
    model_hint: str | None,
    all_rows: list[dict[str, Any]],
    product_index: dict[str, dict[str, Any]],
    resolve_model_number: _ResolveModelFn,
) -> tuple[str, dict[str, Any]] | None:
    """
    将单行草稿（型号/品名提示）对齐到主数据一行。

    返回 ``(model_number, db_row)``；无法对齐时返回 ``None``。
    """
    nh = (name_hint or "").strip()
    mh = (model_hint or "").strip()

    if mh:
        raw_tok = "".join(mh.split())
        resolved_key = resolve_model_number(raw_tok, product_index)
        norm = normalize_model_token(resolved_key or raw_tok)
        hits = _rows_with_same_normalized_model(norm, all_rows)
        if hits:
            if len(hits) == 1:
                p = hits[0]
                return (str(p.get("model_number") or "").strip(), p)
            if nh:
                named = [p for p in hits if name_compatible_with_row(nh, p)]
                if len(named) >= 1:
                    p = named[0]
                    return (str(p.get("model_number") or "").strip(), p)
            p = hits[0]
            return (str(p.get("model_number") or "").strip(), p)

    if nh:
        nhc = _compact_name(nh)
        if len(nhc) < 2:
            return None
        matches: list[dict[str, Any]] = []
        for p in all_rows:
            pn = _compact_name(p.get("name") or "")
            if not pn:
                continue
            if pn == nhc or (len(nhc) >= 3 and (nhc in pn or pn in nhc)):
                matches.append(p)
        if len(matches) != 1:
            return None
        p = matches[0]
        return (str(p.get("model_number") or "").strip(), p)

    return None
