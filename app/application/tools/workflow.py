"""Workflow tool registry + dispatcher + Excel/import handlers.

import logging

logger = logging.getLogger(__name__)
Phase 4B 从 ``app.legacy.tools`` 吸收实现。本模块汇总所有工作流工具的:

- 注册表 :func:`get_workflow_tool_registry` / :func:`_base_registry`
- 分派器 :func:`execute_workflow_tool`
- Excel 分析 / 查询 / 聚合 / 统计:`handle_excel_analysis`
- Excel 导入数据库:`_handle_import_excel_to_database` 及推断映射

后续 (Phase 4C) 可再按工具组细拆到 ``excel_handlers.py`` /
``import_excel.py`` / ``registry.py`` / ``dispatcher.py``,外部 import 不变。
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd

from app.infrastructure.auth.db_token import configured_db_write_token
from app.infrastructure.excel.schema_service import ExcelSchemaUnderstandingService

_workflow_tool_registry_cache: list[dict[str, Any]] | None = None
_workflow_tool_registry_bulk_token_present: bool | None = None
_workflow_registry_cache_ver: int | None = None
# 递增以使进程内工具注册表缓存失效（新增工具时 bump）
_WORKFLOW_REG_VER = 2


def resolve_safe_excel_path(workspace_root_or_file: str, file_path: str | None = None) -> Path:
    """解析安全的 Excel 文件路径，支持多路径查找。"""
    if file_path is None:
        base = Path.cwd().resolve()
        fp = workspace_root_or_file
    else:
        base = Path(workspace_root_or_file).resolve()
        fp = file_path

    if Path(fp).is_absolute():
        p = Path(fp).resolve()
        if p.exists():
            return p
    else:
        p = (base / fp).resolve()
        if p.exists():
            try:
                p.relative_to(base)
                return p
            except ValueError:
                pass

    search_paths = []
    upload_dirs = []

    if base.name == "XCAGI":
        upload_dirs.append(base.parent / "uploads")
        upload_dirs.append(base.parent / "424")
        upload_dirs.append(base / "uploads")

    cwd = Path.cwd().resolve()
    upload_dirs.extend(
        [
            cwd / "uploads",
            cwd.parent / "uploads",
            cwd.parent / "424",
            cwd / "424",
            Path("E:/FHD/uploads"),
            Path("E:/FHD/424"),
            Path("E:/FHD/XCAGI/uploads"),
        ]
    )

    seen = set()
    for d in upload_dirs:
        if d.exists() and str(d.resolve()) not in seen:
            seen.add(str(d.resolve()))
            search_paths.append(d)

    fp_name = Path(fp).name
    for search_dir in search_paths:
        candidate = search_dir / fp_name
        if candidate.exists():
            return candidate.resolve()

    if Path(fp).is_absolute():
        return Path(fp).resolve()
    return (base / fp).resolve()


def _parse_excel_header_row_1based(args: dict[str, Any]) -> int | None:
    raw = args.get("header_row")
    if raw is None or raw == "":
        raw = args.get("header_row_index")
    if raw is None or raw == "":
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    return n if n >= 1 else None


def _read_excel_dataframe(
    p: Path,
    *,
    sheet_name: Any,
    header_row_1based: int | None,
) -> pd.DataFrame:
    kw: dict[str, Any] = {}
    if p.suffix.lower() in (".xlsx", ".xlsm"):
        kw["engine"] = "openpyxl"
    if sheet_name:
        kw["sheet_name"] = sheet_name
    if header_row_1based is not None:
        kw["header"] = header_row_1based - 1
    return pd.read_excel(p, **kw)


def run_natural_language_pandas(
    df: pd.DataFrame, natural_language: str, **kwargs
) -> dict[str, Any]:
    """将自然语言查询转换为 pandas 操作并执行（接 excel_text_to_pandas）。"""
    generated_code = ""
    error_msg: str | None = None
    result_df = df

    try:
        from app.legacy.excel_text_to_pandas import ExcelTextToPandas  # type: ignore

        converter = ExcelTextToPandas()
        code = converter.translate(natural_language, df)
        if code and code.strip():
            generated_code = code
            local_ns: dict = {"df": df.copy()}
            exec(code, {"pd": pd, "__builtins__": {}}, local_ns)  # noqa: S102
            out = local_ns.get("result", local_ns.get("df"))
            if isinstance(out, pd.DataFrame):
                result_df = out
    except Exception as e:
        error_msg = str(e)

    records = json.loads(
        result_df.head(200).replace({float("nan"): None}).to_json(orient="records")
    )
    return {
        "generated_code": generated_code,
        "result_kind": "dataframe",
        "row_count": len(result_df),
        "truncated": len(result_df) > 200,
        "returned_rows": min(len(result_df), 200),
        "columns": list(result_df.columns.astype(str)),
        "records": records,
        **({"error": error_msg} if error_msg else {}),
    }


def handle_excel_analysis(
    args: dict[str, Any], workspace_root: str | None = None
) -> dict[str, Any]:
    file_path = str(args.get("file_path") or "")
    action = str(args.get("action") or "read")
    sheet_name = args.get("sheet_name")
    header_1b = _parse_excel_header_row_1based(args)
    if not file_path:
        return {"success": False, "error": "file_path is required"}
    root = workspace_root or str(Path.cwd())
    try:
        p = resolve_safe_excel_path(root, file_path)
    except Exception as e:
        return {"success": False, "error": str(e), "workspace_root": root, "file_path": file_path}
    if not p.exists():
        return {
            "success": False,
            "error": "file not found",
            "file_path": file_path,
            "workspace_root": root,
            "resolved_path": str(p),
        }
    try:
        df = _read_excel_dataframe(p, sheet_name=sheet_name, header_row_1based=header_1b)
    except Exception as e:
        return {
            "success": False,
            "error": f"read failed: {e}",
            "file_path": file_path,
            "resolved_path": str(p),
            "sheet_name": sheet_name,
            "header_row": header_1b,
        }
    if action == "excel_query":
        nl = str(args.get("natural_language") or "").strip()
        out = run_natural_language_pandas(df, nl, file_path=file_path)
        out["action"] = "excel_query"
        return out
    if action == "read":
        max_return = 200
        slice_df = df.head(max_return)
        out: dict[str, Any] = {
            "success": True,
            "action": action,
            "file_path": file_path,
            "sheet_name": sheet_name,
            "columns": list(df.columns.astype(str)),
            "row_count": int(len(df)),
            "returned_rows": int(len(slice_df)),
            "truncated": len(df) > max_return,
            "records": json.loads(slice_df.replace({float("nan"): None}).to_json(orient="records")),
        }
        try:
            from app.routes.template_grid_core import _extract_customer_hint_from_excel

            customer_hint = str(
                _extract_customer_hint_from_excel(str(p), str(sheet_name).strip() or None) or ""
            ).strip()
            if customer_hint:
                out["customer_hint"] = customer_hint
        except Exception:
            logger.debug("suppressed exception", exc_info=True)
        if header_1b is not None:
            out["header_row"] = header_1b
        return out
    if action == "query":
        expr = str(args.get("query_expression") or "").strip()
        out_df = df.query(expr) if expr else df
        return {
            "success": True,
            "action": "query",
            "file_path": file_path,
            "row_count": int(len(out_df)),
            "records": json.loads(
                out_df.head(200).replace({float("nan"): None}).to_json(orient="records")
            ),
            "columns": list(out_df.columns.astype(str)),
        }
    if action == "aggregate":
        group_by = [str(x) for x in (args.get("group_by") or []) if str(x)]
        metrics = args.get("metrics") or []
        if group_by and isinstance(metrics, list):
            agg_map: dict[str, list[str]] = {}
            for m in metrics:
                if not isinstance(m, dict):
                    continue
                col = str(m.get("column") or "").strip()
                op = str(m.get("op") or "").strip()
                if col and op:
                    agg_map.setdefault(col, []).append(op)
            if agg_map:
                out_df = df.groupby(group_by, dropna=False).agg(agg_map).reset_index()
                out_df.columns = [
                    (
                        "_".join([str(c) for c in x if str(c) != ""]).strip("_")
                        if isinstance(x, tuple)
                        else str(x)
                    )
                    for x in out_df.columns
                ]
            else:
                out_df = df
        else:
            out_df = df
        return {
            "success": True,
            "action": "aggregate",
            "file_path": file_path,
            "row_count": int(len(out_df)),
            "records": json.loads(
                out_df.head(200).replace({float("nan"): None}).to_json(orient="records")
            ),
            "columns": list(out_df.columns.astype(str)),
        }
    if action == "statistics":
        return {
            "success": True,
            "action": "statistics",
            "file_path": file_path,
            "row_count": int(len(df)),
            "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
        }
    return {"success": False, "error": f"unsupported_action:{action}"}


def _base_registry() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "excel_analysis",
                "description": "分析 Excel 文件内容，支持读取、查询、聚合等操作。在需要处理 Excel 数据时必须先调用此工具获取文件内容。如果用户选中了特定工作表，请使用 sheet_name 参数指定工作表名称。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Excel 文件路径（相对于工作区的相对路径或绝对路径）",
                        },
                        "sheet_name": {
                            "type": "string",
                            "description": "工作表名称（Sheet名），用于读取特定工作表。如果用户选中了某个工作表，请使用此参数指定。",
                        },
                        "header_row": {
                            "type": "integer",
                            "description": "表头所在行号（Excel 从 1 开始计数）。报价单等多行标题表格必须与上传预览 extract-grid 检测到的 header_row_index / tables[].header_row 一致，否则会出现 Unnamed 列、大量 nan、价格错位。",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["read", "query", "aggregate", "statistics"],
                            "description": "操作类型：read读取数据、query按条件查询、aggregate聚合统计、statistics统计信息",
                        },
                        "query_expression": {
                            "type": "string",
                            "description": "当 action=query 时使用的查询表达式（pandas query 语法）",
                        },
                        "group_by": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "当 action=aggregate 时的分组列名",
                        },
                        "metrics": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "column": {"type": "string"},
                                    "op": {
                                        "type": "string",
                                        "enum": ["sum", "mean", "count", "min", "max"],
                                    },
                                },
                            },
                            "description": "当 action=aggregate 时的聚合指标",
                        },
                    },
                    "required": ["file_path", "action"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "excel_schema_understand",
                "description": "理解 Excel 文件的数据结构和 schema，返回列名、数据类型、样本数据等元信息。适合在分析前先了解文件结构。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Excel 文件路径（相对于工作区的相对路径或绝对路径）",
                        },
                        "sheet_name": {
                            "type": "string",
                            "description": "可选：工作表名称，默认第一个表。",
                        },
                        "header_row": {
                            "type": "integer",
                            "description": "可选：表头行号（Excel 从 1 开始）。多行标题表若不填则默认第一行为表头，易产生 Unnamed 列。",
                        },
                    },
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "excel_join_compare",
                "description": "合并或对比两个 Excel 文件的数据。支持 join（合并）和 diff（差异对比）两种操作。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["join", "diff"],
                            "description": "操作类型：join合并、diff差异对比",
                        },
                        "file_paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "当 action=join 时，两个文件的路径列表 [file1, file2]",
                        },
                        "file_path_a": {
                            "type": "string",
                            "description": "当 action=diff 时，第一个文件路径",
                        },
                        "file_path_b": {
                            "type": "string",
                            "description": "当 action=diff 时，第二个文件路径",
                        },
                        "join_keys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "当 action=join 时，用于合并的列名列表",
                        },
                        "how": {
                            "type": "string",
                            "enum": ["inner", "left", "right", "outer"],
                            "description": "当 action=join 时，合并方式（默认 inner）",
                        },
                        "key_columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "当 action=diff 时，用于对比的主键列名列表",
                        },
                    },
                    "required": ["action"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "excel_chart_recommend",
                "description": "根据 Excel 数据内容推荐合适的图表类型。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Excel 文件路径"}
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "import_excel_to_database",
                "description": (
                    "将 Excel 数据导入到数据库。系统会分析 Excel 内容并自动匹配字段进行导入。报价单等多行标题表必须传 header_row（与 extract-grid / excel_analysis 一致），否则列名会变成 Unnamed、映射错乱。可选 last_data_row_1based 截断表尾说明文字；未传时仍会对典型合同/报价表尾条款行做启发式过滤。如果系统需要授权令牌，会提示用户输入 DB_WRITE_TOKEN。"
                    "【重要】参数 unit_name 在本系统中表示「客户公司全称」（与主库 purchase_units / 产品上 unit 字段一致），用于把产品挂到该客户下；不是 SKU 计量单位（件、桶、箱等）。缺省时可从运行时上下文 customer_hint / excel_customer_hint 或 Excel「客户/购买单位」列推断。"
                    "若上下文已含 excel_customer_hint 或已解析的文档客户名，不要在对话中再向用户索要公司名称，直接调用本工具即可（unit_name 可填该名或留空）。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Excel 文件路径"},
                        "sheet_name": {
                            "type": "string",
                            "description": "工作表名称；与 excel_analysis 所选表一致",
                        },
                        "header_row": {
                            "type": "integer",
                            "description": "表头所在 Excel 行号（从 1 开始）。必须与上传预览检测的 header_row / excel_analysis 一致。",
                        },
                        "last_data_row_1based": {
                            "type": "integer",
                            "description": "可选：数据区最后一行的 Excel 行号（含），用于去掉表尾条款/说明行。与 header_row 同时使用时，保留的数据行数 = last_data_row_1based - header_row。",
                        },
                        "import_type": {
                            "type": "string",
                            "enum": ["products", "customers", "orders"],
                            "description": "导入类型：products产品、customers客户、orders订单",
                        },
                        "unit_name": {
                            "type": "string",
                            "description": "客户公司全称（业务上亦称「购买单位」= 往来客户，非件/桶等计量单位）。导入产品时必须指向该客户；可留空由服务端从 excel_customer_hint / customer_hint 推断",
                        },
                        "price_column": {
                            "type": "string",
                            "description": "可选：用作单价的表头子串（如「调价前」「调价后」）。不传时自动推断；若同时存在调价前/调价后等价类列，默认取调价前列。",
                        },
                        "confirm": {
                            "type": "boolean",
                            "description": "是否执行写入。默认 true（直接导入）；仅显式传 false 时返回预览。已配置令牌且请求已携带正确 db_write_token 时，服务端仍按已确认写入处理。",
                        },
                        "preview_only": {
                            "type": "boolean",
                            "description": "可选：是否仅预览不写入。true 时即使未传 confirm 也只返回预览。",
                        },
                        "db_write_token": {
                            "type": "string",
                            "description": "数据库写入授权令牌（如系统要求）",
                        },
                    },
                    "required": ["file_path", "import_type"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "generate_office_document",
                "description": (
                    "根据用户自然语言需求**直接生成可下载的 Word（.docx）或 Excel（.xlsx）文件**。"
                    "适用于：合同/协议（如技术服务合同、AI 服务合同）、报价单、项目清单、排期表、简单报表等。"
                    "调用后返回一次性下载链接，须完整转告用户该 URL。"
                    "若用户仅做数据分析而非要独立文件，不要用此工具。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_request": {
                            "type": "string",
                            "description": "用户对文档的完整要求（主题、甲乙方角色、关键条款或表格列等）",
                        },
                        "output_format": {
                            "type": "string",
                            "enum": ["docx", "xlsx"],
                            "description": "docx=Word 文书；xlsx=表格",
                        },
                    },
                    "required": ["user_request", "output_format"],
                },
            },
        },
    ]


def get_workflow_tool_registry() -> list[dict[str, Any]]:
    global _workflow_tool_registry_cache, _workflow_tool_registry_bulk_token_present, _workflow_registry_cache_ver
    bulk_on = bool((os.environ.get("FHD_DB_WRITE_TOKEN") or "").strip())
    if (
        _workflow_tool_registry_cache is not None
        and _workflow_tool_registry_bulk_token_present == bulk_on
        and _workflow_registry_cache_ver == _WORKFLOW_REG_VER
    ):
        return _workflow_tool_registry_cache
    reg = _base_registry()
    if bulk_on:
        reg.append(
            {
                "type": "function",
                "function": {
                    "name": "products_bulk_import",
                    "description": "批量导入产品数据到数据库。需要 DB_WRITE_TOKEN 环境变量授权。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Excel 文件路径"},
                            "sheet_name": {"type": "string", "description": "工作表名称"},
                            "mapping": {"type": "object", "description": "列名映射配置"},
                        },
                        "required": ["file_path"],
                    },
                },
            }
        )
    _workflow_tool_registry_cache = reg
    _workflow_tool_registry_bulk_token_present = bulk_on
    _workflow_registry_cache_ver = _WORKFLOW_REG_VER
    return reg


def execute_workflow_tool(
    name: str,
    args: dict[str, Any] | str,
    workspace_root: str | None = None,
    *,
    db_write_token: str | None = None,
) -> str:
    if isinstance(args, str):
        try:
            args = json.loads(args or "{}")
        except Exception:
            args = {}
    try:
        from app.mod_sdk.planner_native_tools import try_execute_native_planner_tool

        native_raw, _mod = try_execute_native_planner_tool(
            name, args, workspace_root, db_write_token=db_write_token
        )
        if native_raw is not None:
            return native_raw
    except Exception:
        logger.debug("planner native tool dispatch skipped", exc_info=True)
    if name == "excel_analysis":
        return json.dumps(
            handle_excel_analysis(args, workspace_root=workspace_root), ensure_ascii=False
        )
    if name == "excel_chart_recommend":
        return json.dumps(
            {
                "suggestions": [
                    {"chart_type": "bar", "title": "分类对比"},
                    {"chart_type": "line", "title": "趋势分析"},
                ]
            },
            ensure_ascii=False,
        )
    if name == "excel_join_compare":
        try:
            action = str(args.get("action") or "join")
            if action == "join":
                f1, f2 = (args.get("file_paths") or [None, None])[:2]
                p1 = resolve_safe_excel_path(workspace_root or str(Path.cwd()), str(f1))
                p2 = resolve_safe_excel_path(workspace_root or str(Path.cwd()), str(f2))
                if not p1.exists():
                    return json.dumps(
                        {"success": False, "error": f"file not found: {f1}"}, ensure_ascii=False
                    )
                if not p2.exists():
                    return json.dumps(
                        {"success": False, "error": f"file not found: {f2}"}, ensure_ascii=False
                    )
                d1 = pd.read_excel(p1)
                d2 = pd.read_excel(p2)
                keys = [str(x) for x in (args.get("join_keys") or []) if str(x)]
                how = str(args.get("how") or "inner")
                out = d1.merge(d2, on=keys, how=how) if keys else d1
                return json.dumps(
                    {
                        "action": "join",
                        "row_count": int(len(out)),
                        "columns": list(out.columns.astype(str)),
                    },
                    ensure_ascii=False,
                )
            elif action == "diff":
                pa = resolve_safe_excel_path(
                    workspace_root or str(Path.cwd()), str(args.get("file_path_a") or "")
                )
                pb = resolve_safe_excel_path(
                    workspace_root or str(Path.cwd()), str(args.get("file_path_b") or "")
                )
                if not pa.exists():
                    return json.dumps(
                        {"success": False, "error": f"file not found: {args.get('file_path_a')}"},
                        ensure_ascii=False,
                    )
                if not pb.exists():
                    return json.dumps(
                        {"success": False, "error": f"file not found: {args.get('file_path_b')}"},
                        ensure_ascii=False,
                    )
                a = pd.read_excel(pa)
                b = pd.read_excel(pb)
                keys = [str(x) for x in (args.get("key_columns") or []) if str(x)]
                if keys:
                    la = a.set_index(keys)
                    lb = b.set_index(keys)
                    only_l = [idx for idx in la.index if idx not in lb.index]
                    only_r = [idx for idx in lb.index if idx not in la.index]
                    common = [idx for idx in la.index if idx in lb.index]
                    changed = 0
                    for idx in common:
                        if not la.loc[idx].equals(lb.loc[idx]):
                            changed += 1
                    return json.dumps(
                        {
                            "action": "diff",
                            "only_in_left": {"count": len(only_l)},
                            "only_in_right": {"count": len(only_r)},
                            "rows_with_value_changes": {"count": changed},
                        },
                        ensure_ascii=False,
                    )
                else:
                    return json.dumps(
                        {"action": "diff", "row_count": int(len(a))}, ensure_ascii=False
                    )
            else:
                return json.dumps(
                    {"success": False, "error": f"unknown action: {action}"}, ensure_ascii=False
                )
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    if name == "excel_prophet":
        try:
            file_path = str(args.get("file_path") or "")
            value_col = str(args.get("value_column") or args.get("y") or "").strip()
            date_col = str(args.get("date_column") or args.get("ds") or "").strip()
            periods = max(1, min(30, int(args.get("periods") or 6)))
            root = workspace_root or str(Path.cwd())
            if file_path:
                p = resolve_safe_excel_path(root, file_path)
                df = _read_excel_dataframe(p)
                if not value_col or value_col not in df.columns:
                    num_cols = [
                        c
                        for c in df.columns
                        if pd.to_numeric(df[c], errors="coerce").notna().sum() > 2
                    ]
                    value_col = num_cols[0] if num_cols else ""
                y = (
                    pd.to_numeric(df[value_col], errors="coerce").dropna()
                    if value_col
                    else pd.Series([], dtype=float)
                )
            else:
                y = pd.Series([], dtype=float)
            if len(y) < 2:
                return json.dumps(
                    {
                        "action": "forecast",
                        "future_forecast": [{"yhat": 0.0}] * periods,
                        "note": "数据不足，使用零预测",
                    },
                    ensure_ascii=False,
                )
            x = list(range(len(y)))
            # 简单线性回归预测
            n = len(x)
            sx = sum(x)
            sy = float(y.sum())
            sxy = sum(xi * yi for xi, yi in zip(x, y))
            sxx = sum(xi**2 for xi in x)
            denom = n * sxx - sx * sx
            slope = (n * sxy - sx * sy) / denom if denom else 0
            intercept = (sy - slope * sx) / n
            future = [
                {"period": i + 1, "yhat": round(intercept + slope * (len(y) + i), 4)}
                for i in range(periods)
            ]
            return json.dumps(
                {
                    "action": "forecast",
                    "future_forecast": future,
                    "model": "linear_regression",
                    "periods": periods,
                },
                ensure_ascii=False,
            )
        except Exception as e:
            return json.dumps(
                {"action": "forecast", "future_forecast": [], "error": str(e)}, ensure_ascii=False
            )
    if name == "excel_schema_understand":
        try:
            file_path = str(args.get("file_path") or "")
            sheet_n = args.get("sheet_name")
            header_1b = _parse_excel_header_row_1based(args)
            root = workspace_root or str(Path.cwd())
            p = resolve_safe_excel_path(root, file_path)
            if not p.exists():
                return json.dumps(
                    {
                        "success": False,
                        "error": "file_not_found",
                        "message": f"找不到文件: {file_path}",
                        "hint": "请确认文件已正确上传，或重新上传文件。",
                        "workspace_root": root,
                        "resolved_path": str(p),
                    },
                    ensure_ascii=False,
                )
            df = _read_excel_dataframe(p, sheet_name=sheet_n, header_row_1based=header_1b)
            svc = ExcelSchemaUnderstandingService()
            out = svc.understand_dataframe(df, file_path=file_path)
            return json.dumps(out, ensure_ascii=False)
        except Exception as e:
            return json.dumps(
                {"success": False, "error": str(e), "message": f"读取 Excel 文件失败: {e}"},
                ensure_ascii=False,
            )
    if name == "products_bulk_import":
        env_token = (os.environ.get("FHD_DB_WRITE_TOKEN") or "").strip()
        if env_token and (db_write_token or "") != env_token:
            return json.dumps({"error": "unauthorized"}, ensure_ascii=False)
        from app.application.excel_imports import run_bulk_import

        out = run_bulk_import(args)
        return json.dumps(out, ensure_ascii=False)
    if name == "excel_vector_index":
        file_path = str(args.get("file_path") or "").strip()
        if not file_path:
            return json.dumps(
                {"success": False, "error": "file_path is required"}, ensure_ascii=False
            )
        root = workspace_root or str(Path.cwd())
        p = resolve_safe_excel_path(root, file_path)
        if not p.exists():
            return json.dumps(
                {
                    "success": False,
                    "error": "file_not_found",
                    "file_path": file_path,
                    "resolved_path": str(p),
                },
                ensure_ascii=False,
            )
        from app.application import get_excel_vector_ingest_app_service

        index_name = str(args.get("index_name") or "").strip() or None
        index_id = str(args.get("index_id") or "").strip() or None
        result = get_excel_vector_ingest_app_service().ingest_excel(
            file_path=str(p),
            index_name=index_name,
            index_id=index_id,
        )
        if isinstance(result, dict) and result.get("success") and result.get("index_id"):
            result["excel_vector_index_id"] = result.get("index_id")
            result["excel_index_id"] = result.get("index_id")
        return json.dumps(result, ensure_ascii=False)
    if name == "import_excel_to_database":
        return _handle_import_excel_to_database(
            args, workspace_root=workspace_root, db_write_token=db_write_token
        )
    if name == "generate_office_document":
        try:
            req = str(args.get("user_request") or args.get("prompt") or "").strip()
            fmt = str(args.get("output_format") or "docx").lower().strip()
            if fmt not in ("docx", "xlsx"):
                fmt = "docx"
            if not req:
                return json.dumps(
                    {"success": False, "error": "missing_user_request"}, ensure_ascii=False
                )
            from app.services.kitten_ai_document.generate import generate_office_file
            from app.services.kitten_ai_document.pickup import store_document_pickup

            content, fname = generate_office_file(req, fmt)  # type: ignore[arg-type]
            mime = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                if fmt == "xlsx"
                else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            token = store_document_pickup(content, fname, mime)
            return json.dumps(
                {
                    "success": True,
                    "message": f"已生成《{fname}》。请让用户在浏览器打开以下路径下载（一次性有效，勿泄露 token）：",
                    "pickup_token": token,
                    "file_name": fname,
                    "download_url": f"/api/ai/kitten/document/pickup/{token}",
                    "assistant_hint": (
                        "将 download_url 原样写入回复（可做成 Markdown 链接）；"
                        "不要再次调用 generate_office_document，除非用户明确要求重新生成。"
                    ),
                },
                ensure_ascii=False,
            )
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    return json.dumps({"success": False, "error": "unknown_tool", "tool": name}, ensure_ascii=False)


def _handle_import_excel_to_database(
    args: dict[str, Any],
    workspace_root: str | None = None,
    db_write_token: str | None = None,
) -> str:
    """处理 Excel 导入数据库请求。"""
    expected_write_token = str(configured_db_write_token() or "").strip()
    if expected_write_token:
        provided_token = str(args.get("db_write_token") or db_write_token or "").strip()
        if not provided_token:
            return json.dumps(
                {
                    "success": False,
                    "requires_token": True,
                    "token_name": "DB_WRITE_TOKEN",
                    "token_description": "数据库写入授权令牌",
                    "message": "导入数据需要数据库写入授权令牌。请输入令牌继续。",
                },
                ensure_ascii=False,
            )
        if provided_token != expected_write_token:
            return json.dumps(
                {"success": False, "error": "invalid_token", "message": "令牌无效，请重新输入"},
                ensure_ascii=False,
            )

    try:
        import_type = str(args.get("import_type") or "products")
        file_path = str(args.get("file_path") or "").strip()
        sheet_n = args.get("sheet_name")

        req_ctx = args.get("context")
        if not isinstance(req_ctx, dict):
            req_ctx = {}
        excel_analysis_ctx = args.get("excel_analysis")
        if not isinstance(excel_analysis_ctx, dict):
            excel_analysis_ctx = req_ctx.get("excel_analysis")
        if not isinstance(excel_analysis_ctx, dict):
            excel_analysis_ctx = {}

        if not str(sheet_n or "").strip():
            selected = req_ctx.get("excel_analysis_selected_sheet")
            if isinstance(selected, dict):
                sn = str(selected.get("sheet_name") or "").strip()
                if sn:
                    sheet_n = sn
        if not str(sheet_n or "").strip():
            sn = str(req_ctx.get("preferred_sheet_name") or "").strip()
            if sn:
                sheet_n = sn
        if not str(sheet_n or "").strip():
            pd0 = excel_analysis_ctx.get("preview_data")
            if isinstance(pd0, dict):
                sn = str(pd0.get("sheet_name") or "").strip()
                if sn:
                    sheet_n = sn

        if not file_path:
            return json.dumps(
                {"success": False, "error": "file_path is required"}, ensure_ascii=False
            )

        p = resolve_safe_excel_path(workspace_root or str(Path.cwd()), file_path)
        if not p.exists():
            return json.dumps({"success": False, "error": "file not found"}, ensure_ascii=False)

        unit_name = str(args.get("unit_name") or "").strip()

        if not unit_name:
            unit_name = str(args.get("excel_customer_hint") or "").strip()
            if not unit_name:
                if req_ctx:
                    unit_name = str(req_ctx.get("excel_customer_hint") or "").strip()
            if not unit_name:
                if excel_analysis_ctx:
                    unit_name = str(
                        excel_analysis_ctx.get("customer_hint")
                        or (excel_analysis_ctx.get("preview_data") or {}).get("customer_hint")
                        or ""
                    ).strip()
            if not unit_name:
                try:
                    from app.routes.template_grid_core import (
                        _extract_inline_customer_hits_from_cell,
                    )

                    linked_items: list[dict[str, Any]] = []
                    one = req_ctx.get("excel_linked_grid_preview")
                    if isinstance(one, dict):
                        linked_items.append(one)
                    many = req_ctx.get("excel_linked_grid_previews")
                    if isinstance(many, list):
                        linked_items.extend([x for x in many if isinstance(x, dict)])

                    for item in linked_items:
                        text = str(item.get("preview_text") or "").strip()
                        if text:
                            hits = _extract_inline_customer_hits_from_cell(text)
                            if hits:
                                unit_name = str(hits[0]).strip()
                                break
                except Exception:
                    logger.debug("suppressed exception", exc_info=True)
            if not unit_name:
                try:
                    from app.routes.template_grid_core import _extract_customer_hint_from_excel

                    unit_name = str(
                        _extract_customer_hint_from_excel(str(p), sheet_n if sheet_n else None)
                        or ""
                    ).strip()
                except Exception:
                    logger.debug("suppressed exception", exc_info=True)

        preview_only = bool(args.get("preview_only", False))
        confirm = bool(args.get("confirm", True))
        if preview_only:
            confirm = False
        if expected_write_token and not confirm:
            confirm = True

        header_1b = _parse_excel_header_row_1based(args)
        if header_1b is None and excel_analysis_ctx:
            try:
                from app.domain.context.session_context import detected_excel_header_row_1based

                header_1b = detected_excel_header_row_1based(
                    excel_analysis_ctx,
                    preferred_sheet_name=str(sheet_n or "").strip() or None,
                )
            except Exception:
                header_1b = None
        try:
            df = _read_excel_dataframe(p, sheet_name=sheet_n, header_row_1based=header_1b)
        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"read_excel_failed: {e}",
                    "sheet_name": sheet_n,
                    "header_row": header_1b,
                },
                ensure_ascii=False,
            )
        if df.empty:
            return json.dumps(
                {"success": False, "error": "Excel file is empty"}, ensure_ascii=False
            )

        price_column_hint = str(args.get("price_column") or "").strip() or None

        last_data = args.get("last_data_row_1based")
        try:
            last_data_i = (
                int(last_data) if last_data is not None and str(last_data).strip() != "" else None
            )
        except (TypeError, ValueError):
            last_data_i = None
        if last_data_i is not None and last_data_i >= 1:
            hdr_eff = header_1b if header_1b is not None else 1
            n_keep = last_data_i - hdr_eff
            if n_keep < 1:
                return json.dumps(
                    {
                        "success": False,
                        "error": "invalid_last_data_row",
                        "message": "last_data_row_1based 必须大于 header_row（或表头在第 1 行时大于 1）",
                        "header_row": hdr_eff,
                        "last_data_row_1based": last_data_i,
                    },
                    ensure_ascii=False,
                )
            df = df.iloc[:n_keep]

        columns = list(df.columns.astype(str))
        row_count = len(df)

        read_meta = {
            "sheet_name": sheet_n,
            "header_row": header_1b,
            "last_data_row_applied": last_data_i,
        }

        if import_type == "products":
            return _import_products_preview_or_execute(
                df,
                columns,
                unit_name,
                confirm,
                row_count,
                read_meta=read_meta,
                price_column_hint=price_column_hint,
            )
        elif import_type == "customers":
            return _import_customers_preview_or_execute(df, columns, confirm, row_count)
        elif import_type == "orders":
            return _import_orders_preview_or_execute(df, columns, unit_name, confirm, row_count)
        else:
            return json.dumps(
                {
                    "success": True,
                    "preview": True,
                    "import_type": import_type,
                    "columns": columns,
                    "row_count": row_count,
                    "sample_data": json.loads(
                        df.head(5).replace({float("nan"): None}).to_json(orient="records")
                    ),
                    "message": "未实现该类型的自动导入，请先导出为模板格式再导入。",
                },
                ensure_ascii=False,
            )

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


def _infer_product_field_mapping(
    columns: list[str],
    *,
    price_column_hint: str | None = None,
) -> dict[str, str]:
    """按列名推断产品字段映射。"""
    cols = [str(c) for c in columns]
    mapping: dict[str, str] = {}

    def _norm(s: str) -> str:
        return s.replace(" ", "").replace("\u3000", "").strip()

    norm_pairs = [(c, _norm(c)) for c in cols]
    taken: set[str] = set()

    def _take(field: str, col: str) -> None:
        if field not in mapping and col not in taken:
            mapping[field] = col
            taken.add(col)

    for c, cn in norm_pairs:
        cl = c.lower()
        if "规格" in cn and "号" not in cn and "编" not in cn:
            continue
        if ("编" in c and "号" in c) or "编号" in cn or "编码" in cn or "sku" in cl:
            _take("model_number", c)
            break
    for c, cn in norm_pairs:
        cl = c.lower()
        if c in taken:
            continue
        if "型号" in c or "model" in cl:
            _take("model_number", c)
            break

    for c, cn in norm_pairs:
        if c in taken:
            continue
        if "规格" in c or "规格" in cn or ("规" in c and "格" in c):
            _take("specification", c)
            break

    for c, cn in norm_pairs:
        cl = c.lower()
        if c in taken:
            continue
        if "产品名称" in cn or "品名" in cn or "名称" in c or "name" in cl:
            _take("name", c)
            break

    hint = _norm(price_column_hint) if price_column_hint else ""
    if hint:
        for c, cn in norm_pairs:
            if c in taken:
                continue
            cn_l = cn.lower()
            hl = hint.lower()
            if hint in cn or hl in cn_l or hint in c:
                _take("price", c)
                break

    if "price" not in mapping:
        price_order = [
            ("调价前", "price"),
            ("调价后", "price"),
            ("现价", "price"),
            ("单价", "price"),
            ("价格", "price"),
            ("price", "price"),
        ]
        for key_sub, field in price_order:
            ks = key_sub.lower()
            for c, cn in norm_pairs:
                if c in taken:
                    continue
                cn_l = cn.lower()
                if ks in cn_l or key_sub in c:
                    _take(field, c)
                    break
            if "price" in mapping:
                break

    for c, cn in norm_pairs:
        cl = c.lower()
        if c in taken:
            continue
        if "单位" in c or "unit" in cl:
            _take("unit", c)
            break
    for c, cn in norm_pairs:
        cl = c.lower()
        if c in taken:
            continue
        if "数量" in c or "quantity" in cl or "qty" in cl:
            _take("quantity", c)
            break
    for c, cn in norm_pairs:
        cl = c.lower()
        if c in taken:
            continue
        if "备注" in c or "描述" in c or "description" in cl:
            _take("description", c)
            break
    for c, cn in norm_pairs:
        cl = c.lower()
        if c in taken:
            continue
        if "品牌" in c or "brand" in cl:
            _take("brand", c)
            break
    for c, cn in norm_pairs:
        cl = c.lower()
        if c in taken:
            continue
        if "类别" in c or "category" in cl or "分类" in c:
            _take("category", c)
            break

    return mapping


def _excel_cell_as_clean_str(val: Any) -> str:
    """pandas/Excel 单元格转展示用字符串；NaN、字面量 'nan' 视为空。"""
    if val is None:
        return ""
    if isinstance(val, bool):
        return ""
    try:
        if pd.isna(val):
            return ""
    except TypeError:
        pass
    if isinstance(val, float) and val != val:
        return ""
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        if isinstance(val, float) and val.is_integer():
            return str(int(val))
        s = str(val).strip()
        if s.lower() in ("nan", "inf", "-inf"):
            return ""
        return s
    s = str(val).strip()
    if s.lower() in ("nan", "none", "null", "<na>", "nat"):
        return ""
    return s


def _excel_cell_as_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or (isinstance(val, float) and val != val):
            return default
        if pd.isna(val):
            return default
    except TypeError:
        pass
    try:
        v = float(val)
        if v != v:
            return default
        return v
    except (TypeError, ValueError):
        return default


# 报价单 / 合同表尾常见语句（命中则不作为产品行导入）
_CLAUSE_SUBSTRINGS = (
    "含税价",
    "含税",
    "月结",
    "数期",
    "担保",
    "付款责任",
    "保质保量",
    "验收签名",
    "所送货物",
    "若贵司",
    "未能按时付款",
    "配套使用",
    "我厂产品",
    "所示比例施工",
    "供应方签名",
    "供应方",
    "采购方",
    "盖章",
    "出资人",
    "签名及盖章",
    "以上价格为",
    "以上各种产品",
    "请严格按",
    "请配套",
)


def _looks_like_contract_or_footer_line(name: str) -> bool:
    t = (name or "").strip()
    if len(t) < 6:
        return False
    if any(s in t for s in _CLAUSE_SUBSTRINGS):
        return True
    # 「1、xxx」「2、xxx」式条款，且去掉序号后仍像说明句
    m = re.match(r"^\s*(\d+)[、．\.]\s*(.+)$", t)
    if m and len(m.group(2)) >= 8:
        rest = m.group(2)
        if any(s in rest for s in _CLAUSE_SUBSTRINGS):
            return True
        if re.search(r"(以上|所送|数期|保质|验收|付款|月结|含税|施工|配套|货物)", rest):
            return True
    return False


def _import_products_preview_or_execute(
    df,
    columns,
    unit_name,
    confirm,
    row_count,
    *,
    read_meta: dict[str, Any] | None = None,
    price_column_hint: str | None = None,
):
    field_mapping = _infer_product_field_mapping(columns, price_column_hint=price_column_hint)

    detected_unit = unit_name
    if not detected_unit and "unit" in field_mapping:
        units = df[field_mapping["unit"]].dropna().astype(str).unique()
        if len(units) == 1:
            detected_unit = str(units[0]).strip()

    spec_col = field_mapping.get("specification")
    model_col = field_mapping.get("model_number")
    name_col = field_mapping.get("name")

    records: list[dict[str, Any]] = []
    skipped_clause_like = 0
    for _, row in df.iterrows():
        spec_val = ""
        if spec_col:
            spec_val = _excel_cell_as_clean_str(row.get(spec_col, ""))
        elif model_col:
            spec_val = _excel_cell_as_clean_str(row.get(model_col, ""))
        name_val = _excel_cell_as_clean_str(row.get(name_col, "")) if name_col else ""
        model_val = (
            _excel_cell_as_clean_str(row.get(field_mapping["model_number"], ""))
            if "model_number" in field_mapping
            else ""
        )
        if name_val and _looks_like_contract_or_footer_line(name_val):
            skipped_clause_like += 1
            continue
        qty_raw = row.get(field_mapping["quantity"], 0) if "quantity" in field_mapping else 0
        try:
            qf = _excel_cell_as_float(qty_raw, 0.0)
            qty_i = int(qf)
        except (TypeError, ValueError):
            qty_i = 0
        record = {
            "model_number": ((model_val or None) if "model_number" in field_mapping else None),
            "name": ((name_val or None) if name_col else None),
            "specification": spec_val or None,
            "price": (
                _excel_cell_as_float(row.get(field_mapping.get("price", ""), 0), 0.0)
                if "price" in field_mapping
                else 0.0
            ),
            "unit": detected_unit or unit_name or "件",
            "quantity": qty_i if "quantity" in field_mapping else 0,
            "description": (
                _excel_cell_as_clean_str(row.get(field_mapping["description"], "")) or None
                if "description" in field_mapping
                else None
            ),
            "brand": (
                _excel_cell_as_clean_str(row.get(field_mapping["brand"], "")) or None
                if "brand" in field_mapping
                else None
            ),
            "category": (
                _excel_cell_as_clean_str(row.get(field_mapping["category"], "")) or None
                if "category" in field_mapping
                else None
            ),
        }
        if record["name"]:
            records.append(record)

    if not confirm:
        payload = {
            "success": True,
            "preview": True,
            "import_type": "products",
            "detected_unit": detected_unit,
            "field_mapping": field_mapping,
            "row_count": len(records),
            "skipped_clause_like_rows": skipped_clause_like,
            "sample_data": records[:5],
            "message": (
                f"检测到 {len(records)} 条产品记录，绑定客户: {detected_unit or unit_name or '未指定'}。"
                + (
                    f" 已跳过疑似表尾条款行 {skipped_clause_like} 条。"
                    if skipped_clause_like
                    else ""
                )
                + "当前为预览模式，传 confirm=true 或去掉 preview_only 可直接导入。"
            ),
        }
        if read_meta:
            payload["read_options"] = read_meta
        return json.dumps(payload, ensure_ascii=False)

    try:
        from app.bootstrap import get_customer_app_service, get_products_service
        from app.services.unified_query_service import find_purchase_unit

        if detected_unit or unit_name:
            target_unit = detected_unit or unit_name
            if not find_purchase_unit(unit_name=target_unit):
                customer_service = get_customer_app_service()
                customer_service.create(
                    {
                        "customer_name": target_unit,
                        "contact_person": None,
                        "contact_phone": None,
                        "contact_address": None,
                    }
                )

        products_service = get_products_service()
        for record in records:
            record["unit"] = detected_unit or unit_name or "件"

        result = products_service.batch_add_products(records)

        imported = 0
        failed = 0
        if isinstance(result, dict):
            imported = int(result.get("success_count") or result.get("imported") or 0)
            failed = int(result.get("failed_count") or result.get("failed") or 0)
            if imported == 0 and failed == 0 and isinstance(result.get("data"), dict):
                nested = result["data"]
                imported = int(nested.get("success_count") or 0)
                failed = int(nested.get("failed_count") or 0)
        msg = (
            result.get("message")
            if isinstance(result, dict) and result.get("message")
            else f"成功导入 {imported} 条产品"
        )

        return json.dumps(
            {
                "success": True,
                "preview": False,
                "imported": imported,
                "failed": failed,
                "skipped_clause_like_rows": skipped_clause_like,
                "message": msg
                + (
                    f"（另跳过疑似条款/表尾行 {skipped_clause_like} 条）"
                    if skipped_clause_like
                    else ""
                ),
            },
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps({"success": False, "error": f"导入失败: {str(e)}"}, ensure_ascii=False)


def _import_customers_preview_or_execute(df, columns, confirm, row_count):
    records = []
    for _, row in df.iterrows():
        record = {}
        for col in columns:
            col_l = col.lower()
            val = str(row.get(col, "")).strip()
            if "名称" in col or "name" in col_l or "客户" in col:
                record["customer_name"] = val
            elif "联系人" in col or "contact" in col_l or "person" in col_l:
                record["contact_person"] = val
            elif "电话" in col or "phone" in col_l or "mobile" in col_l:
                record["contact_phone"] = val
            elif "地址" in col or "address" in col_l:
                record["contact_address"] = val

        if record.get("customer_name"):
            records.append(record)

    if not confirm:
        return json.dumps(
            {
                "success": True,
                "preview": True,
                "import_type": "customers",
                "row_count": len(records),
                "sample_data": records[:5],
                "message": (
                    f"检测到 {len(records)} 条客户记录。"
                    f"当前为预览模式，传 confirm=true 或去掉 preview_only 可直接导入。"
                ),
            },
            ensure_ascii=False,
        )

    try:
        from app.bootstrap import get_customer_app_service

        customer_service = get_customer_app_service()
        imported = 0
        failed = 0

        for record in records:
            result = customer_service.create(record)
            if result.get("success"):
                imported += 1
            else:
                failed += 1

        return json.dumps(
            {
                "success": True,
                "preview": False,
                "imported": imported,
                "failed": failed,
                "message": f"成功导入 {imported} 条客户，失败 {failed} 条",
            },
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps({"success": False, "error": f"导入失败: {str(e)}"}, ensure_ascii=False)


def _import_orders_preview_or_execute(df, columns, unit_name, confirm, row_count):
    """从 Excel 导入出货记录（订单）。"""
    sample_data = json.loads(df.head(5).replace({float("nan"): None}).to_json(orient="records"))
    # 推断列映射
    col_map: dict[str, str] = {}
    name_hints = {
        "产品名称": "product_name",
        "product_name": "product_name",
        "名称": "product_name",
    }
    model_hints = {
        "型号": "model_number",
        "model_number": "model_number",
        "产品型号": "model_number",
    }
    qty_hints = {
        "数量": "quantity",
        "quantity": "quantity",
        "qty": "quantity",
        "数量(桶)": "quantity",
    }
    unit_name_hints = {"购买单位": "unit_name", "客户": "unit_name", "purchase_unit": "unit_name"}
    for col in columns:
        col_lower = str(col).strip().lower()
        if col in name_hints or col_lower in {k.lower() for k in name_hints}:
            col_map[col] = "product_name"
        elif col in model_hints or col_lower in {k.lower() for k in model_hints}:
            col_map[col] = "model_number"
        elif col in qty_hints or col_lower in {k.lower() for k in qty_hints}:
            col_map[col] = "quantity"
        elif col in unit_name_hints or col_lower in {k.lower() for k in unit_name_hints}:
            col_map[col] = "unit_name"

    if not confirm:
        return json.dumps(
            {
                "success": True,
                "preview": True,
                "import_type": "orders",
                "columns": columns,
                "column_mapping": col_map,
                "row_count": row_count,
                "sample_data": sample_data,
                "message": f"检测到 {row_count} 条出货记录，确认导入请设置 confirm=true。",
            },
            ensure_ascii=False,
        )

    try:
        from app.bootstrap import get_shipment_app_service

        svc = get_shipment_app_service()
        imported = 0
        failed = 0
        for _, row in df.iterrows():
            try:
                effective_unit = (
                    unit_name
                    or str(
                        row.get(next((c for c, f in col_map.items() if f == "unit_name"), ""), "")
                        or ""
                    ).strip()
                )
                if not effective_unit:
                    failed += 1
                    continue
                product_name = str(
                    row.get(next((c for c, f in col_map.items() if f == "product_name"), ""), "")
                    or ""
                ).strip()
                model_number = str(
                    row.get(next((c for c, f in col_map.items() if f == "model_number"), ""), "")
                    or ""
                ).strip()
                qty_raw = row.get(next((c for c, f in col_map.items() if f == "quantity"), ""), 1)
                qty = max(1, int(float(qty_raw))) if qty_raw else 1
                items = [
                    {
                        "product_name": product_name or model_number,
                        "model_number": model_number,
                        "quantity": qty,
                    }
                ]
                result = svc.create_shipment(unit_name=effective_unit, items_data=items)
                if result.get("success"):
                    imported += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

        return json.dumps(
            {
                "success": True,
                "preview": False,
                "imported": imported,
                "failed": failed,
                "message": f"成功导入 {imported} 条出货记录，失败 {failed} 条",
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"订单导入失败: {str(e)}"}, ensure_ascii=False
        )


__all__ = [
    "resolve_safe_excel_path",
    "run_natural_language_pandas",
    "handle_excel_analysis",
    "get_workflow_tool_registry",
    "execute_workflow_tool",
]
