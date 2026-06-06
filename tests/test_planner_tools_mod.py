# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-planner-bridge"


def test_planner_mod_manifest_tools_execution_flag():
    data = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    cfg = data.get("config") or {}
    assert cfg.get("planner_tools_execution") is True


def test_planner_tools_config_file():
    cfg = json.loads((MOD_DIR / "config" / "planner_tools.json").read_text(encoding="utf-8"))
    assert cfg.get("schema_version") == 1
    native = cfg.get("mod_native_tools") or {}
    assert "excel_analysis" in (native.get("tools") or [])


def test_planner_blueprints_tools_execute_route():
    text = (MOD_DIR / "backend" / "blueprints.py").read_text(encoding="utf-8")
    assert "/tools/execute" in text
    assert "execute_planner_tool" in text


def test_list_planner_tools_registry_detail_host_path(monkeypatch):
    from app.mod_sdk import planner_native_tools as pnt
    from app.mod_sdk import planner_tools as pt

    monkeypatch.setattr(pt, "is_planner_tools_via_mod_enabled", lambda: False)
    monkeypatch.setattr(pnt, "is_planner_native_tools_enabled", lambda: False)
    data = pt.list_planner_tools_registry_detail()
    assert data.get("ok") is True
    assert data.get("execution_path") == "host.workflow"
    assert isinstance(data.get("tool_names"), list)
    assert len(data["tool_names"]) >= 1


def test_list_planner_tools_registry_detail_mod_facade(monkeypatch):
    from app.mod_sdk import planner_native_tools as pnt
    from app.mod_sdk import planner_tools as pt

    monkeypatch.setattr(pt, "is_planner_tools_via_mod_enabled", lambda: True)
    monkeypatch.setattr(pnt, "is_planner_native_tools_enabled", lambda: False)
    data = pt.list_planner_tools_registry_detail()
    assert data.get("execution_via_mod_facade") is True
    from tests.mod_sdk_expectations import MOD_FACADE_EXECUTION_PATHS

    assert data.get("execution_path") in MOD_FACADE_EXECUTION_PATHS
    assert "tools/execute" in str(data.get("tools_execute_endpoint") or "")


def test_execute_planner_tool_from_body_missing_name():
    from app.mod_sdk.planner_tools import execute_planner_tool_from_body

    out = execute_planner_tool_from_body({})
    assert out.get("ok") is False


def test_execute_planner_tool_excel_chart_recommend(monkeypatch):
    from app.mod_sdk.planner_tools import execute_planner_tool_from_body

    monkeypatch.setenv("XCAGI_PLANNER_TOOLS_VIA_MOD", "1")
    out = execute_planner_tool_from_body(
        {"tool_name": "excel_chart_recommend", "arguments": {"file_path": "x.xlsx"}}
    )
    assert out.get("ok") is True
    assert out.get("execution_path") == "mod_native"
    assert out.get("mod_id") == "xcagi-planner-excel-tools"
    raw = out.get("result") or ""
    parsed = json.loads(raw)
    assert "suggestions" in parsed


def test_resolve_planner_tool_executor_env(monkeypatch):
    from app.mod_sdk.planner_tools import (
        execute_planner_workflow_tool,
        resolve_planner_tool_executor,
    )

    monkeypatch.delenv("XCAGI_PLANNER_TOOLS_VIA_MOD", raising=False)
    monkeypatch.setattr(
        "app.mod_sdk.planner_tools.is_planner_tools_via_mod_enabled",
        lambda: False,
    )
    assert resolve_planner_tool_executor().__name__ == "execute_workflow_tool"

    monkeypatch.setenv("XCAGI_PLANNER_TOOLS_VIA_MOD", "1")
    monkeypatch.setattr(
        "app.mod_sdk.planner_tools.is_planner_tools_via_mod_enabled",
        lambda: True,
    )
    assert resolve_planner_tool_executor().__name__ == "execute_planner_workflow_tool"
    raw = execute_planner_workflow_tool("excel_chart_recommend", {})
    assert json.loads(raw).get("suggestions")
