import json

import numpy as np
import pandas as pd

import backend.tools as tools
from backend.excel_schema_understanding_service import dataframe_schema_snapshot
from backend.excel_text_to_pandas import _safe_exec_pandas, _validate_generated_code
from backend.tools import execute_workflow_tool


def test_dataframe_schema_snapshot():
    df = pd.DataFrame({"a": [1, 2], "b": ["x", None]})
    snap = dataframe_schema_snapshot(df, sample_rows=2)
    assert snap["row_count"] == 2
    assert "a" in snap["dtypes"]


def test_safe_exec_nlargest():
    df = pd.DataFrame({"Name": ["A", "B"], "Age": [20, 35]})
    code = "result = df.nlargest(1, 'Age')"
    out = _safe_exec_pandas(code, df)
    assert len(out) == 1
    assert int(out["Age"].iloc[0]) == 35


def test_validate_code_blocks_dunder():
    assert _validate_generated_code("result = df.__class__") is not None


def test_excel_query_mocked_generation(excel_workspace, monkeypatch):
    root = str(excel_workspace)

    def fake_run(df, nl, **kwargs):
        code = "result = df[df['Age'] == df['Age'].max()]"
        out = _safe_exec_pandas(code, df)
        return {
            "generated_code": code,
            "result_kind": "dataframe",
            "row_count": len(out),
            "truncated": False,
            "returned_rows": len(out),
            "columns": list(out.columns.astype(str)),
            "records": json.loads(out.replace({np.nan: None}).to_json(orient="records", date_format="iso")),
        }

    monkeypatch.setattr("backend.tools.run_natural_language_pandas", fake_run)
    raw = execute_workflow_tool(
        "excel_analysis",
        {
            "action": "excel_query",
            "file_path": "sample.xlsx",
            "natural_language": "年龄最大的记录",
        },
        workspace_root=root,
    )
    out = json.loads(raw)
    assert out["action"] == "excel_query"
    assert out["row_count"] >= 1


def test_excel_schema_understand_mocked(excel_workspace, monkeypatch):
    class FakeSchemaSvc:
        def understand_dataframe(self, df, *, file_path, sheet_name=None):
            return {
                "file_path": file_path,
                "sheet_name": sheet_name,
                "snapshot": {"row_count": len(df)},
                "llm_understanding": {
                    "table_summary": "测试表",
                    "business_domain": "测试",
                    "columns": [],
                },
            }

    monkeypatch.setattr(tools, "ExcelSchemaUnderstandingService", FakeSchemaSvc)
    root = str(excel_workspace)
    raw = execute_workflow_tool(
        "excel_schema_understand",
        {"file_path": "sample.xlsx"},
        workspace_root=root,
    )
    out = json.loads(raw)
    assert out["llm_understanding"]["table_summary"] == "测试表"
    assert out["snapshot"]["row_count"] == 3
