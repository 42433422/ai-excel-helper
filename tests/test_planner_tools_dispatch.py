# -*- coding: utf-8 -*-
"""里程碑 S2：Planner 工具执行须经 planner_tools 门面分派。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EXCEL_MOD = REPO / "mods" / "xcagi-planner-excel-tools"


def test_planner_excel_tools_manifest_execution_owner():
    data = json.loads((EXCEL_MOD / "manifest.json").read_text(encoding="utf-8"))
    cfg = data.get("config") or {}
    assert cfg.get("tools_execution_owner") == "mod"
    assert "excel_analysis" in (cfg.get("native_planner_tools") or [])


def test_execute_workflow_tool_delegates_to_native_first(monkeypatch):
    from app.application.tools import workflow as wf

    monkeypatch.setattr(
        "app.mod_sdk.planner_native_tools.try_execute_native_planner_tool",
        lambda *a, **k: ('{"source":"mod:test","ok":true}', "xcagi-planner-excel-tools"),
    )
    raw = wf.execute_workflow_tool("excel_analysis", {})
    parsed = json.loads(raw)
    assert parsed.get("source") == "mod:test"


def test_resolve_executor_facade_vs_host(monkeypatch):
    from app.mod_sdk.planner_tools import (
        execute_planner_workflow_tool,
        resolve_planner_tool_executor,
    )

    monkeypatch.setattr(
        "app.mod_sdk.planner_tools.is_planner_tools_via_mod_enabled",
        lambda: False,
    )
    assert resolve_planner_tool_executor().__name__ == "execute_workflow_tool"

    monkeypatch.setattr(
        "app.mod_sdk.planner_tools.is_planner_tools_via_mod_enabled",
        lambda: True,
    )
    assert resolve_planner_tool_executor().__name__ == "execute_planner_workflow_tool"
    raw = execute_planner_workflow_tool("excel_chart_recommend", {})
    assert "suggestions" in json.loads(raw)


def test_execute_planner_tool_from_body_mod_native_path(monkeypatch):
    from app.mod_sdk.planner_tools import execute_planner_tool_from_body

    monkeypatch.setenv("XCAGI_PLANNER_TOOLS_VIA_MOD", "1")
    out = execute_planner_tool_from_body({"tool_name": "excel_chart_recommend", "arguments": {}})
    assert out.get("ok") is True
    assert out.get("execution_path") == "mod_native"
    assert out.get("mod_id") == "xcagi-planner-excel-tools"
