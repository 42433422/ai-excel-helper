import json

import pandas as pd
import pytest

from backend.tools import execute_workflow_tool


def test_excel_chart_recommend(excel_workspace):
    root = str(excel_workspace)
    raw = execute_workflow_tool(
        "excel_chart_recommend",
        {"file_path": "sample.xlsx", "max_suggestions": 5},
        workspace_root=root,
    )
    out = json.loads(raw)
    assert "suggestions" in out
    assert len(out["suggestions"]) >= 1
    assert any("chart_type" in s for s in out["suggestions"])


def test_excel_join_two_files(tmp_path):
    left = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
    right = pd.DataFrame({"id": [1, 2], "score": [10, 20]})
    left.to_excel(tmp_path / "l.xlsx", index=False)
    right.to_excel(tmp_path / "r.xlsx", index=False)
    root = str(tmp_path)
    raw = execute_workflow_tool(
        "excel_join_compare",
        {
            "action": "join",
            "file_paths": ["l.xlsx", "r.xlsx"],
            "join_keys": ["id"],
            "how": "inner",
        },
        workspace_root=root,
    )
    out = json.loads(raw)
    assert out.get("action") == "join"
    assert out["row_count"] == 2
    assert "name" in out["columns"] and "score" in out["columns"]


def test_excel_diff_two_files(tmp_path):
    a = pd.DataFrame({"id": [1, 2, 3], "v": [10, 20, 30]})
    b = pd.DataFrame({"id": [2, 3, 4], "v": [20, 999, 40]})
    a.to_excel(tmp_path / "a.xlsx", index=False)
    b.to_excel(tmp_path / "b.xlsx", index=False)
    root = str(tmp_path)
    raw = execute_workflow_tool(
        "excel_join_compare",
        {
            "action": "diff",
            "file_path_a": "a.xlsx",
            "file_path_b": "b.xlsx",
            "key_columns": ["id"],
        },
        workspace_root=root,
    )
    out = json.loads(raw)
    assert out.get("action") == "diff"
    assert out["only_in_left"]["count"] == 1
    assert out["only_in_right"]["count"] == 1
    assert out["rows_with_value_changes"]["count"] >= 1


def test_excel_prophet_forecast(tmp_path):
    pytest.importorskip("prophet")
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    df = pd.DataFrame({"ds": dates, "y": range(30)})
    df.to_excel(tmp_path / "ts.xlsx", index=False)
    root = str(tmp_path)
    raw = execute_workflow_tool(
        "excel_prophet",
        {
            "action": "forecast",
            "file_path": "ts.xlsx",
            "date_column": "ds",
            "value_column": "y",
            "periods": 7,
        },
        workspace_root=root,
    )
    out = json.loads(raw)
    assert out.get("action") == "forecast"
    assert len(out.get("future_forecast", [])) == 7
