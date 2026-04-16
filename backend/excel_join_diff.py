"""
多 Excel 按键 Join；或两表基于主键做行级差异对比。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def load_excel(path: Path, sheet_name: str | int | None, header_row: int) -> pd.DataFrame:
    kwargs: dict[str, Any] = {"engine": "openpyxl", "header": header_row}
    kwargs["sheet_name"] = 0 if sheet_name is None else sheet_name
    return pd.read_excel(path, **kwargs)


def join_frames(
    frames: list[pd.DataFrame],
    join_keys: list[str],
    how: str = "inner",
) -> dict[str, Any]:
    if len(frames) < 2:
        return {"error": "need_at_least_two_frames"}
    how = how.lower()
    if how not in ("inner", "left", "right", "outer"):
        return {"error": "invalid_how", "allowed": ["inner", "left", "right", "outer"]}

    for i, df in enumerate(frames):
        miss = [k for k in join_keys if k not in df.columns]
        if miss:
            return {"error": "missing_join_keys", "frame_index": i, "missing": miss}

    out = frames[0]
    for j in range(1, len(frames)):
        out = pd.merge(out, frames[j], on=join_keys, how=how, suffixes=(f"_{j-1}", f"_{j}"))

    cap = 500
    total = len(out)
    head = out.head(cap)
    records = json.loads(head.replace({np.nan: None}).to_json(orient="records", date_format="iso"))
    return {
        "action": "join",
        "how": how,
        "join_keys": join_keys,
        "row_count": total,
        "truncated": total > cap,
        "returned_rows": len(head),
        "columns": list(out.columns.astype(str)),
        "records": records,
    }


def diff_frames(
    dfa: pd.DataFrame,
    dfb: pd.DataFrame,
    key_columns: list[str],
    compare_columns: list[str] | None = None,
    max_rows_per_section: int = 200,
) -> dict[str, Any]:
    miss_a = [k for k in key_columns if k not in dfa.columns]
    miss_b = [k for k in key_columns if k not in dfb.columns]
    if miss_a or miss_b:
        return {"error": "missing_keys", "left_missing": miss_a, "right_missing": miss_b}

    dup_a = dfa.duplicated(subset=key_columns).sum()
    dup_b = dfb.duplicated(subset=key_columns).sum()
    if dup_a or dup_b:
        return {
            "error": "duplicate_keys",
            "left_duplicates": int(dup_a),
            "right_duplicates": int(dup_b),
            "hint": "请先对主键去重或指定唯一业务键。",
        }

    overlap = [c for c in dfa.columns if c in dfb.columns and c not in key_columns]
    if compare_columns is not None:
        overlap = [c for c in compare_columns if c in overlap]
    if not overlap:
        return {"error": "no_comparable_columns", "hint": "除键外无共同列可对比。"}

    merged = pd.merge(
        dfa,
        dfb,
        on=key_columns,
        how="outer",
        indicator=True,
        suffixes=("_left", "_right"),
    )

    only_left = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])
    only_right = merged[merged["_merge"] == "right_only"].drop(columns=["_merge"])
    both = merged[merged["_merge"] == "both"].drop(columns=["_merge"])

    def _cell_differs(va: Any, vb: Any) -> bool:
        if pd.isna(va) and pd.isna(vb):
            return False
        if pd.isna(va) or pd.isna(vb):
            return True
        try:
            fa, fb = float(va), float(vb)
            if np.isfinite(fa) and np.isfinite(fb):
                return not np.isclose(fa, fb, rtol=1e-5, atol=1e-8)
        except (TypeError, ValueError):
            pass
        return str(va) != str(vb)

    changes: list[dict[str, Any]] = []
    for _, row in both.iterrows():
        diffs: dict[str, dict[str, Any]] = {}
        for c in overlap:
            la, rb = f"{c}_left", f"{c}_right"
            if la not in row.index or rb not in row.index:
                continue
            va, vb = row[la], row[rb]
            if _cell_differs(va, vb):
                diffs[c] = {"left": va, "right": vb}
        if diffs:
            entry = {k: row[k] for k in key_columns}
            entry["changed_fields"] = diffs
            changes.append(entry)

    def pack(df: pd.DataFrame) -> dict[str, Any]:
        total = len(df)
        h = df.head(max_rows_per_section)
        rec = json.loads(h.replace({np.nan: None}).to_json(orient="records", date_format="iso"))
        return {"count": total, "truncated": total > max_rows_per_section, "records": rec}

    return {
        "action": "diff",
        "key_columns": key_columns,
        "compared_columns": overlap,
        "only_in_left": pack(only_left),
        "only_in_right": pack(only_right),
        "rows_with_value_changes": {
            "count": len(changes),
            "truncated": len(changes) > max_rows_per_section,
            "records": changes[:max_rows_per_section],
        },
    }
