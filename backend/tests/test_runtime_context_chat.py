"""runtime_context：对话侧注入 excel_analysis / recent_messages 摘要。"""

from __future__ import annotations

from backend.runtime_context import (
    format_excel_analysis_for_llm,
    format_recent_messages_excerpt_for_llm,
    merge_system_prompt,
)


def test_format_excel_analysis_includes_summary_and_fields():
    ctx = {
        "excel_file_path": "uploads/a.xlsx",
        "excel_analysis": {
            "file_name": "报价.xlsx",
            "summary": "已查询并完成 1 个工作表的分析。\n下面是对每个工作表的简要说明",
            "fields": [{"label": "编号"}, {"label": "产品名称"}],
            "preview_data": {
                "sheet_names": ["Sheet1"],
                "sample_rows": [{"编号": "1", "产品名称": "测试品"}],
            },
        },
    }
    block = format_excel_analysis_for_llm(ctx)
    assert block
    assert "报价.xlsx" in block
    assert "已查询并完成" in block
    assert "编号" in block and "产品名称" in block
    assert "Sheet1" in block


def test_format_recent_messages_excerpt():
    ctx = {
        "recent_messages": [
            {"role": "user", "content": "第一条"},
            {"role": "ai", "content": "回复A"},
            {"role": "user", "content": "最后一条较长" * 80},
        ]
    }
    block = format_recent_messages_excerpt_for_llm(ctx)
    assert block
    assert "[user]" in block
    assert "最后一条" in block


def test_merge_system_prompt_includes_excel_and_recent_without_products():
    ctx = {
        "excel_file_path": "uploads/a.xlsx",
        "excel_analysis": {
            "file_name": "f.xlsx",
            "summary": "已提取：主要列含单价、数量。",
            "fields": [{"label": "单价"}],
            "preview_data": {"sample_rows": [{"单价": "10"}]},
        },
        "recent_messages": [{"role": "user", "content": "请分析表"}],
    }
    merged = merge_system_prompt(None, ctx, include_products_context=False)
    assert merged
    assert "uploads/a.xlsx" in merged
    assert "已提取" in merged
    assert "单价" in merged
    assert "请分析表" in merged


def test_merge_system_prompt_db_write_excel_tool_chain():
    ctx = {
        "chat_db_write_authorized": True,
        "excel_file_path": "424/报价.xlsx",
        "excel_analysis": {"file_name": "报价.xlsx", "summary": "样例摘要"},
    }
    merged = merge_system_prompt(None, ctx, include_products_context=False)
    assert merged
    assert "products_bulk_import" in merged
    assert "excel_analysis" in merged
    assert "dry_run" in merged
