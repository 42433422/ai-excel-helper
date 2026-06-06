# -*- coding: utf-8 -*-
"""里程碑 F～F4：Planner 工作流工具原生实现（Mod 侧）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MOD_SOURCE = "mod:xcagi-planner-excel-tools"

NATIVE_TOOL_NAMES = frozenset(
    {
        "excel_chart_recommend",
        "excel_schema_understand",
        "excel_analysis",
        "excel_join_compare",
        "import_excel_to_database",
        "generate_office_document",
        "products_bulk_import",
        "excel_vector_index",
    }
)


def _parse_args(args: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args or "{}")
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _tag_source(out: dict[str, Any]) -> dict[str, Any]:
    out["source"] = MOD_SOURCE
    return out


def _inject_source_json(raw: str) -> str:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            _tag_source(parsed)
            return json.dumps(parsed, ensure_ascii=False)
    except json.JSONDecodeError:
        pass
    return raw


def _handle_excel_chart_recommend(_args: dict[str, Any]) -> str:
    return json.dumps(
        _tag_source(
            {
                "suggestions": [
                    {"chart_type": "bar", "title": "分类对比"},
                    {"chart_type": "line", "title": "趋势分析"},
                ],
            }
        ),
        ensure_ascii=False,
    )


def _handle_excel_schema_understand(args: dict[str, Any], workspace_root: str | None) -> str:
    from app.application.tools.workflow import (
        _parse_excel_header_row_1based,
        _read_excel_dataframe,
        resolve_safe_excel_path,
    )
    from app.infrastructure.excel.schema_service import ExcelSchemaUnderstandingService

    file_path = str(args.get("file_path") or "")
    sheet_n = args.get("sheet_name")
    header_1b = _parse_excel_header_row_1based(args)
    root = workspace_root or str(Path.cwd())
    p = resolve_safe_excel_path(root, file_path)
    if not p.exists():
        return json.dumps(
            _tag_source(
                {
                    "success": False,
                    "error": "file_not_found",
                    "message": f"找不到文件: {file_path}",
                    "hint": "请确认文件已正确上传，或重新上传文件。",
                    "workspace_root": root,
                    "resolved_path": str(p),
                }
            ),
            ensure_ascii=False,
        )
    try:
        df = _read_excel_dataframe(p, sheet_name=sheet_n, header_row_1based=header_1b)
        svc = ExcelSchemaUnderstandingService()
        out = svc.understand_dataframe(df, file_path=file_path)
        if isinstance(out, dict):
            _tag_source(out)
        return json.dumps(out, ensure_ascii=False)
    except Exception as e:
        return json.dumps(
            _tag_source(
                {
                    "success": False,
                    "error": str(e),
                    "message": f"读取 Excel 文件失败: {e}",
                }
            ),
            ensure_ascii=False,
        )


def _handle_excel_analysis(args: dict[str, Any], workspace_root: str | None) -> str:
    from app.application.tools.workflow import handle_excel_analysis

    out = handle_excel_analysis(args, workspace_root=workspace_root)
    if isinstance(out, dict):
        _tag_source(out)
    return json.dumps(out, ensure_ascii=False)


def _handle_excel_join_compare(args: dict[str, Any], workspace_root: str | None) -> str:
    import pandas as pd

    from app.application.tools.workflow import resolve_safe_excel_path

    root = workspace_root or str(Path.cwd())
    try:
        action = str(args.get("action") or "join")
        if action == "join":
            f1, f2 = (args.get("file_paths") or [None, None])[:2]
            p1 = resolve_safe_excel_path(root, str(f1))
            p2 = resolve_safe_excel_path(root, str(f2))
            if not p1.exists():
                return json.dumps(
                    _tag_source({"success": False, "error": f"file not found: {f1}"}),
                    ensure_ascii=False,
                )
            if not p2.exists():
                return json.dumps(
                    _tag_source({"success": False, "error": f"file not found: {f2}"}),
                    ensure_ascii=False,
                )
            d1 = pd.read_excel(p1)
            d2 = pd.read_excel(p2)
            keys = [str(x) for x in (args.get("join_keys") or []) if str(x)]
            how = str(args.get("how") or "inner")
            out_df = d1.merge(d2, on=keys, how=how) if keys else d1
            return json.dumps(
                _tag_source(
                    {
                        "action": "join",
                        "row_count": int(len(out_df)),
                        "columns": list(out_df.columns.astype(str)),
                    }
                ),
                ensure_ascii=False,
            )
        if action == "diff":
            pa = resolve_safe_excel_path(root, str(args.get("file_path_a") or ""))
            pb = resolve_safe_excel_path(root, str(args.get("file_path_b") or ""))
            if not pa.exists():
                return json.dumps(
                    _tag_source(
                        {"success": False, "error": f"file not found: {args.get('file_path_a')}"}
                    ),
                    ensure_ascii=False,
                )
            if not pb.exists():
                return json.dumps(
                    _tag_source(
                        {"success": False, "error": f"file not found: {args.get('file_path_b')}"}
                    ),
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
                changed = sum(
                    1 for idx in common if not la.loc[idx].equals(lb.loc[idx])
                )
                return json.dumps(
                    _tag_source(
                        {
                            "action": "diff",
                            "only_in_left": {"count": len(only_l)},
                            "only_in_right": {"count": len(only_r)},
                            "rows_with_value_changes": {"count": changed},
                        }
                    ),
                    ensure_ascii=False,
                )
            return json.dumps(
                _tag_source({"action": "diff", "row_count": int(len(a))}),
                ensure_ascii=False,
            )
        return json.dumps(
            _tag_source({"success": False, "error": f"unknown action: {action}"}),
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps(_tag_source({"success": False, "error": str(e)}), ensure_ascii=False)


def _handle_import_excel_to_database(
    args: dict[str, Any],
    workspace_root: str | None,
    db_write_token: str | None,
) -> str:
    from app.application.tools.workflow import _handle_import_excel_to_database

    raw = _handle_import_excel_to_database(
        args,
        workspace_root=workspace_root,
        db_write_token=db_write_token,
    )
    return _inject_source_json(raw)


def _handle_generate_office_document(args: dict[str, Any]) -> str:
    req = str(args.get("user_request") or args.get("prompt") or "").strip()
    fmt = str(args.get("output_format") or "docx").lower().strip()
    if fmt not in ("docx", "xlsx"):
        fmt = "docx"
    if not req:
        return json.dumps(
            _tag_source({"success": False, "error": "missing_user_request"}),
            ensure_ascii=False,
        )
    try:
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
            _tag_source(
                {
                    "success": True,
                    "message": (
                        f"已生成《{fname}》。请让用户在浏览器打开以下路径下载"
                        "（一次性有效，勿泄露 token）："
                    ),
                    "pickup_token": token,
                    "file_name": fname,
                    "download_url": f"/api/ai/kitten/document/pickup/{token}",
                    "assistant_hint": (
                        "将 download_url 原样写入回复（可做成 Markdown 链接）；"
                        "不要再次调用 generate_office_document，除非用户明确要求重新生成。"
                    ),
                }
            ),
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps(_tag_source({"success": False, "error": str(e)}), ensure_ascii=False)


def _handle_products_bulk_import(
    args: dict[str, Any],
    db_write_token: str | None,
) -> str:
    import os

    env_token = (os.environ.get("FHD_DB_WRITE_TOKEN") or "").strip()
    if env_token and str(db_write_token or "").strip() != env_token:
        return json.dumps(_tag_source({"error": "unauthorized"}), ensure_ascii=False)
    from app.application.excel_imports import run_bulk_import

    out = run_bulk_import(args)
    if isinstance(out, dict):
        _tag_source(out)
    return json.dumps(out, ensure_ascii=False)


def _handle_excel_vector_index(args: dict[str, Any], workspace_root: str | None) -> str:
    from app.application import get_excel_vector_ingest_app_service
    from app.application.tools.workflow import resolve_safe_excel_path

    file_path = str(args.get("file_path") or "").strip()
    if not file_path:
        return json.dumps(
            _tag_source({"success": False, "error": "file_path is required"}),
            ensure_ascii=False,
        )
    root = workspace_root or str(Path.cwd())
    p = resolve_safe_excel_path(root, file_path)
    if not p.exists():
        return json.dumps(
            _tag_source(
                {
                    "success": False,
                    "error": "file_not_found",
                    "file_path": file_path,
                    "resolved_path": str(p),
                }
            ),
            ensure_ascii=False,
        )
    index_name = str(args.get("index_name") or "").strip() or None
    index_id = str(args.get("index_id") or "").strip() or None
    result = get_excel_vector_ingest_app_service().ingest_excel(
        file_path=str(p),
        index_name=index_name,
        index_id=index_id,
    )
    if isinstance(result, dict):
        _tag_source(result)
        if result.get("success") and result.get("index_id"):
            result["excel_vector_index_id"] = result.get("index_id")
            result["excel_index_id"] = result.get("index_id")
    return json.dumps(result, ensure_ascii=False)


def run_native_tool(
    name: str,
    args: dict[str, Any] | str,
    *,
    workspace_root: str | None = None,
    db_write_token: str | None = None,
) -> str | None:
    """由 mod_sdk.planner_native_tools 调用；未识别的工具返回 None。"""
    tool = str(name or "").strip()
    if tool not in NATIVE_TOOL_NAMES:
        return None
    payload = _parse_args(args)
    if tool == "excel_chart_recommend":
        return _handle_excel_chart_recommend(payload)
    if tool == "excel_schema_understand":
        return _handle_excel_schema_understand(payload, workspace_root)
    if tool == "excel_analysis":
        return _handle_excel_analysis(payload, workspace_root)
    if tool == "excel_join_compare":
        return _handle_excel_join_compare(payload, workspace_root)
    if tool == "import_excel_to_database":
        return _handle_import_excel_to_database(payload, workspace_root, db_write_token)
    if tool == "generate_office_document":
        return _handle_generate_office_document(payload)
    if tool == "products_bulk_import":
        return _handle_products_bulk_import(payload, db_write_token)
    if tool == "excel_vector_index":
        return _handle_excel_vector_index(payload, workspace_root)
    return None
