"""Streaming planner path: mocked OpenAI stream chunks, no API key."""

import json
from unittest.mock import MagicMock

from backend.planner import chat_stream_text


def _chunk(delta, finish_reason=None):
    ch0 = MagicMock(finish_reason=finish_reason, delta=delta)
    return MagicMock(choices=[ch0])


def test_chat_stream_yields_content_parts_final_turn():
    d1 = MagicMock()
    d1.content = "hel"
    d1.tool_calls = None
    d2 = MagicMock()
    d2.content = "lo"
    d2.tool_calls = None
    stream = [_chunk(d1), _chunk(d2, finish_reason="stop")]

    client = MagicMock()
    client.chat.completions.create.return_value = iter(stream)

    parts = list(
        chat_stream_text(
            "hi",
            client=client,
            system_prompt="",
            runtime_context=None,
        )
    )
    assert parts == ["hel", "lo"]
    client.chat.completions.create.assert_called_once()
    kw = client.chat.completions.create.call_args.kwargs
    assert kw.get("stream") is True


def test_chat_stream_tool_round_then_text():
    """First stream turn finishes with tool_calls; second turn streams text."""
    tc_a = MagicMock()
    tc_a.index = 0
    tc_a.id = "c1"
    tc_a.function = MagicMock(name="excel_analysis", arguments="")

    tc_b = MagicMock()
    tc_b.index = 0
    tc_b.id = None
    tc_b.function = MagicMock(name=None, arguments=json.dumps({"action": "read", "file_path": "a.xlsx"}))

    stream1 = [
        _chunk(MagicMock(content=None, tool_calls=[tc_a])),
        _chunk(MagicMock(content=None, tool_calls=[tc_b]), finish_reason="tool_calls"),
    ]

    d1 = MagicMock(content="完", tool_calls=None)
    d2 = MagicMock(content="成", tool_calls=None)
    stream2 = [_chunk(d1), _chunk(d2, finish_reason="stop")]

    client = MagicMock()
    client.chat.completions.create.side_effect = [iter(stream1), iter(stream2)]

    def fake_execute(name: str, raw_args: str, workspace_root=None):
        return json.dumps({"action": "read", "row_count": 0}, ensure_ascii=False)

    import backend.planner as planner_mod

    orig = planner_mod.execute_workflow_tool
    planner_mod.execute_workflow_tool = fake_execute
    try:
        parts = list(chat_stream_text("分析", client=client, workspace_root="."))
    finally:
        planner_mod.execute_workflow_tool = orig

    assert parts == ["完", "成"]
    assert client.chat.completions.create.call_count == 2
