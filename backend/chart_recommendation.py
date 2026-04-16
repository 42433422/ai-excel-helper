"""
根据 DataFrame 的列类型、基数与形状，推荐合适的可视化图表类型（规则引擎，无需 LLM）。
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def _is_datetime_series(s: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(s):
        return True
    if s.dtype == object:
        sample = s.dropna().head(30)
        if len(sample) == 0:
            return False
        try:
            t = pd.to_datetime(sample, errors="coerce", format="mixed")
        except (TypeError, ValueError):
            t = pd.to_datetime(sample, errors="coerce")
        return bool(t.notna().mean() >= 0.7)
    return False


def _numeric_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def _categorical_cols(df: pd.DataFrame, max_cardinality: int = 50) -> list[str]:
    out: list[str] = []
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]) or _is_datetime_series(df[c]):
            continue
        nu = df[c].nunique(dropna=True)
        if nu <= max_cardinality and nu >= 1:
            out.append(str(c))
    return out


def _datetime_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if _is_datetime_series(df[c])]


def recommend_charts(df: pd.DataFrame, *, max_suggestions: int = 6) -> dict[str, Any]:
    if df.empty:
        return {"error": "empty_dataframe", "suggestions": []}

    num = _numeric_cols(df)
    cat = _categorical_cols(df)
    dt = _datetime_cols(df)
    n_rows, n_cols = len(df), len(df.columns)

    suggestions: list[dict[str, Any]] = []

    def add(chart_type: str, reason: str, mapping: dict[str, Any], priority: int = 5) -> None:
        suggestions.append(
            {
                "chart_type": chart_type,
                "reason_zh": reason,
                "x": mapping.get("x"),
                "y": mapping.get("y"),
                "series": mapping.get("series"),
                "value": mapping.get("value"),
                "priority": priority,
            }
        )

    # 时间序列 + 指标
    if dt and num:
        add(
            "line",
            "存在日期/时间与数值列，适合折线图观察趋势。",
            {"x": dt[0], "y": num[0]},
            priority=1,
        )
        add(
            "area",
            "同一组合也可用面积图强调量级累积感。",
            {"x": dt[0], "y": num[0]},
            priority=4,
        )

    # 一分类 + 一数值
    if cat and num:
        vc = df.groupby(cat[0])[num[0]].sum(numeric_only=True)
        if len(vc) <= 30:
            add(
                "bar",
                f"分类列「{cat[0]}」基数适中，可对数值列「{num[0]}」做柱状图对比。",
                {"x": cat[0], "y": num[0]},
                priority=2,
            )
        if len(vc) <= 8:
            add(
                "pie",
                "类别很少时可考虑饼图（注意可读性，柱状图通常更稳）。",
                {"category": cat[0], "value": num[0]},
                priority=7,
            )

    # 双数值
    if len(num) >= 2:
        add(
            "scatter",
            "两列数值适合散点图观察相关与分布。",
            {"x": num[0], "y": num[1]},
            priority=3,
        )
        if len(num) >= 3:
            add(
                "scatter_3d_hint",
                "三列及以上数值可考虑散点图用颜色/大小编码第三维，或平行坐标。",
                {"x": num[0], "y": num[1], "series": num[2]},
                priority=8,
            )

    # 双分类 + 数值 → 热力或分组柱
    if len(cat) >= 2 and num:
        add(
            "grouped_bar",
            "两个分类维度 + 度量，可用分组柱状图或数据透视热力图。",
            {"x": cat[0], "series": cat[1], "value": num[0]},
            priority=5,
        )
        add(
            "heatmap",
            "两维分类交叉计数或求和时适合热力图。",
            {"x": cat[0], "y": cat[1], "value": num[0]},
            priority=6,
        )

    # 纯数值多列 → 相关
    if len(num) >= 3:
        add(
            "correlation_heatmap",
            "多列数值可计算相关系数矩阵并以热力图展示。",
            {"columns": num[:12]},
            priority=5,
        )

    # 单列分布
    if len(num) == 1 and not cat and not dt:
        add(
            "histogram",
            "单列数值适合直方图或 KDE 看分布。",
            {"x": num[0]},
            priority=4,
        )

    # 单列分类频数
    if len(cat) == 1 and not num:
        add(
            "bar",
            "可对分类列统计频数后画柱状图。",
            {"x": cat[0], "y": "(count)"},
            priority=3,
        )

    if not suggestions:
        add(
            "table",
            "结构较混合或列类型不明显，可先以表格+基础统计探索。",
            {"columns": list(map(str, df.columns))},
            priority=9,
        )

    suggestions.sort(key=lambda x: x["priority"])
    suggestions = suggestions[:max_suggestions]

    return {
        "row_count": n_rows,
        "column_count": n_cols,
        "numeric_columns": num,
        "categorical_columns": cat,
        "datetime_columns": dt,
        "suggestions": suggestions,
    }
