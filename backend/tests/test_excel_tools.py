import json

from backend.tools import (
    execute_workflow_tool,
    get_excel_tool_registry,
    get_workflow_tool_registry,
    handle_excel_analysis,
    resolve_safe_excel_path,
)


def test_registry_exposes_excel_analysis_to_llm():
    wf = get_workflow_tool_registry()
    excel = get_excel_tool_registry()
    assert wf == excel
    names = [t["function"]["name"] for t in wf]
    assert names[0] == "excel_analysis"
    assert "excel_analysis" in names


def test_read_excel(excel_workspace):
    root = str(excel_workspace)
    out = json.loads(
        execute_workflow_tool(
            "excel_analysis",
            {"action": "read", "file_path": "sample.xlsx"},
            workspace_root=root,
        )
    )
    assert out["action"] == "read"
    assert out["row_count"] == 3
    assert len(out["records"]) == 3


def test_query_excel(excel_workspace):
    root = str(excel_workspace)
    out = json.loads(
        execute_workflow_tool(
            "excel_analysis",
            {"action": "query", "file_path": "sample.xlsx", "query_expression": "Age > 26"},
            workspace_root=root,
        )
    )
    assert out["action"] == "query"
    assert out["row_count"] == 2
    names = {r["Name"] for r in out["records"]}
    assert names == {"Alice", "Carol"}


def test_aggregate_excel(excel_workspace):
    root = str(excel_workspace)
    out = json.loads(
        execute_workflow_tool(
            "excel_analysis",
            {
                "action": "aggregate",
                "file_path": "sample.xlsx",
                "group_by": ["Dept"],
                "metrics": [{"column": "Age", "op": "mean"}, {"column": "Name", "op": "count"}],
            },
            workspace_root=root,
        )
    )
    assert out["action"] == "aggregate"
    assert out["row_count"] == 2
    depts = {r["Dept"] for r in out["records"]}
    assert depts == {"Eng", "Sales"}


def test_statistics_excel(excel_workspace):
    root = str(excel_workspace)
    out = json.loads(
        execute_workflow_tool(
            "excel_analysis",
            {"action": "statistics", "file_path": "sample.xlsx"},
            workspace_root=root,
        )
    )
    assert out["action"] == "statistics"
    assert out["row_count"] == 3
    assert "Age" in out["dtypes"]


def test_path_escape_rejected(excel_workspace):
    root = str(excel_workspace)
    out = handle_excel_analysis(
        {"action": "read", "file_path": "../outside.xlsx"},
        workspace_root=root,
    )
    assert "error" in out


def test_unknown_tool():
    out = json.loads(execute_workflow_tool("nope", {}, workspace_root="."))
    assert out["error"] == "unknown_tool"


def test_vector_index_tool_dispatch(excel_workspace, monkeypatch):
    root = str(excel_workspace)

    class _FakeSvc:
        def index_excel(self, file_path, **kwargs):
            _ = kwargs
            return {"indexed": 3, "file_path": file_path, "total_chunks": 3}

        def get_index_stats(self):
            return {"chunk_count": 3, "files_indexed": 1}

    monkeypatch.setattr("backend.tools._get_vector_service", lambda workspace_root: _FakeSvc())
    out = json.loads(
        execute_workflow_tool(
            "excel_vector_index",
            {"file_path": "sample.xlsx"},
            workspace_root=root,
        )
    )
    assert out["action"] == "vector_index"
    assert out["indexed"] == 3
    assert out["file_path"] == "sample.xlsx"
    assert out["index_stats"]["chunk_count"] == 3


def test_vector_search_tool_dispatch(excel_workspace, monkeypatch):
    root = str(excel_workspace)

    class _FakeSvc:
        def search(self, query, top_k=5):
            _ = (query, top_k)
            return [
                {
                    "score": 0.91,
                    "text": "产品名称=AAA | 单价=12",
                    "meta": {"file_path": "sample.xlsx", "row_index": 1},
                }
            ]

    monkeypatch.setattr("backend.tools._get_vector_service", lambda workspace_root: _FakeSvc())
    out = json.loads(
        execute_workflow_tool(
            "excel_vector_search",
            {"query": "AAA 单价", "top_k": 3, "file_path": "sample.xlsx"},
            workspace_root=root,
        )
    )
    assert out["action"] == "vector_search"
    assert out["count"] == 1
    assert out["results"][0]["meta"]["file_path"] == "sample.xlsx"


def test_resolve_safe_path(excel_workspace):
    root = str(excel_workspace)
    p = resolve_safe_excel_path(root, "sample.xlsx")
    assert p.is_file()
    assert p.suffix.lower() == ".xlsx"
