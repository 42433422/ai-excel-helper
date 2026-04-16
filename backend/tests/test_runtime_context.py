from backend.runtime_context import (
    format_runtime_context_for_llm,
    merge_system_prompt,
    planner_workflow_interrupt_reply,
    runtime_context_after_workflow_interrupt,
)


def test_format_excel_file_path():
    text = format_runtime_context_for_llm({"excel_file_path": "uploads/abc.xlsx"})
    assert text is not None
    assert "uploads/abc.xlsx" in text
    assert "excel_analysis" in text


def test_format_multiple_paths():
    text = format_runtime_context_for_llm(
        {"excel_file_paths": ["a.xlsx", "b.xlsx"]}
    )
    assert text is not None
    assert "a.xlsx" in text and "b.xlsx" in text


def test_merge_system_prompt():
    m = merge_system_prompt("你是助手。", {"excel_file_path": "x.xlsx"})
    assert m is not None
    assert "你是助手" in m
    assert "x.xlsx" in m


def test_empty_context_returns_none():
    assert format_runtime_context_for_llm({}) is None
    assert format_runtime_context_for_llm(None) is None


def test_runtime_context_after_workflow_interrupt_strips_known_keys():
    prior = {
        "excel_file_path": "a.xlsx",
        "recent_messages": [{"role": "user", "content": "x"}],
        "custom": 1,
    }
    cleared = runtime_context_after_workflow_interrupt(prior)
    assert cleared == {"custom": 1}


def test_planner_workflow_interrupt_reply():
    assert planner_workflow_interrupt_reply("取消") is not None
    assert planner_workflow_interrupt_reply("  否  ") is not None
    assert planner_workflow_interrupt_reply("否但不是") is None
    assert planner_workflow_interrupt_reply("分析一下") is None


def test_format_synced_export_templates_in_runtime_context():
    text = format_runtime_context_for_llm(
        {
            "synced_export_templates": [
                {
                    "id": "pg-word:price_list_docx:price_list_default",
                    "kind": "word",
                    "displayName": "默认报价表",
                    "business_scope": "priceList",
                    "slug": "price_list_default",
                    "role": "price_list_docx",
                    "storage_relpath": "424/document_templates/price_list_default.docx",
                }
            ]
        }
    )
    assert text is not None
    assert "用户已同步的导出模板" in text
    assert "price_list_default" in text
    assert "price_list_docx" in text
