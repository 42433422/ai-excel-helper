"""
Smoke: agentic loop calls tools twice then returns final text (mocked LLM, no API key).
"""

import json
from unittest.mock import MagicMock

from backend.planner import chat


def test_agentic_two_tool_rounds_then_answer():
    """read aggregate pattern: first round tool_calls read, second aggregate, third no tools."""
    tool_read = json.dumps(
        {"action": "read", "row_count": 2, "records": [{"x": 1}], "columns": ["x"], "truncated": False, "returned_rows": 1},
        ensure_ascii=False,
    )
    tool_agg = json.dumps(
        {"action": "aggregate", "row_count": 1, "records": [{"s": 2}], "columns": ["s"], "truncated": False, "returned_rows": 1},
        ensure_ascii=False,
    )

    msg1 = MagicMock()
    msg1.content = ""
    msg1.tool_calls = [
        MagicMock(
            id="call_1",
            function=MagicMock(name="excel_analysis", arguments=json.dumps({"action": "read", "file_path": "a.xlsx"})),
        )
    ]

    msg2 = MagicMock()
    msg2.content = ""
    msg2.tool_calls = [
        MagicMock(
            id="call_2",
            function=MagicMock(
                name="excel_analysis",
                arguments=json.dumps({"action": "aggregate", "file_path": "a.xlsx", "group_by": ["g"], "metrics": [{"column": "v", "op": "sum"}]}),
            ),
        )
    ]

    msg3 = MagicMock()
    msg3.content = "根据工具结果，汇总完成。"
    msg3.tool_calls = None

    choice1 = MagicMock(message=msg1)
    choice2 = MagicMock(message=msg2)
    choice3 = MagicMock(message=msg3)
    comp1 = MagicMock(choices=[choice1])
    comp2 = MagicMock(choices=[choice2])
    comp3 = MagicMock(choices=[choice3])

    client = MagicMock()
    client.chat.completions.create.side_effect = [comp1, comp2, comp3]

    def fake_execute(name: str, raw_args: str, workspace_root=None):
        if "aggregate" in raw_args:
            return tool_agg
        return tool_read

    import backend.planner as planner_mod

    orig = planner_mod.execute_workflow_tool
    planner_mod.execute_workflow_tool = fake_execute
    try:
        text = chat("分析表格", client=client, workspace_root=".", max_iterations=10)
    finally:
        planner_mod.execute_workflow_tool = orig

    assert "汇总完成" in text
    assert client.chat.completions.create.call_count == 3
