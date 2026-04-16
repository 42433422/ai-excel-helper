"""
Workflow tool registry and execution.

excel_analysis supports read | query | aggregate | statistics | excel_query (NL→pandas).
excel_schema_understand: LLM summary + data dictionary for an uploaded Excel.
Paths are resolved only under a configurable workspace root.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from backend.chart_recommendation import recommend_charts
from backend.excel_join_diff import diff_frames, join_frames
from backend.excel_prophet_ops import run_prophet_anomalies, run_prophet_forecast
from backend.excel_schema_understanding_service import ExcelSchemaUnderstandingService
from backend.excel_text_to_pandas import run_natural_language_pandas
from backend.price_list_docx_export import build_price_list_docx_bytes

# Cap rows returned to the LLM to avoid context blow-up
_DEFAULT_MAX_OUTPUT_ROWS = 500
_VECTOR_SERVICES: dict[str, Any] = {}


def _default_workspace_root() -> str:
    return os.environ.get("WORKSPACE_ROOT", os.getcwd())


def flatten_tool_result_dict_for_client(raw: dict[str, Any]) -> dict[str, Any]:
    """
    将 Planner 最近一次工具结果扁平化进聊天 ``data``：除标量外，允许 JSON 可序列化的 list/dict
    （如 ``products``、``data``），避免前端只能看到模型原始 arguments。
    """
    out: dict[str, Any] = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        if isinstance(v, (str, int, float, bool, type(None))):
            out[k] = v
        elif isinstance(v, (list, dict)):
            try:
                s = json.dumps(v, ensure_ascii=False, default=str)
                if len(s) > 200_000:
                    continue
                out[k] = json.loads(s)
            except (TypeError, ValueError):
                continue
    return out


def _get_vector_service(workspace_root: str) -> Any:
    """
    Lazily initialize a persisted vector service per workspace root.
    Uses lazy import to avoid circular import at module import time.
    """
    root = str(Path(workspace_root).resolve())
    svc = _VECTOR_SERVICES.get(root)
    if svc is not None:
        return svc

    from backend.persistence_integration import create_persisted_service

    svc = create_persisted_service(
        workspace_root=root,
        use_cache=True,
        auto_save=True,
    )
    _VECTOR_SERVICES[root] = svc
    return svc


def resolve_safe_excel_path(workspace_root: str, file_path: str) -> Path:
    """
    Resolve file_path to an absolute path that must stay under workspace_root.
    Rejects '..' segments and paths that escape the root after resolution.
    """
    root = Path(workspace_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"workspace root is not a directory: {root}")

    raw = Path(file_path)
    if raw.is_absolute():
        candidate = raw.resolve()
    else:
        candidate = (root / raw).resolve()

    try:
        candidate.relative_to(root)
    except ValueError as e:
        raise PermissionError("file_path must resolve inside workspace root") from e

    if ".." in Path(file_path).parts:
        raise PermissionError("file_path must not contain '..'")

    if candidate.suffix.lower() not in (".xlsx", ".xlsm", ".xls"):
        raise ValueError("only Excel files (.xlsx, .xlsm, .xls) are supported")

    return candidate


def _excel_sheet_names(path: Path) -> list[str]:
    xl = pd.ExcelFile(path, engine="openpyxl")
    try:
        return list(xl.sheet_names)
    finally:
        xl.close()


def _coerce_sheet_argument(path: Path, sheet: Any) -> tuple[Any, list[str], str | None]:
    """
    Normalize sheet arg for pandas.read_excel(sheet_name=...).

    与 XCAGI 前端 ``sheet_index`` 约定一致：**1..n 为 Excel 左下角「第几张表」**（1 起算）；
    **0 表示第一张表**（与 pandas 下标 0 对齐）。字符串仍按工作表名称匹配。
    """
    names = _excel_sheet_names(path)
    n = len(names)
    if n == 0:
        raise ValueError("workbook has no sheets")
    note: str | None = None
    if sheet is None or sheet == "":
        return 0, names, None
    if isinstance(sheet, str):
        s = sheet.strip()
        if not s:
            return 0, names, None
        if s in names:
            return s, names, None
        for nm in names:
            if nm.strip() == s:
                return nm, names, None
        if s.isdigit():
            i = int(s)
            if i == 0:
                return 0, names, None
            if 1 <= i <= n:
                return i - 1, names, "sheet index interpreted as 1-based (Excel sheet number)"
        raise ValueError(
            f"Unknown sheet_name={sheet!r}. Available ({n}): {names!r}"
        )
    if isinstance(sheet, (int, float)) and not isinstance(sheet, bool):
        i = int(sheet)
        if i == 0:
            return 0, names, None
        if 1 <= i <= n:
            if i != 1:
                note = "sheet index interpreted as 1-based (Excel sheet number)"
            return i - 1, names, note
        raise ValueError(
            f"sheet index {i} out of range for workbook with {n} sheet(s). "
            f"Use 1..{n} (Excel sheet number) or 0 for the first sheet. Available: {names!r}"
        )
    raise ValueError(f"Unsupported sheet_name type: {type(sheet).__name__}")


def _load_sheet(
    path: Path,
    sheet_name: str | int | None,
    header_row: int,
) -> tuple[pd.DataFrame, str | None]:
    resolved, _names, warn = _coerce_sheet_argument(path, sheet_name)
    kwargs: dict[str, Any] = {"engine": "openpyxl", "header": header_row, "sheet_name": resolved}
    df = pd.read_excel(path, **kwargs)
    return df, warn


def _df_slice_range(
    df: pd.DataFrame,
    cell_range: str | None,
    header_row: int,
) -> pd.DataFrame:
    """Slice DataFrame by Excel range (1-based rows/cols). Rows map after header_row in the file."""
    if not cell_range:
        return df
    try:
        from openpyxl.utils import range_boundaries
    except ImportError as e:
        raise RuntimeError("openpyxl is required for range slicing") from e

    min_col, min_row, max_col, max_row = range_boundaries(cell_range)
    file_first_0based = min_row - 1
    file_last_0based = max_row - 1
    df_start = file_first_0based - (header_row + 1)
    df_end_inclusive = file_last_0based - (header_row + 1)
    df_start = max(df_start, 0)
    if df_start >= len(df):
        return df.iloc[0:0]
    df_end_exclusive = min(df_end_inclusive + 1, len(df))
    col_start = min_col - 1
    col_end = max_col
    return df.iloc[df_start:df_end_exclusive, col_start:col_end]


def _sanitize_records(df: pd.DataFrame, max_rows: int) -> dict[str, Any]:
    """Convert DataFrame to JSON-safe records with truncation."""
    total = len(df)
    head = df.head(max_rows)
    records = json.loads(
        head.replace({np.nan: None}).to_json(orient="records", date_format="iso")
    )
    return {
        "row_count": total,
        "truncated": total > max_rows,
        "returned_rows": len(head),
        "columns": list(df.columns.astype(str)),
        "records": records,
    }


def _merge_sheet_resolution_note(payload: dict[str, Any], warn: str | None) -> dict[str, Any]:
    if warn:
        return {**payload, "sheet_resolution_note": warn}
    return payload


def _excel_args_sheet_alias(arguments: Mapping[str, Any]) -> dict[str, Any]:
    """兼容 LLM / 前端传入的 sheet_index（与 sheet_name 二选一）。"""
    out = dict(arguments)
    if out.get("sheet_name") is None and out.get("sheet_index") is not None:
        out["sheet_name"] = out.get("sheet_index")
    return out


def _action_read(args: Mapping[str, Any], path: Path) -> dict[str, Any]:
    sheet = args.get("sheet_name")
    header_row = int(args.get("header_row", 0))
    max_out = int(args.get("max_rows", _DEFAULT_MAX_OUTPUT_ROWS))
    columns = args.get("columns")
    cell_range = args.get("range")

    df, s_note = _load_sheet(path, sheet, header_row)
    df = _df_slice_range(df, cell_range, header_row)
    if columns:
        cols = [c for c in columns if c in df.columns]
        missing = [c for c in columns if c not in df.columns]
        if missing:
            return {"error": "unknown_columns", "missing": missing, "available": list(map(str, df.columns))}
        df = df[cols]
    return _merge_sheet_resolution_note({"action": "read", **_sanitize_records(df, max_out)}, s_note)


def _action_query(args: Mapping[str, Any], path: Path) -> dict[str, Any]:
    """Filter rows using pandas.DataFrame.query(expr). Column names must be valid identifiers."""
    sheet = args.get("sheet_name")
    header_row = int(args.get("header_row", 0))
    max_out = int(args.get("max_rows", _DEFAULT_MAX_OUTPUT_ROWS))
    expr = args.get("query_expression") or args.get("expr")
    if not expr or not isinstance(expr, str):
        return {"error": "missing_query_expression", "hint": "Provide query_expression (pandas query syntax)."}

    df, s_note = _load_sheet(path, sheet, header_row)
    try:
        filtered = df.query(expr, engine="python")
    except Exception as e:
        return {"error": "query_failed", "message": str(e), "columns": list(map(str, df.columns))}

    return _merge_sheet_resolution_note(
        {"action": "query", "query_expression": expr, **_sanitize_records(filtered, max_out)},
        s_note,
    )


def _action_excel_query(args: Mapping[str, Any], path: Path) -> dict[str, Any]:
    """
    Natural language → LLM-generated pandas code → restricted execution (result variable).
    """
    sheet = args.get("sheet_name")
    header_row = int(args.get("header_row", 0))
    nl = args.get("natural_language") or args.get("question")
    if not nl or not isinstance(nl, str):
        return {
            "error": "missing_natural_language",
            "hint": "Provide natural_language (or question) describing the query in plain language.",
        }

    df, s_note = _load_sheet(path, sheet, header_row)
    out = run_natural_language_pandas(df, nl.strip())
    if "error" in out:
        return _merge_sheet_resolution_note({"action": "excel_query", "natural_language": nl, **out}, s_note)
    out["action"] = "excel_query"
    out["natural_language"] = nl
    return _merge_sheet_resolution_note(out, s_note)


def _action_aggregate(args: Mapping[str, Any], path: Path) -> dict[str, Any]:
    """
    metrics: list of {"column": str, "op": "sum"|"mean"|"count"|"min"|"max"|"nunique"}
    """
    sheet = args.get("sheet_name")
    header_row = int(args.get("header_row", 0))
    group_by = args.get("group_by") or []
    metrics = args.get("metrics") or []

    if not group_by:
        return {"error": "missing_group_by", "hint": "Provide group_by: list of column names."}
    if not metrics:
        return {"error": "missing_metrics", "hint": "Provide metrics: list of {column, op}."}

    df, s_note = _load_sheet(path, sheet, header_row)
    missing_g = [c for c in group_by if c not in df.columns]
    if missing_g:
        return {"error": "unknown_group_by_columns", "missing": missing_g}

    agg_map: dict[str, list[str]] = {}
    for m in metrics:
        if not isinstance(m, dict):
            continue
        col = m.get("column")
        op = (m.get("op") or "").lower()
        if col not in df.columns:
            return {"error": "unknown_metric_column", "column": col}
        if op not in ("sum", "mean", "count", "min", "max", "nunique"):
            return {"error": "invalid_op", "op": op, "allowed": ["sum", "mean", "count", "min", "max", "nunique"]}
        agg_map.setdefault(col, []).append(op)

    if not agg_map:
        return {"error": "no_valid_metrics"}

    try:
        g = df.groupby(group_by, dropna=False)
        series_list: list[pd.Series] = []
        used: set[str] = set()
        for m in metrics:
            if not isinstance(m, dict):
                continue
            col = m.get("column")
            op = (m.get("op") or "").lower()
            base = f"{col}_{op}"
            name = base
            n = 2
            while name in used:
                name = f"{base}_{n}"
                n += 1
            used.add(name)
            if op == "nunique":
                s = g[col].nunique()
            elif op == "count":
                s = g[col].count()
            else:
                s = getattr(g[col], op)()
            s = s.rename(name)
            series_list.append(s)
        if not series_list:
            return {"error": "no_valid_metrics"}
        out = pd.concat(series_list, axis=1)
        out = out.reset_index()
    except Exception as e:
        return {"error": "aggregate_failed", "message": str(e)}

    return _merge_sheet_resolution_note(
        {"action": "aggregate", **_sanitize_records(out, _DEFAULT_MAX_OUTPUT_ROWS)},
        s_note,
    )


def _action_statistics(args: Mapping[str, Any], path: Path) -> dict[str, Any]:
    sheet = args.get("sheet_name")
    header_row = int(args.get("header_row", 0))
    columns = args.get("columns")

    df, s_note = _load_sheet(path, sheet, header_row)
    if columns:
        miss = [c for c in columns if c not in df.columns]
        if miss:
            return {"error": "unknown_columns", "missing": miss}
        df = df[columns]

    try:
        desc = df.describe(include="all", datetime_is_numeric=True)
    except TypeError:
        desc = df.describe(include="all")
    desc_dict = json.loads(desc.replace({np.nan: None}).to_json(date_format="iso"))
    null_counts = {str(k): int(v) for k, v in df.isnull().sum().items()}
    dtypes = {str(c): str(t) for c, t in df.dtypes.items()}

    return _merge_sheet_resolution_note(
        {
            "action": "statistics",
            "row_count": len(df),
            "column_count": len(df.columns),
            "describe": desc_dict,
            "null_counts": null_counts,
            "dtypes": dtypes,
        },
        s_note,
    )


def handle_excel_analysis(
    arguments: Mapping[str, Any],
    workspace_root: str | None = None,
) -> dict[str, Any]:
    root = workspace_root or _default_workspace_root()
    action = (arguments.get("action") or "").lower()
    file_path = arguments.get("file_path")
    if not file_path:
        return {"error": "missing_file_path"}

    try:
        path = resolve_safe_excel_path(root, str(file_path))
    except (OSError, ValueError, PermissionError) as e:
        return {"error": "path_resolution_failed", "message": str(e)}

    if not path.is_file():
        return {"error": "file_not_found", "path": str(path)}

    args = _excel_args_sheet_alias(arguments)
    try:
        if action == "read":
            return _action_read(args, path)
        if action == "query":
            return _action_query(args, path)
        if action == "excel_query":
            return _action_excel_query(args, path)
        if action == "aggregate":
            return _action_aggregate(args, path)
        if action == "statistics":
            return _action_statistics(args, path)
    except ValueError as e:
        msg = str(e)
        if "sheet" in msg.lower() or "unknown sheet" in msg.lower() or "workbook has no sheets" in msg.lower():
            try:
                avail = _excel_sheet_names(path)
            except Exception:
                avail = []
            return {
                "error": "invalid_sheet",
                "message": msg,
                "sheet_name": args.get("sheet_name"),
                "sheet_index": args.get("sheet_index"),
                "available_sheets": avail,
            }
        raise
    return {
        "error": "invalid_action",
        "action": action,
        "allowed": ["read", "query", "excel_query", "aggregate", "statistics"],
    }


def handle_excel_schema_understand(
    arguments: Mapping[str, Any],
    workspace_root: str | None = None,
) -> dict[str, Any]:
    """Load Excel under workspace and ask LLM for table summary + data dictionary + semantics."""
    root = workspace_root or _default_workspace_root()
    file_path = arguments.get("file_path")
    if not file_path:
        return {"error": "missing_file_path"}
    try:
        path = resolve_safe_excel_path(root, str(file_path))
    except (OSError, ValueError, PermissionError) as e:
        return {"error": "path_resolution_failed", "message": str(e)}
    if not path.is_file():
        return {"error": "file_not_found", "path": str(path)}

    args = _excel_args_sheet_alias(arguments)
    sheet = args.get("sheet_name")
    header_row = int(args.get("header_row", 0))
    try:
        df, s_note = _load_sheet(path, sheet, header_row)
    except ValueError as e:
        msg = str(e)
        try:
            avail = _excel_sheet_names(path)
        except Exception:
            avail = []
        return {
            "error": "invalid_sheet",
            "message": msg,
            "sheet_name": sheet,
            "available_sheets": avail,
        }
    try:
        svc = ExcelSchemaUnderstandingService()
        out = svc.understand_dataframe(df, file_path=str(file_path), sheet_name=sheet)
        if not isinstance(out, dict):
            out = {"result": out}
        return _merge_sheet_resolution_note(out, s_note)
    except Exception as e:
        return {"error": "schema_understand_failed", "message": str(e)}


def handle_excel_vector_index(
    arguments: Mapping[str, Any],
    workspace_root: str | None = None,
) -> dict[str, Any]:
    """Build vector index for an Excel file under workspace root."""
    root = workspace_root or _default_workspace_root()
    file_path = arguments.get("file_path")
    if not file_path:
        return {"error": "missing_file_path"}

    try:
        safe_path = resolve_safe_excel_path(root, str(file_path))
    except (OSError, ValueError, PermissionError) as e:
        return {"error": "path_resolution_failed", "message": str(e)}
    if not safe_path.is_file():
        return {"error": "file_not_found", "path": str(safe_path)}

    rel_path = Path(os.path.relpath(safe_path, Path(root).resolve())).as_posix()
    sheet_name = arguments.get("sheet_name")
    columns = arguments.get("columns")
    header_row = int(arguments.get("header_row", 0))
    max_rows = arguments.get("max_rows")
    max_rows_int = int(max_rows) if max_rows is not None else None
    force_rebuild = bool(arguments.get("force_rebuild", False))

    try:
        svc = _get_vector_service(root)
        result = svc.index_excel(
            rel_path,
            sheet_name=sheet_name,
            columns=columns,
            header_row=header_row,
            max_rows=max_rows_int,
            force_rebuild=force_rebuild,
        )
        stats = svc.get_index_stats() if hasattr(svc, "get_index_stats") else {"chunk_count": getattr(svc, "chunk_count", 0)}
        return {"action": "vector_index", **result, "index_stats": stats}
    except Exception as e:
        return {"error": "vector_index_failed", "message": str(e), "file_path": rel_path}


def handle_excel_vector_search(
    arguments: Mapping[str, Any],
    workspace_root: str | None = None,
) -> dict[str, Any]:
    """Search over the current vector index."""
    root = workspace_root or _default_workspace_root()
    query = str(arguments.get("query") or arguments.get("question") or "").strip()
    if not query:
        return {"error": "missing_query", "hint": "Provide query or question."}

    top_k = int(arguments.get("top_k", 5))
    top_k = max(1, min(top_k, 50))
    file_path = arguments.get("file_path")

    try:
        svc = _get_vector_service(root)
        results = svc.search(query, top_k=top_k)
        if file_path:
            expected = Path(str(file_path)).as_posix()
            filtered = [r for r in results if str((r.get("meta") or {}).get("file_path", "")).replace("\\", "/") == expected]
            results = filtered
        return {
            "action": "vector_search",
            "query": query,
            "top_k": top_k,
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        return {"error": "vector_search_failed", "message": str(e)}


def handle_excel_prophet(
    arguments: Mapping[str, Any],
    workspace_root: str | None = None,
) -> dict[str, Any]:
    """Prophet：forecast 未来若干期；anomalies 基于拟合残差阈值。"""
    root = workspace_root or _default_workspace_root()
    action = (arguments.get("action") or "forecast").lower()
    file_path = arguments.get("file_path")
    date_col = arguments.get("date_column")
    y_col = arguments.get("value_column")
    if not file_path or not date_col or not y_col:
        return {"error": "missing_fields", "need": ["file_path", "date_column", "value_column"]}
    try:
        path = resolve_safe_excel_path(root, str(file_path))
    except (OSError, ValueError, PermissionError) as e:
        return {"error": "path_resolution_failed", "message": str(e)}
    if not path.is_file():
        return {"error": "file_not_found", "path": str(path)}

    args = _excel_args_sheet_alias(arguments)
    sheet = args.get("sheet_name")
    header_row = int(args.get("header_row", 0))
    try:
        df, s_note = _load_sheet(path, sheet, header_row)
    except ValueError as e:
        try:
            avail = _excel_sheet_names(path)
        except Exception:
            avail = []
        return {
            "error": "invalid_sheet",
            "message": str(e),
            "sheet_name": sheet,
            "available_sheets": avail,
        }

    if action == "forecast":
        periods = int(arguments.get("periods", arguments.get("forecast_periods", 14)))
        freq = arguments.get("freq") or arguments.get("frequency")
        if isinstance(freq, str) and not freq.strip():
            freq = None
        out = run_prophet_forecast(df, str(date_col), str(y_col), periods, freq=freq)
        merged = out if "error" in out else {**out, "file_path": file_path}
        return _merge_sheet_resolution_note(merged, s_note)
    if action == "anomalies":
        sigma = float(arguments.get("sigma", arguments.get("anomaly_sigma", 3.0)))
        out = run_prophet_anomalies(df, str(date_col), str(y_col), sigma=sigma)
        merged = out if "error" in out else {**out, "file_path": file_path}
        return _merge_sheet_resolution_note(merged, s_note)
    return {"error": "invalid_action", "allowed": ["forecast", "anomalies"]}


def handle_excel_chart_recommend(
    arguments: Mapping[str, Any],
    workspace_root: str | None = None,
) -> dict[str, Any]:
    root = workspace_root or _default_workspace_root()
    file_path = arguments.get("file_path")
    if not file_path:
        return {"error": "missing_file_path"}
    try:
        path = resolve_safe_excel_path(root, str(file_path))
    except (OSError, ValueError, PermissionError) as e:
        return {"error": "path_resolution_failed", "message": str(e)}
    if not path.is_file():
        return {"error": "file_not_found", "path": str(path)}
    args = _excel_args_sheet_alias(arguments)
    sheet = args.get("sheet_name")
    header_row = int(args.get("header_row", 0))
    try:
        df, s_note = _load_sheet(path, sheet, header_row)
    except ValueError as e:
        try:
            avail = _excel_sheet_names(path)
        except Exception:
            avail = []
        return {
            "error": "invalid_sheet",
            "message": str(e),
            "sheet_name": sheet,
            "available_sheets": avail,
        }
    n = int(arguments.get("max_suggestions", 6))
    out = recommend_charts(df, max_suggestions=max(1, min(n, 12)))
    out["file_path"] = file_path
    return _merge_sheet_resolution_note(out, s_note)


def handle_excel_join_compare(
    arguments: Mapping[str, Any],
    workspace_root: str | None = None,
) -> dict[str, Any]:
    root = workspace_root or _default_workspace_root()
    action = (arguments.get("action") or "join").lower()

    if action == "join":
        paths = arguments.get("file_paths") or arguments.get("paths")
        if not paths or not isinstance(paths, list) or len(paths) < 2:
            return {"error": "need_file_paths_list", "min": 2}
        keys = arguments.get("join_keys") or arguments.get("on")
        if not keys or not isinstance(keys, list):
            return {"error": "need_join_keys"}
        how = str(arguments.get("how", "inner"))
        args_join = _excel_args_sheet_alias(arguments)
        sheet = args_join.get("sheet_name")
        header_row = int(args_join.get("header_row", 0))
        frames: list[pd.DataFrame] = []
        for fp in paths:
            try:
                p = resolve_safe_excel_path(root, str(fp))
            except (OSError, ValueError, PermissionError) as e:
                return {"error": "path_resolution_failed", "file": fp, "message": str(e)}
            if not p.is_file():
                return {"error": "file_not_found", "path": str(p)}
            try:
                fr, _ = _load_sheet(p, sheet, header_row)
            except ValueError as e:
                try:
                    avail = _excel_sheet_names(p)
                except Exception:
                    avail = []
                return {
                    "error": "invalid_sheet",
                    "message": str(e),
                    "file": fp,
                    "sheet_name": sheet,
                    "available_sheets": avail,
                }
            frames.append(fr)
        out = join_frames(frames, [str(k) for k in keys], how=how)
        return out

    if action == "diff":
        a = arguments.get("file_path_a") or arguments.get("left_file")
        b = arguments.get("file_path_b") or arguments.get("right_file")
        keys = arguments.get("key_columns") or arguments.get("join_keys")
        if not a or not b:
            return {"error": "need_file_path_a_and_b"}
        if not keys or not isinstance(keys, list):
            return {"error": "need_key_columns"}
        merged = _excel_args_sheet_alias(arguments)
        sheet_a = arguments.get("sheet_name_a")
        if sheet_a is None and arguments.get("sheet_index_a") is not None:
            sheet_a = arguments.get("sheet_index_a")
        if sheet_a is None:
            sheet_a = merged.get("sheet_name")
        sheet_b = arguments.get("sheet_name_b")
        if sheet_b is None and arguments.get("sheet_index_b") is not None:
            sheet_b = arguments.get("sheet_index_b")
        if sheet_b is None:
            sheet_b = merged.get("sheet_name")
        header_a = int(arguments.get("header_row_a", arguments.get("header_row", 0)))
        header_b = int(arguments.get("header_row_b", arguments.get("header_row", 0)))
        try:
            pa = resolve_safe_excel_path(root, str(a))
            pb = resolve_safe_excel_path(root, str(b))
        except (OSError, ValueError, PermissionError) as e:
            return {"error": "path_resolution_failed", "message": str(e)}
        if not pa.is_file() or not pb.is_file():
            return {"error": "file_not_found"}
        try:
            dfa, _ = _load_sheet(pa, sheet_a, header_a)
            dfb, _ = _load_sheet(pb, sheet_b, header_b)
        except ValueError as e:
            try:
                avail_a = _excel_sheet_names(pa)
                avail_b = _excel_sheet_names(pb)
            except Exception:
                avail_a, avail_b = [], []
            return {
                "error": "invalid_sheet",
                "message": str(e),
                "sheet_name_a": sheet_a,
                "sheet_name_b": sheet_b,
                "available_sheets_a": avail_a,
                "available_sheets_b": avail_b,
            }
        compare_cols = arguments.get("compare_columns")
        if compare_cols is not None and not isinstance(compare_cols, list):
            compare_cols = None
        out = diff_frames(dfa, dfb, [str(k) for k in keys], compare_columns=compare_cols)
        out["file_path_a"] = a
        out["file_path_b"] = b
        return out

    return {"error": "invalid_action", "allowed": ["join", "diff"]}


def handle_sales_contract_export(arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Planner：生成销售合同 **Excel（.xlsx）**（与 ``/api/sales-contract/generate`` 同源；选 Word 模板时自动改用送货单版式）。"""
    from fastapi import HTTPException

    from backend.routers.sales_contract import SalesContractGenerateRequest, SalesContractProduct
    from backend.sales_contract_generate_core import run_sales_contract_generation

    raw_products = arguments.get("products") or []
    products: list[SalesContractProduct] = []
    for p in raw_products:
        if not isinstance(p, dict):
            continue
        products.append(
            SalesContractProduct(
                model_number=str(p.get("model_number") or ""),
                name=str(p.get("name") or ""),
                spec=str(p.get("spec") or p.get("specification") or ""),
                unit=str(p.get("unit") or ""),
                quantity=str(p.get("quantity") or "1"),
                unit_price=str(p.get("unit_price") or "0"),
                amount=str(p.get("amount") or "0"),
            )
        )
    if not products:
        return {"error": "missing_products", "message": "products 不能为空"}

    req = SalesContractGenerateRequest(
        customer_name=str(arguments.get("customer_name") or "").strip(),
        customer_phone=str(arguments.get("customer_phone") or ""),
        contract_date=str(arguments.get("contract_date") or ""),
        products=products,
        return_buckets_expected=int(arguments.get("return_buckets_expected") or 0),
        return_buckets_actual=int(arguments.get("return_buckets_actual") or 0),
        template_id=(arguments.get("template_id") or arguments.get("template_slug")),
    )
    try:
        out = run_sales_contract_generation(req)
    except HTTPException as he:
        d = he.detail if isinstance(he.detail, str) else str(he.detail)
        return {"success": False, "error": d, "message": d}
    except Exception as e:
        return {"success": False, "error": str(e), "message": "销售合同生成失败"}

    if not out.get("success"):
        return out
    data = out.get("data") or {}
    if isinstance(data, dict):
        cn = str(data.get("customer_name") or "").strip()
        if cn:
            out["customer_name"] = cn
    fp = data.get("file_path")
    if fp:
        try:
            rel = Path(fp).resolve().relative_to(Path.cwd().resolve())
            url_path = rel.as_posix()
        except Exception:
            url_path = str(fp)
        dl = f"/api/sales-contract/download?filepath={fp}"
        out["download_url"] = dl
        out["file_path"] = url_path if url_path else fp
        if isinstance(data, dict):
            data = dict(data)
            data["download_url"] = dl
            out["data"] = data
    return out


def handle_price_list_export(
    arguments: Mapping[str, Any],
    workspace_root: str | None = None,
) -> dict[str, Any]:
    """
    生成 Word 价格表文件。
    流程：1) 从数据库加载产品列表 2) 按客户名称过滤 3) 生成 Word 文件
    """
    import tempfile
    from backend.price_list_docx_export import resolve_price_list_docx_template

    customer_name = arguments.get("customer_name") or arguments.get("unit") or arguments.get("客户名称")
    if not customer_name:
        return {"error": "missing_customer_name", "message": "需要提供 customer_name 参数"}

    template_slug = arguments.get("template_id") or arguments.get("template_slug")
    ts = str(template_slug).strip() if template_slug not in (None, "") else None
    template_path = resolve_price_list_docx_template(ts)
    if not template_path:
        return {
            "error": "template_not_found",
            "message": "未找到价格表模板。请放置 424/document_templates/price_list_default.docx 或通过模板库登记，或设置 FHD_PRICE_LIST_DOCX_TEMPLATE",
        }

    keyword = arguments.get("keyword") or arguments.get("产品关键词")
    export_date = arguments.get("export_date") or arguments.get("quote_date")

    products = _load_products_for_price_list(customer_name, keyword)
    if not products:
        return {
            "error": "no_products_found",
            "message": f"未找到客户「{customer_name}」的产品",
        }

    try:
        docx_bytes = build_price_list_docx_bytes(
            template_path,
            customer_name=customer_name,
            quote_date=export_date,
            products=products,
        )
    except Exception as e:
        return {"error": "docx_generation_failed", "message": str(e)}

    root = workspace_root or _default_workspace_root()
    upload_dir = Path(root) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"价格表_{customer_name}_{export_date or ''}.docx"
    output_path = upload_dir / output_filename
    output_path.write_bytes(docx_bytes)

    try:
        rel = output_path.relative_to(Path(root).resolve())
        file_path = rel.as_posix()
    except ValueError:
        file_path = str(output_path)

    return {
        "success": True,
        "message": f"已生成客户「{customer_name}」的价格表，包含 {len(products)} 个产品",
        "data": {
            "file_path": file_path,
            "download_url": f"/api/word/download?path={file_path}",
            "product_count": len(products),
            "filename": f"价格表_{customer_name}_{export_date or ''}.docx",
        },
        "file_path": file_path,
        "download_url": f"/api/word/download?path={file_path}",
        "product_count": len(products),
    }


def _load_products_for_price_list(customer_name: str, keyword: str | None = None) -> list[dict[str, Any]]:
    """从数据库加载价格表产品（按客户名称过滤）"""
    from backend.product_db_read import load_products_for_price_list_by_customer

    return load_products_for_price_list_by_customer(customer_name, keyword)


def _products_bulk_import_tool_def() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "products_bulk_import",
            "description": (
                "【授权数据库写入】将报价产品行写入 PostgreSQL：按购买单位写入/更新 products，必要时创建 purchase_units。"
                "仅在用户在 HTTP 请求 JSON 中传入 db_write_token（与服务器环境变量 FHD_DB_WRITE_TOKEN 一致）时才能成功。"
                "参数 customer_name 为购买单位；items 为 {model_number?, name, specification?, price}；"
                "replace=true 会先删除该单位下全部产品再插入；dry_run=true 仅统计不写库。"
                "supplier_name、quote_date 会写入 description/brand（视表结构）。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "客户/购买单位名称（写入 products.unit）",
                    },
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "model_number": {"type": "string"},
                                "name": {"type": "string"},
                                "specification": {"type": "string"},
                                "price": {"type": "number"},
                            },
                            "required": ["name"],
                        },
                    },
                    "replace": {
                        "type": "boolean",
                        "description": "为 true 时删除该单位下旧产品后全量插入",
                    },
                    "dry_run": {"type": "boolean"},
                    "supplier_name": {"type": "string"},
                    "quote_date": {"type": "string"},
                },
                "required": ["customer_name", "items"],
            },
        },
    }


def get_excel_tool_registry() -> list[dict[str, Any]]:
    """
    Excel 工具集（OpenAI Chat Completions 的 `tools` 列表）。

    必须以 `excel_analysis` 为主入口：通过 `action` 在单表上完成读数、表达式过滤、
    自然语言转 pandas、分组聚合与描述统计。其余条目为 Schema 理解、Prophet、图表推荐、多表 Join/Diff。
    """
    tools: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "excel_analysis",
                "description": (
                    "【Excel 核心工具】在 workspace 内分析单个 Excel：必选 action + file_path。"
                    "read=预览行；query=pandas query 表达式过滤；excel_query=自然语言问数（内部生成 pandas）；"
                    "aggregate=分组聚合；statistics=describe/缺失/类型。路径须相对 WORKSPACE_ROOT。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["read", "query", "excel_query", "aggregate", "statistics"],
                            "description": (
                                "read: load rows; query: pandas query_expression; excel_query: natural_language→pandas; "
                                "aggregate: group_by + metrics; statistics: describe/nulls/dtypes"
                            ),
                        },
                        "file_path": {"type": "string", "description": "Path to .xlsx/.xlsm/.xls under workspace"},
                        "sheet_index": {
                            "type": "integer",
                            "description": "与 sheet_name 二选一；整数表号 1..n（Excel 第几张表），同 sheet_name 为整数时的语义",
                        },
                        "sheet_name": {
                            "oneOf": [
                                {"type": "string"},
                                {"type": "integer"},
                            ],
                            "description": "工作表名称；或整数表号：1..n 与 Excel 左下角一致（第 1 张表传 1），0 表示第一张表",
                        },
                        "header_row": {"type": "integer", "description": "Row index (0-based) for column headers", "default": 0},
                        "max_rows": {
                            "type": "integer",
                            "description": "Max rows to return for read/query/aggregate (default 500)",
                        },
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "For read/statistics: subset of columns",
                        },
                        "range": {
                            "type": "string",
                            "description": "Optional cell range like A1:D100 applied to loaded DataFrame by position",
                        },
                        "query_expression": {
                            "type": "string",
                            "description": "For action=query: pandas.DataFrame.query expression (engine=python)",
                        },
                        "natural_language": {
                            "type": "string",
                            "description": "For action=excel_query: question in natural language (e.g. 销量最高的产品)",
                        },
                        "question": {
                            "type": "string",
                            "description": "Alias for natural_language when action=excel_query",
                        },
                        "group_by": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "For action=aggregate: grouping columns",
                        },
                        "metrics": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "column": {"type": "string"},
                                    "op": {
                                        "type": "string",
                                        "enum": ["sum", "mean", "count", "min", "max", "nunique"],
                                    },
                                },
                                "required": ["column", "op"],
                            },
                            "description": "For action=aggregate: metrics to compute per group",
                        },
                    },
                    "required": ["action", "file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "excel_schema_understand",
                "description": (
                    "After upload, infer what the spreadsheet is: Chinese summary, data dictionary, "
                    "and semantic tags per column. Uses LLM; file_path must be under workspace root."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {
                            "oneOf": [{"type": "string"}, {"type": "integer"}],
                            "description": "Sheet name or index; default first sheet",
                        },
                        "header_row": {"type": "integer", "default": 0},
                    },
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "excel_vector_index",
                "description": (
                    "为 Excel 建立向量索引，供后续语义检索使用。"
                    "支持按 sheet/列限制索引范围，索引会自动持久化。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Excel 路径（相对 WORKSPACE_ROOT）"},
                        "sheet_name": {"oneOf": [{"type": "string"}, {"type": "integer"}]},
                        "columns": {"type": "array", "items": {"type": "string"}},
                        "header_row": {"type": "integer", "default": 0},
                        "max_rows": {"type": "integer"},
                        "force_rebuild": {"type": "boolean", "default": False},
                    },
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "excel_vector_search",
                "description": (
                    "在已有向量索引中做语义检索。"
                    "可选 file_path 过滤特定文件结果。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "检索问题，例如：金额合计是多少"},
                        "question": {"type": "string", "description": "query 别名"},
                        "top_k": {"type": "integer", "default": 5},
                        "file_path": {"type": "string", "description": "可选，仅返回该文件结果"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "excel_prophet",
                "description": (
                    "时间序列：用 Prophet 做趋势预测（forecast）或基于拟合残差的异常检测（anomalies）。"
                    "需提供日期列与数值列名。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["forecast", "anomalies"]},
                        "file_path": {"type": "string"},
                        "date_column": {"type": "string"},
                        "value_column": {"type": "string"},
                        "sheet_name": {"oneOf": [{"type": "string"}, {"type": "integer"}]},
                        "header_row": {"type": "integer", "default": 0},
                        "periods": {
                            "type": "integer",
                            "description": "forecast：向前预测期数",
                            "default": 14,
                        },
                        "freq": {"type": "string", "description": "可选，如 D/H/W-MON，传给 Prophet future 频率"},
                        "sigma": {
                            "type": "number",
                            "description": "anomalies：残差阈值倍数（均值+sigma*std）",
                            "default": 3,
                        },
                    },
                    "required": ["action", "file_path", "date_column", "value_column"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "excel_chart_recommend",
                "description": (
                    "根据表格列类型与基数，自动推荐合适图表类型（折线/柱/散点/热力等）及字段映射建议。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"oneOf": [{"type": "string"}, {"type": "integer"}]},
                        "header_row": {"type": "integer", "default": 0},
                        "max_suggestions": {"type": "integer", "default": 6},
                    },
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "excel_join_compare",
                "description": (
                    "多文件：join 将多个 Excel 按相同主键连接；diff 对比两表在主键上的增删与字段值变化。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["join", "diff"]},
                        "file_paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "join：至少两个相对 workspace 的路径",
                        },
                        "file_path_a": {"type": "string", "description": "diff：左侧文件"},
                        "file_path_b": {"type": "string", "description": "diff：右侧文件"},
                        "join_keys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "join 时的键（各表列名一致）",
                        },
                        "key_columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "diff 时的主键列",
                        },
                        "how": {
                            "type": "string",
                            "enum": ["inner", "left", "right", "outer"],
                            "default": "inner",
                        },
                        "sheet_name": {"description": "join/diff 共用的表名或索引"},
                        "sheet_name_a": {},
                        "sheet_name_b": {},
                        "header_row": {"type": "integer", "default": 0},
                        "compare_columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "diff：仅比较这些重叠列；默认所有非键重叠列",
                        },
                    },
                    "required": ["action"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "price_list_export",
                "description": (
                    "【价格表导出工具】生成 Word 格式的价格表/报价单："
                    "根据客户名称从数据库加载产品列表，填充到 Word 模板后生成可下载的 .docx 文件。"
                    "适用于用户说「打印XXX公司的价格单」「导出报价单」「生成客户报价表」等场景。"
                    "可选参数 template_id / template_slug 必须为 "
                    "``GET /api/document-templates?role=price_list_docx`` 返回行中的 ``slug``（与前端 template_id 一致）。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {
                            "type": "string",
                            "description": "客户/购买单位名称，如「深圳市百木鼎家具有限公司」",
                        },
                        "template_id": {
                            "type": "string",
                            "description": (
                                "可选；价格表 Word 模板 slug，须来自 "
                                "``GET /api/document-templates?role=price_list_docx`` 的 ``slug`` 字段"
                            ),
                        },
                        "template_slug": {
                            "type": "string",
                            "description": "与 template_id 相同含义的别名",
                        },
                        "keyword": {
                            "type": "string",
                            "description": "可选，产品名称/型号关键词过滤",
                        },
                        "export_date": {
                            "type": "string",
                            "description": "可选，报价日期，格式 YYYY-MM-DD，默认当天",
                        },
                    },
                    "required": ["customer_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "sales_contract_export",
                "description": (
                    "【销售合同导出】根据客户与产品行生成销售合同 **Excel（.xlsx，送货单版式）**。"
                    "template_id 为 ``GET /api/document-templates?role=sales_contract_docx`` 的 ``slug``；"
                    "若选中 Word（.docx）登记项则自动改用库内送货单 Excel 源；省略 template_id 时按库默认解析。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {"type": "string", "description": "客户名称"},
                        "customer_phone": {"type": "string", "description": "可选，联系电话"},
                        "contract_date": {"type": "string", "description": "可选，合同日期"},
                        "template_id": {
                            "type": "string",
                            "description": "可选；模板 slug，来自 document-templates?role=sales_contract_docx",
                        },
                        "return_buckets_expected": {"type": "integer", "description": "可选，应退桶数"},
                        "return_buckets_actual": {"type": "integer", "description": "可选，实退桶数"},
                        "products": {
                            "type": "array",
                            "description": "产品列表",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "model_number": {"type": "string"},
                                    "name": {"type": "string"},
                                    "spec": {"type": "string"},
                                    "unit": {"type": "string"},
                                    "quantity": {"type": "string"},
                                    "unit_price": {"type": "string"},
                                },
                                "required": ["model_number"],
                            },
                        },
                    },
                    "required": ["customer_name", "products"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "validate_contract",
                "description": (
                    "【合同校验工具】在生成销售合同前校验客户名称和产品型号是否在数据库中存在。"
                    "返回校验结果、有效产品列表、无效产品列表及修正建议。"
                    "生成合同前必须调用此工具进行校验。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {
                            "type": "string",
                            "description": "客户/购买单位名称",
                        },
                        "products": {
                            "type": "array",
                            "description": "产品列表，每个产品包含 model_number（型号）和 quantity（数量）",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "model_number": {"type": "string", "description": "产品型号"},
                                    "quantity": {"type": "integer", "description": "数量（桶数）"},
                                    "name": {"type": "string", "description": "产品名称（可选）"},
                                },
                                "required": ["model_number"],
                            },
                        },
                    },
                    "required": ["customer_name", "products"],
                },
            },
        },
    ]
    if os.environ.get("FHD_DB_WRITE_TOKEN", "").strip():
        tools.append(_products_bulk_import_tool_def())
    return tools


def _handle_products_bulk_import(
    args: dict[str, Any], *, db_write_token: str | None
) -> dict[str, Any]:
    from backend.db_write_auth import configured_db_write_token, verify_db_write_token_value
    from backend.products_bulk_import import run_bulk_import

    if not configured_db_write_token():
        return {"error": "db_write_disabled", "message": "服务器未配置 FHD_DB_WRITE_TOKEN"}
    if not verify_db_write_token_value(db_write_token):
        return {
            "error": "unauthorized",
            "message": "缺少或错误的 db_write_token（须在聊天 JSON 中与 FHD_DB_WRITE_TOKEN 一致传入）",
        }
    return run_bulk_import(args)


def _handle_validate_contract(args: dict[str, Any]) -> dict[str, Any]:
    """处理合同校验"""
    try:
        from backend.contract_validator import (
            augment_validate_contract_client_fields,
            validate_contract as do_validate,
        )

        customer_name = args.get("customer_name", "")
        products = args.get("products", [])
        result = do_validate(customer_name, products)
        if not isinstance(result, dict):
            return result
        return augment_validate_contract_client_fields(result)
    except Exception as e:
        return {"error": "validation_failed", "message": str(e)}


_workflow_tool_registry_cache: list[dict[str, Any]] | None = None
_workflow_tool_registry_bulk_token_present: bool | None = None


def get_workflow_tool_registry() -> list[dict[str, Any]]:
    """
    工作流工具注册表：交给 planner / Chat Completions 的 `tools` 参数，
    使 LLM 能看见并发起 function calling。

    当前实现为 Excel 工具 + 模板工具（Word/Excel 双模板）；
    若以后增加非 Excel 工具，在此合并列表即可。

    缓存列表避免 planner 每轮重复构造大 dict；当 ``FHD_DB_WRITE_TOKEN`` 是否配置发生变化时
    会重建缓存，避免进程启动后补配令牌却仍看不到 ``products_bulk_import``。
    """
    global _workflow_tool_registry_cache, _workflow_tool_registry_bulk_token_present
    bulk_on = bool(os.environ.get("FHD_DB_WRITE_TOKEN", "").strip())
    if (
        _workflow_tool_registry_cache is not None
        and _workflow_tool_registry_bulk_token_present == bulk_on
    ):
        return _workflow_tool_registry_cache
    from backend.template_handler import get_template_tool_registry

    _workflow_tool_registry_bulk_token_present = bulk_on
    _workflow_tool_registry_cache = get_excel_tool_registry() + get_template_tool_registry()
    return _workflow_tool_registry_cache


def execute_workflow_tool(
    name: str,
    arguments: Mapping[str, Any] | str | None,
    workspace_root: str | None = None,
    db_write_token: str | None = None,
    planner_user_utterance: str | None = None,
) -> str:
    """
    Dispatch tool by name. arguments may be a dict or JSON string from the model.
    Returns JSON string for the assistant tool message content.

    ``planner_user_utterance``：当前轮用户原话，供 ``sales_contract_export`` 在并行线程中
    仍能合并 bridge（不单独依赖 threading.local）。
    """
    if arguments is None:
        args: dict[str, Any] = {}
    elif isinstance(arguments, str):
        args = json.loads(arguments) if arguments.strip() else {}
    else:
        args = dict(arguments)

    if name == "excel_analysis":
        result = handle_excel_analysis(args, workspace_root=workspace_root)
    elif name == "excel_schema_understand":
        result = handle_excel_schema_understand(args, workspace_root=workspace_root)
    elif name == "excel_vector_index":
        result = handle_excel_vector_index(args, workspace_root=workspace_root)
    elif name == "excel_vector_search":
        result = handle_excel_vector_search(args, workspace_root=workspace_root)
    elif name == "excel_prophet":
        result = handle_excel_prophet(args, workspace_root=workspace_root)
    elif name == "excel_chart_recommend":
        result = handle_excel_chart_recommend(args, workspace_root=workspace_root)
    elif name == "excel_join_compare":
        result = handle_excel_join_compare(args, workspace_root=workspace_root)
    elif name == "price_list_export":
        result = handle_price_list_export(args, workspace_root=workspace_root)
    elif name == "sales_contract_export":
        try:
            from backend.sales_contract_intent_bridge import (
                get_planner_contract_user_utterance,
                merge_planner_sales_contract_args,
            )

            utter = planner_user_utterance or get_planner_contract_user_utterance()
            args = merge_planner_sales_contract_args(dict(args), utter)
        except Exception:
            pass
        result = handle_sales_contract_export(args)
    elif name == "validate_contract":
        try:
            from backend.sales_contract_intent_bridge import (
                get_planner_contract_user_utterance,
                merge_planner_sales_contract_args,
            )

            utter = planner_user_utterance or get_planner_contract_user_utterance()
            args = merge_planner_sales_contract_args(dict(args), utter)
        except Exception:
            pass
        result = _handle_validate_contract(args)
    elif name == "products_bulk_import":
        result = _handle_products_bulk_import(args, db_write_token=db_write_token)
    else:
        result = {"error": "unknown_tool", "name": name}

    return json.dumps(result, ensure_ascii=False, default=str)
