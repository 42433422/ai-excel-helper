# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-planner-excel-tools"


def test_planner_excel_tools_manifest():
    data = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    tools = data.get("config", {}).get("native_planner_tools") or []
    assert "excel_chart_recommend" in tools
    assert "excel_schema_understand" in tools
    assert "excel_analysis" in tools
    assert "excel_join_compare" in tools
    assert "import_excel_to_database" in tools
    assert "generate_office_document" in tools
    assert "products_bulk_import" in tools
    assert "excel_vector_index" in tools


def test_tool_handlers_chart_recommend():
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-planner-excel-tools", "tool_handlers")
    raw = mod.run_native_tool("excel_chart_recommend", {})
    assert raw is not None
    parsed = json.loads(raw)
    assert parsed.get("suggestions")
    assert "xcagi-planner-excel-tools" in str(parsed.get("source"))


def test_try_execute_native_chart(monkeypatch):
    from app.mod_sdk import planner_native_tools as pnt

    monkeypatch.setattr(
        pnt,
        "_discover_native_tool_mods",
        lambda: [
            {
                "mod_id": "xcagi-planner-excel-tools",
                "mod_path": str(MOD_DIR),
                "tool_names": ["excel_chart_recommend"],
            }
        ],
    )
    monkeypatch.setattr(pnt, "is_planner_native_tools_enabled", lambda: True)
    raw, mod_id = pnt.try_execute_native_planner_tool("excel_chart_recommend", {})
    assert raw is not None
    assert mod_id == "xcagi-planner-excel-tools"
    assert "suggestions" in raw


def test_native_excel_join_compare_diff(monkeypatch):
    import pandas as pd

    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-planner-excel-tools", "tool_handlers")
    tmp = REPO / "tests" / "_tmp_join"
    tmp.mkdir(parents=True, exist_ok=True)
    pa = tmp / "a.xlsx"
    pb = tmp / "b.xlsx"
    pd.DataFrame({"id": [1, 2], "v": [10, 20]}).to_excel(pa, index=False)
    pd.DataFrame({"id": [1, 3], "v": [10, 30]}).to_excel(pb, index=False)
    try:
        raw = mod.run_native_tool(
            "excel_join_compare",
            {
                "action": "diff",
                "file_path_a": str(pa),
                "file_path_b": str(pb),
                "key_columns": ["id"],
            },
            workspace_root=str(REPO),
        )
        assert raw is not None
        parsed = json.loads(raw)
        assert parsed.get("action") == "diff"
        assert parsed.get("source") == "mod:xcagi-planner-excel-tools"
    finally:
        for f in (pa, pb):
            if f.exists():
                f.unlink()


def test_native_excel_analysis_delegates(monkeypatch):
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-planner-excel-tools", "tool_handlers")
    monkeypatch.setattr(
        "app.application.tools.workflow.handle_excel_analysis",
        lambda args, workspace_root=None: {"success": True, "action": "read", "row_count": 3},
    )
    raw = mod.run_native_tool("excel_analysis", {"file_path": "x.xlsx", "action": "read"})
    parsed = json.loads(raw or "{}")
    assert parsed.get("success") is True
    assert parsed.get("source") == "mod:xcagi-planner-excel-tools"


def test_native_generate_office_document(monkeypatch):
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-planner-excel-tools", "tool_handlers")
    monkeypatch.setattr(
        "app.services.kitten_ai_document.generate.generate_office_file",
        lambda req, fmt: (b"fake", "test.docx"),
    )
    monkeypatch.setattr(
        "app.services.kitten_ai_document.pickup.store_document_pickup",
        lambda content, fname, mime: "tok-test-123",
    )
    raw = mod.run_native_tool(
        "generate_office_document",
        {"user_request": "写一份测试合同", "output_format": "docx"},
    )
    parsed = json.loads(raw or "{}")
    assert parsed.get("success") is True
    assert "/api/ai/kitten/document/pickup/tok-test-123" in str(parsed.get("download_url"))
    assert parsed.get("source") == "mod:xcagi-planner-excel-tools"


def test_native_import_excel_requires_token_message(monkeypatch):
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-planner-excel-tools", "tool_handlers")
    monkeypatch.setattr(
        "app.application.tools.workflow._handle_import_excel_to_database",
        lambda args, workspace_root=None, db_write_token=None: json.dumps(
            {"success": False, "requires_token": True, "token_name": "DB_WRITE_TOKEN"}
        ),
    )
    raw = mod.run_native_tool("import_excel_to_database", {"file_path": "a.xlsx"})
    parsed = json.loads(raw or "{}")
    assert parsed.get("requires_token") is True
    assert parsed.get("source") == "mod:xcagi-planner-excel-tools"


def test_native_products_bulk_import_dry_run(monkeypatch):
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-planner-excel-tools", "tool_handlers")
    monkeypatch.delenv("FHD_DB_WRITE_TOKEN", raising=False)
    raw = mod.run_native_tool(
        "products_bulk_import",
        {"customer_name": "测试客户", "items": [{"sku": "A1"}], "dry_run": True},
    )
    parsed = json.loads(raw or "{}")
    assert parsed.get("success") is True
    assert parsed.get("dry_run") is True
    assert parsed.get("source") == "mod:xcagi-planner-excel-tools"


def test_native_products_bulk_import_unauthorized(monkeypatch):
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-planner-excel-tools", "tool_handlers")
    monkeypatch.setenv("FHD_DB_WRITE_TOKEN", "secret-token")
    raw = mod.run_native_tool(
        "products_bulk_import",
        {"customer_name": "测试客户", "items": [{"sku": "A1"}]},
        db_write_token="wrong",
    )
    parsed = json.loads(raw or "{}")
    assert parsed.get("error") == "unauthorized"
    assert parsed.get("source") == "mod:xcagi-planner-excel-tools"


def test_native_excel_vector_index(monkeypatch):
    import pandas as pd

    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-planner-excel-tools", "tool_handlers")
    tmp = REPO / "tests" / "_tmp_vector"
    tmp.mkdir(parents=True, exist_ok=True)
    px = tmp / "vec.xlsx"
    pd.DataFrame({"col": ["a", "b"]}).to_excel(px, index=False)
    monkeypatch.setattr(
        "app.application.get_excel_vector_ingest_app_service",
        lambda: type(
            "FakeIngest",
            (),
            {
                "ingest_excel": staticmethod(
                    lambda file_path, index_name=None, index_id=None: {
                        "success": True,
                        "index_id": "idx-test",
                        "index_name": index_name or "vec",
                        "source_file": "vec.xlsx",
                        "chunk_count": 2,
                    }
                )
            },
        )(),
    )
    try:
        raw = mod.run_native_tool(
            "excel_vector_index",
            {"file_path": str(px)},
            workspace_root=str(REPO),
        )
        parsed = json.loads(raw or "{}")
        assert parsed.get("success") is True
        assert parsed.get("excel_index_id") == "idx-test"
        assert parsed.get("source") == "mod:xcagi-planner-excel-tools"
    finally:
        if px.exists():
            px.unlink()


def test_workflow_excel_vector_index_fallback(monkeypatch):
    import pandas as pd

    from app.application.tools.workflow import execute_workflow_tool

    monkeypatch.setattr(
        "app.mod_sdk.planner_native_tools.try_execute_native_planner_tool",
        lambda *a, **k: (None, None),
    )
    tmp = REPO / "tests" / "_tmp_vector_wf"
    tmp.mkdir(parents=True, exist_ok=True)
    px = tmp / "wf.xlsx"
    pd.DataFrame({"x": [1]}).to_excel(px, index=False)
    monkeypatch.setattr(
        "app.application.get_excel_vector_ingest_app_service",
        lambda: type(
            "FakeIngest",
            (),
            {
                "ingest_excel": staticmethod(
                    lambda file_path, index_name=None, index_id=None: {
                        "success": True,
                        "index_id": "wf-idx",
                        "chunk_count": 1,
                    }
                )
            },
        )(),
    )
    try:
        raw = execute_workflow_tool(
            "excel_vector_index",
            {"file_path": str(px)},
            workspace_root=str(REPO),
        )
        parsed = json.loads(raw)
        assert parsed.get("success") is True
        assert parsed.get("excel_vector_index_id") == "wf-idx"
    finally:
        if px.exists():
            px.unlink()


def test_workflow_delegates_chart_to_native(monkeypatch):
    from app.mod_sdk import planner_native_tools as pnt

    monkeypatch.setattr(pnt, "is_planner_native_tools_enabled", lambda: True)
    monkeypatch.setattr(
        pnt,
        "_discover_native_tool_mods",
        lambda: [
            {
                "mod_id": "xcagi-planner-excel-tools",
                "mod_path": str(MOD_DIR),
                "tool_names": ["excel_chart_recommend"],
            }
        ],
    )
    from app.application.tools.workflow import execute_workflow_tool

    raw = execute_workflow_tool("excel_chart_recommend", {})
    parsed = json.loads(raw)
    assert "mod:xcagi-planner-excel-tools" in str(parsed.get("source"))
