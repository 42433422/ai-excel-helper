"""
将上传/会话侧的运行时信息格式化为 LLM 可见的 system 文案（如 Excel 相对路径）。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Mapping

logger = logging.getLogger(__name__)

# 注入 Planner system 时的体积上限（避免 token 爆炸）
_EXCEL_ANALYSIS_SUMMARY_MAX_CHARS = 6000
_EXCEL_FIELD_LABELS_MAX = 80
_EXCEL_SAMPLE_ROWS_MAX = 15
_EXCEL_SAMPLE_ROW_KEYS_MAX = 12
_EXCEL_CELL_VALUE_MAX_CHARS = 80
_RECENT_MESSAGES_MAX = 4
_RECENT_MESSAGE_CONTENT_MAX_CHARS = 300

# 用户明确中断工作流（如「取消」）时从会话上下文剥离的键，避免下一轮仍注入 Planner。
_RESETTABLE_RUNTIME_CONTEXT_KEYS: frozenset[str] = frozenset(
    {
        "excel_file_path",
        "excel_file_paths",
        "excel_analysis",
        "excel_analysis_selected_sheet",
        "preferred_sheet_name",
        "recent_messages",
        "chat_db_write_authorized",
        "word_template_path",
    }
)

_INTERRUPT_REFLEX_INTENTS: frozenset[str] = frozenset({"stop", "confirm_no"})


def runtime_context_after_workflow_interrupt(
    prior: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """保留自定义键，去掉与当前 Excel/对话摘要/写库授权等相关的 Planner 注入字段。"""
    if not prior:
        return {}
    return {k: v for k, v in prior.items() if k not in _RESETTABLE_RUNTIME_CONTEXT_KEYS}


def planner_workflow_interrupt_reply(message: str) -> str | None:
    """
    与 Reflex 中 stop / confirm_no 一致：整句仅为停止或否认时返回固定短句，否则 None。
    用于在调用 LLM 前短路，并在响应里附带清理后的 runtime_context。
    """
    from backend.unified_ai.registry.reflex_registry import match_reflex

    m = (message or "").strip()
    if not m:
        return None
    pat = match_reflex(m)
    if pat is None or pat.intent not in _INTERRUPT_REFLEX_INTENTS:
        return None
    return pat.response


def _load_products_sample_for_llm(max_count: int = 30) -> list[dict[str, Any]]:
    """加载产品样本给 LLM 参考（仅加载活跃产品的前 N 条）。"""
    try:
        from backend.routers.xcagi_compat import _load_products_all_for_export
        products = _load_products_all_for_export(keyword=None, unit=None)
        return products[:max_count]
    except Exception as e:
        logger.warning("failed to load products sample: %s", e)
        return []


def _load_customers_sample_for_llm(max_count: int = 20) -> list[dict[str, Any]]:
    """加载客户/购买单位样本给 LLM 参考。"""
    try:
        from backend.routers.xcagi_compat import _load_customers_rows
        customers = _load_customers_rows()
        return customers[:max_count]
    except Exception as e:
        logger.warning("failed to load customers sample: %s", e)
        return []


def format_products_context_for_llm() -> str | None:
    """
    传递产品数据库信息给 LLM，使其知道有哪些产品和单位可供选择。
    在生成销售合同/价格表前必须参考此信息。
    """
    products = _load_products_sample_for_llm(max_count=30)
    customers = _load_customers_sample_for_llm(max_count=20)

    if not products and not customers:
        return None

    lines = ["【产品数据库参考信息】（生成合同/价格表前必须参考）"]

    if products:
        lines.append("\n## 已有产品（部分示例）：")
        lines.append("| 型号 | 名称 | 规格 | 单价 |")
        lines.append("|------|------|------|------|")
        for p in products[:20]:
            name = (p.get("name") or "").strip()
            model = (p.get("model_number") or "").strip()
            spec = (p.get("specification") or "").strip()
            price = p.get("price")
            price_str = f"{price:.2f}" if price is not None else "待查"
            unit = (p.get("unit") or "").strip()
            if unit:
                spec = f"{spec} {unit}" if spec else unit
            lines.append(f"| {model} | {name} | {spec} | {price_str} |")
        if len(products) > 20:
            lines.append(f"\n（共 {len(products)} 条产品，以上为前 20 条示例）")

    if customers:
        lines.append("\n## 已有客户/购买单位：")
        for c in customers[:15]:
            name = (c.get("customer_name") or c.get("name") or c.get("unit_name") or "").strip()
            if name:
                lines.append(f"- {name}")
        if len(customers) > 15:
            lines.append(f"（共 {len(customers)} 个客户，以上为前 15 条）")

    lines.append("\n**重要提示**：生成合同前必须确认产品型号和客户名称与本列表匹配，不存在的不得写入。")

    return "\n".join(lines)


def _truncate_text(text: str, max_len: int) -> str:
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _format_sample_rows_block(sample_rows: list[Any]) -> list[str]:
    out: list[str] = []
    if not isinstance(sample_rows, list) or not sample_rows:
        return out
    out.append("### 样例行（截断，用于理解列含义）")
    for i, row in enumerate(sample_rows[:_EXCEL_SAMPLE_ROWS_MAX]):
        if not isinstance(row, dict):
            continue
        parts: list[str] = []
        for k in list(row.keys())[:_EXCEL_SAMPLE_ROW_KEYS_MAX]:
            v = row.get(k)
            if v is None:
                vs = ""
            elif isinstance(v, (dict, list)):
                vs = _truncate_text(json.dumps(v, ensure_ascii=False), _EXCEL_CELL_VALUE_MAX_CHARS)
            else:
                vs = _truncate_text(str(v), _EXCEL_CELL_VALUE_MAX_CHARS)
            parts.append(f"{k}={vs}")
        out.append(f"- 第{i + 1}行: " + ("; ".join(parts) if parts else "(空)"))
    if len(sample_rows) > _EXCEL_SAMPLE_ROWS_MAX:
        out.append(f"（共 {len(sample_rows)} 行样例，此处仅展示前 {_EXCEL_SAMPLE_ROWS_MAX} 行）")
    return out


def format_excel_analysis_for_llm(runtime_context: Mapping[str, Any] | None) -> str | None:
    """
    将前端 extract-grid 后的 excel_analysis 摘要注入 system，使模型无需仅靠 @文件名 猜测表结构。
    不包含 grid_preview / 全量 all_sheets 单元格矩阵。
    """
    if not runtime_context:
        return None
    raw = runtime_context.get("excel_analysis")
    if not isinstance(raw, dict) or not raw:
        return None

    lines: list[str] = [
        "【已提取表格摘要】（来自上传/网格提取：列名与少量样例行供理解；**精确数值、全量行与入库必须以 "
        "excel_analysis（如 action=read）读盘结果为准**，勿仅凭本段编造或推断全表数据）。"
        "若对话中已有对同一文件成功的 `action=read` 工具结果，**勿再重复**相同参数的 read，应直接回答、"
        "换用 `aggregate`/`query` 或进入下一步工具（如 `products_bulk_import`）。"
    ]

    fn = str(raw.get("file_name") or "").strip()
    if fn:
        lines.append(f"- 文件名: `{fn}`")

    summary = str(raw.get("summary") or "").strip()
    if summary:
        lines.append("")
        lines.append("### 分析说明")
        lines.append(_truncate_text(summary, _EXCEL_ANALYSIS_SUMMARY_MAX_CHARS))

    sel = runtime_context.get("excel_analysis_selected_sheet")
    if isinstance(sel, dict):
        sn = str(sel.get("sheet_name") or "").strip()
        idx = sel.get("sheet_index")
        if sn or idx is not None:
            lines.append("")
            lines.append(f"- 用户关联工作表: {sn or '?'}（index={idx!r}）")
    psn = str(runtime_context.get("preferred_sheet_name") or "").strip()
    if psn and (not isinstance(sel, dict) or str(sel.get("sheet_name") or "").strip() != psn):
        lines.append(f"- preferred_sheet_name: `{psn}`")

    preview = raw.get("preview_data")
    if isinstance(preview, dict):
        sns = preview.get("sheet_names")
        if isinstance(sns, list) and sns:
            names = [str(x).strip() for x in sns if str(x).strip()]
            if names:
                lines.append("")
                lines.append("- Sheet 列表: " + "、".join(names[:40]))
                if len(names) > 40:
                    lines.append(f"（共 {len(names)} 个 sheet，此处列出前 40 个）")
        sh = str(preview.get("sheet_name") or preview.get("selected_sheet_name") or "").strip()
        if sh:
            lines.append(f"- 当前/主 sheet: `{sh}`")
        fp = str(preview.get("file_path") or "").strip()
        if fp:
            lines.append(f"- preview_data.file_path: `{fp}`")
        meta = preview.get("all_sheets_meta")
        if isinstance(meta, list) and meta:
            lines.append("")
            lines.append("### 多表拆分概要（元数据，无全网格）")
            for item in meta[:24]:
                if not isinstance(item, dict):
                    continue
                sname = str(item.get("sheet_name") or "").strip() or "?"
                sfields = item.get("fields") or []
                labels2: list[str] = []
                if isinstance(sfields, list):
                    for f in sfields[:20]:
                        if isinstance(f, dict):
                            lab = str(f.get("label") or f.get("name") or "").strip()
                            if lab:
                                labels2.append(lab)
                        elif isinstance(f, str) and f.strip():
                            labels2.append(f.strip())
                cnt = item.get("sample_row_count")
                extra = f"（样例行数约 {cnt}）" if isinstance(cnt, int) else ""
                if labels2:
                    lines.append(f"- 「{sname}」{extra}: " + "、".join(labels2))
            if len(meta) > 24:
                lines.append(f"（共 {len(meta)} 个分表元数据条目，此处展示前 24 个）")

    sheets = raw.get("sheets")
    if isinstance(sheets, list) and sheets:
        lines.append("")
        lines.append("### 分表字段（各表前几项）")
        for s in sheets[:12]:
            if not isinstance(s, dict):
                continue
            sname = str(s.get("sheet_name") or "").strip() or "?"
            sfields = s.get("fields") or []
            labels: list[str] = []
            if isinstance(sfields, list):
                for f in sfields[:20]:
                    if isinstance(f, dict):
                        lab = str(f.get("label") or f.get("name") or "").strip()
                        if lab:
                            labels.append(lab)
                    elif isinstance(f, str) and f.strip():
                        labels.append(f.strip())
            if labels:
                lines.append(f"- 「{sname}」: " + "、".join(labels))
        if len(sheets) > 12:
            lines.append(f"（共 {len(sheets)} 个分表结构条目，此处展示前 12 个）")

    fields = raw.get("fields")
    if isinstance(fields, list) and fields:
        labels: list[str] = []
        for f in fields[:_EXCEL_FIELD_LABELS_MAX]:
            if isinstance(f, dict):
                lab = str(f.get("label") or f.get("name") or "").strip()
                if lab:
                    labels.append(lab)
            elif isinstance(f, str) and f.strip():
                labels.append(f.strip())
        if labels:
            lines.append("")
            lines.append("### 字段列表（主表/合并视图）")
            lines.append("- " + "、".join(labels))
            if len(fields) > _EXCEL_FIELD_LABELS_MAX:
                lines.append(f"（共 {len(fields)} 个字段，此处列出前 {_EXCEL_FIELD_LABELS_MAX} 个）")

    if isinstance(preview, dict):
        sample_rows = preview.get("sample_rows")
        if isinstance(sample_rows, list) and sample_rows:
            lines.append("")
            lines.extend(_format_sample_rows_block(sample_rows))

    return "\n".join(lines) if len(lines) > 1 else None


def format_recent_messages_excerpt_for_llm(runtime_context: Mapping[str, Any] | None) -> str | None:
    """Planner 当前为单条 user message，用摘录补最近几轮对话要点。"""
    if not runtime_context:
        return None
    rms = runtime_context.get("recent_messages")
    if not isinstance(rms, list) or not rms:
        return None
    tail = rms[-_RECENT_MESSAGES_MAX:]
    lines: list[str] = ["【最近对话摘录】（仅要点，完整语义以用户本轮消息为准）"]
    for m in tail:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "user").strip() or "user"
        content = _truncate_text(
            str(m.get("content") or "").replace("\n", " ").strip(),
            _RECENT_MESSAGE_CONTENT_MAX_CHARS,
        )
        if not content:
            continue
        lines.append(f"- [{role}] {content}")
    return "\n".join(lines) if len(lines) > 1 else None


def format_synced_export_templates_for_llm(runtime_context: Mapping[str, Any] | None) -> str | None:
    """模板预览页同步到对话的 Excel / Word 导出模板登记，供模型选用对应工具与 template_id。"""
    if not runtime_context:
        return None
    raw = runtime_context.get("synced_export_templates")
    if not isinstance(raw, list) or not raw:
        return None
    lines: list[str] = [
        "【用户已同步的导出模板】（来自「模板预览」页；生成价格表/合同或填表时请优先匹配 slug / 业务范围）"
    ]
    for i, item in enumerate(raw[:24]):
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip().lower()
        dn = str(item.get("displayName") or item.get("display_name") or "").strip() or "(未命名)"
        scope = str(item.get("business_scope") or "").strip() or "?"
        tt = str(item.get("template_type") or "").strip()
        slug = str(item.get("slug") or "").strip()
        role = str(item.get("role") or "").strip()
        tid = str(item.get("id") or "").strip()
        rel = str(item.get("storage_relpath") or "").strip()
        bits = [f"{i + 1}. [{kind or '?'}] {dn}"]
        bits.append(f"业务={scope}")
        if tt:
            bits.append(f"type={tt}")
        if slug:
            bits.append(f"template_id/slug=`{slug}`")
        if role:
            bits.append(f"role=`{role}`")
        if tid:
            bits.append(f"registry_id=`{tid}`")
        if rel:
            bits.append(f"path=`{rel}`")
        lines.append("- " + " · ".join(bits))
    if len(raw) > 24:
        lines.append(f"（共 {len(raw)} 条登记，此处展示前 24 条）")
    lines.append(
        "**用法提示**：价格表 Word 导出请使用工具或接口中的 `template_id`（slug）；"
        "销售合同生成使用 `sales_contract` 相关能力与 `template_id`；"
        "Excel 导出/分析使用 `excel_analysis` 与用户给出的 `file_path`（若登记为 Excel 模板）。"
    )
    return "\n".join(lines)


def format_runtime_context_for_llm(runtime_context: Mapping[str, Any] | None) -> str | None:
    """
    供 Planner 拼进 system prompt。约定：
      - excel_file_path: str — 相对 WORKSPACE_ROOT 的路径
      - excel_file_paths: list[str] — 多个文件
    """
    if not runtime_context:
        return None

    lines: list[str] = ["【当前对话运行时上下文】"]

    if runtime_context.get("chat_db_write_authorized"):
        lines.append(
            "- 本轮请求已携带数据库写入授权：若用户要求把报价或产品行写入 PostgreSQL，"
            "应调用工具 products_bulk_import（customer_name=购买单位，items 为 model_number/name/specification/price；"
            "编号为空时用名称+规格生成型号键）。工具失败时再说明原因，不要默认改口成「只能手动录入」。"
        )

    fp = runtime_context.get("excel_file_path")
    if fp and isinstance(fp, str) and fp.strip():
        lines.append(
            f"- 用户已上传 Excel，调用 excel_analysis / excel_schema_understand / excel_prophet / "
            f"excel_chart_recommend / excel_join_compare 等工具时，请使用 file_path（相对工作区）为：`{fp.strip()}`"
        )

    fps = runtime_context.get("excel_file_paths")
    if isinstance(fps, (list, tuple)) and fps:
        paths = [str(p).strip() for p in fps if p and str(p).strip()]
        if paths:
            joined = "`, `".join(paths)
            lines.append(
                f"- 用户已上传多个 Excel，按需选用 file_path：`{joined}`"
            )

    analysis_block = format_excel_analysis_for_llm(runtime_context)
    if analysis_block:
        lines.append("")
        lines.append(analysis_block)

    recent_block = format_recent_messages_excerpt_for_llm(runtime_context)
    if recent_block:
        lines.append("")
        lines.append(recent_block)

    sync_tpl = format_synced_export_templates_for_llm(runtime_context)
    if sync_tpl:
        lines.append("")
        lines.append(sync_tpl)

    fp0 = runtime_context.get("excel_file_path")
    fp_ok = isinstance(fp0, str) and bool(fp0.strip())
    fps0 = runtime_context.get("excel_file_paths")
    fps_ok = isinstance(fps0, (list, tuple)) and any(str(p).strip() for p in fps0 if p)
    ea0 = runtime_context.get("excel_analysis")
    ea_ok = isinstance(ea0, dict) and bool(ea0)
    if runtime_context.get("chat_db_write_authorized") and (fp_ok or fps_ok or ea_ok):
        lines.append("")
        lines.append(
            "**报价 Excel → 产品库（须走工具）**：当用户要「导入 / 写入 / 同步到数据库」时，"
            "你必须先用 **excel_analysis**（`action=read`，`file_path` 用上文路径，必要时设 `header_row` / `sheet_name`）"
            "从工作区读真实行，再把行映射为 **products_bulk_import** 的 `items`（`name`、`specification`、`price` 用现价列如「调价后」；"
            "`model_number` 用编号列，可省略空编号由服务端生成）。"
            "`customer_name` 为购买单位/客户名称，可带 `supplier_name`、`quote_date`；可先 **`dry_run=true`** 校验。"
            "**禁止**用「无法直接操作数据库」、仅输出 SQL 或示例 JSON 代替上述工具调用；"
            "仅在工具不可用或返回错误时，再说明原因并给出人工步骤。"
        )
        if ea_ok:
            lines.append(
                "**减少无效轮次**：若上文【已提取表格摘要】或对话里已有一条对同一 `file_path` 成功的 "
                "`excel_analysis`（`action=read`）结果，**不要**再重复相同参数的 read；应直接调用 "
                "`products_bulk_import`，或改用 `aggregate` / `query` 等不同 action 以回答用户问题。"
            )

    if len(lines) <= 1:
        return None
    return "\n".join(lines)


def merge_system_prompt(
    base: str | None,
    runtime_context: Mapping[str, Any] | None,
    include_products_context: bool = True,
) -> str | None:
    """合并业务 system 与运行时上下文；若皆空则返回 None。

    Args:
        base: 基础 system prompt
        runtime_context: 运行时上下文（如 Excel 文件路径）
        include_products_context: 是否包含产品数据库信息（默认 True，帮助 LLM 避免生成不存在的单位/产品）
    """
    ctx_block = format_runtime_context_for_llm(runtime_context)
    parts = [p for p in (base.strip() if base else None, ctx_block) if p]

    if include_products_context:
        products_block = format_products_context_for_llm()
        if products_block:
            parts.append(products_block)

    parts.append(
        "【销售合同 · 口语与工具】用户用自然语描述多品、数量、店名（如「那个…」「帮我打印」「一统」、"
        "「慢干水」「PU稀释剂」混排）时，**不要**在未校验的情况下把整句塞进 `customer_name` 后直调 "
        "`sales_contract_export`：应先 `validate_contract`，或保证参数来自对用户原话的**结构化理解**。"
        "短句且已明确「客户全称 + 型号 + 桶/瓶数」时可校验后导出。"
    )

    rt = str((runtime_context or {}).get("_fhd_ai_tier") or "p1").strip().lower()
    if rt != "p2":
        parts.append(
            "【权限】当前为 P1 会话：`products_bulk_import` 工具已被禁用；若业务需要批量写库，"
            "请在 XCAGI 设置中开启开发者模式并配置与服务器环境变量 FHD_AI_ELEVATED_TOKEN 一致的口令（P2）。"
        )

    if not parts:
        return None
    return "\n\n".join(parts)
