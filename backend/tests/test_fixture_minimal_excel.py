"""
Plan: four excel_analysis actions against committed fixture backend/tests/fixtures/minimal.xlsx.
"""

import json
from pathlib import Path

from backend.tools import execute_workflow_tool

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_TESTS_ROOT = _FIXTURES.parent
_MINIMAL = _FIXTURES / "minimal.xlsx"


def test_minimal_fixture_file_exists():
    assert _MINIMAL.is_file(), "run: pandas DataFrame.to_excel(backend/tests/fixtures/minimal.xlsx)"


def test_read_from_fixtures_dir():
    root = str(_TESTS_ROOT)
    out = json.loads(
        execute_workflow_tool(
            "excel_analysis",
            {"action": "read", "file_path": "fixtures/minimal.xlsx"},
            workspace_root=root,
        )
    )
    assert out["action"] == "read"
    assert out["row_count"] == 3
    products = {r["Product"] for r in out["records"]}
    assert products == {"A", "B", "C"}


def test_query_from_fixtures_dir():
    root = str(_TESTS_ROOT)
    out = json.loads(
        execute_workflow_tool(
            "excel_analysis",
            {
                "action": "query",
                "file_path": "fixtures/minimal.xlsx",
                "query_expression": "Qty > 8",
            },
            workspace_root=root,
        )
    )
    assert out["action"] == "query"
    assert out["row_count"] == 2


def test_aggregate_from_fixtures_dir():
    root = str(_TESTS_ROOT)
    out = json.loads(
        execute_workflow_tool(
            "excel_analysis",
            {
                "action": "aggregate",
                "file_path": "fixtures/minimal.xlsx",
                "group_by": ["Product"],
                "metrics": [{"column": "Qty", "op": "sum"}, {"column": "Price", "op": "mean"}],
            },
            workspace_root=root,
        )
    )
    assert out["action"] == "aggregate"
    assert out["row_count"] == 3


def test_statistics_from_fixtures_dir():
    root = str(_TESTS_ROOT)
    out = json.loads(
        execute_workflow_tool(
            "excel_analysis",
            {"action": "statistics", "file_path": "fixtures/minimal.xlsx"},
            workspace_root=root,
        )
    )
    assert out["action"] == "statistics"
    assert out["row_count"] == 3
    assert "Qty" in out["dtypes"]
