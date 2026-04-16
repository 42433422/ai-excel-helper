"""Planner：连续相同参数的 excel_analysis 只执行一次。"""

from __future__ import annotations

import json

from backend.planner import append_tool_messages, reset_planner_tool_dedup_state


class _Fn:
    __slots__ = ("name", "arguments")

    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class _Tc:
    __slots__ = ("id", "function")

    def __init__(self, tc_id: str, name: str, arguments: str) -> None:
        self.id = tc_id
        self.function = _Fn(name, arguments)


def test_duplicate_excel_analysis_skips_second_execution():
    reset_planner_tool_dedup_state()
    raw = json.dumps({"action": "read", "file_path": "x.xlsx"}, ensure_ascii=False)
    tc = _Tc("call_1", "excel_analysis", raw)
    calls: list[int] = []

    def run(name: str, a: str, root: str | None) -> str:
        calls.append(1)
        return json.dumps({"ok": True, "rows": 1}, ensure_ascii=False)

    msgs: list[dict] = []
    append_tool_messages(msgs, [tc], workspace_root=".", execute_tool=run)
    append_tool_messages(msgs, [tc], workspace_root=".", execute_tool=run)

    assert len(calls) == 1
    second = json.loads(msgs[-1]["content"])
    assert second.get("error") == "duplicate_tool_call"
    assert "hint" in second
