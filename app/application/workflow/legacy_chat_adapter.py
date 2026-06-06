"""Legacy planner chat adapter (absorbed).

Phase 4B 从 ``app.legacy.planner`` 吸收实现。``chat`` / ``chat_stream_sse_events``
两个主入口直接在此承载; xcagi_compat 以及其它应用服务通过本模块调用对话链。

内部工具执行仍走 :mod:`app.application.tools`,LLM 客户端与 runtime context
分别走 :mod:`app.infrastructure.llm.client` 与 :mod:`app.domain.context.session_context`。
"""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from openai import OpenAI

from app.application.workflow.multimodal_user_content import build_openai_user_content
from app.domain.context.session_context import (
    enrich_excel_tool_arguments,
    merge_system_prompt,
)
from app.infrastructure.llm.client import (
    get_openai_compatible_client,
    require_api_key,
    resolve_chat_model,
)

# 流式 SSE 里展示给用户的中文说明（避免裸 snake_case +「...]」像截断 bug）
# generate_office_document 的展示文案由 _tool_stream_call_label 按 output_format 细分
_PLANNER_TOOL_STREAM_LABELS: dict[str, str] = {
    "generate_office_document": "生成可下载文档（Word 或 Excel）",
    "import_excel_to_database": "导入 Excel 到数据库",
    "excel_analysis": "读取或分析 Excel",
    "excel_schema_understand": "识别 Excel 表结构",
    "excel_join_compare": "合并或对比 Excel 文件",
    "excel_chart_recommend": "根据数据推荐图表",
    "products_bulk_import": "批量导入产品数据",
}


def _get_workflow_tool_registry():
    from app.mod_sdk.planner_tools import (
        get_planner_chat_tool_registry,
        is_planner_tools_via_mod_enabled,
    )

    if is_planner_tools_via_mod_enabled():
        return get_planner_chat_tool_registry()
    from app.application.tools.workflow import get_workflow_tool_registry as _impl

    return _impl()


def _resolve_chat_execute_tool():
    from app.mod_sdk.planner_tools import resolve_planner_tool_executor

    return resolve_planner_tool_executor()


_TOOL_DEDUP: set[str] = set()
_TOOL_DEDUP_LOCK = threading.Lock()

# 这些工具可能在首轮就返回 requires_token,后续工具在串行语义下不应被执行;并行会改变该顺序。
_TOKEN_ORDER_SENSITIVE_TOOLS = frozenset({"import_excel_to_database", "products_bulk_import"})


def _resolve_chat_model_for_client(client: Any | None, explicit_model: str | None) -> str:
    if explicit_model:
        return explicit_model
    if client is not None and getattr(client, "is_modstore_openai_compatible", False):
        default_model = str(getattr(client, "default_model", "") or "").strip()
        default_provider = str(getattr(client, "default_provider", "") or "").strip()
        if default_model:
            return f"{default_provider}/{default_model}" if default_provider else default_model
    return resolve_chat_model()


def reset_planner_tool_dedup_state() -> None:
    with _TOOL_DEDUP_LOCK:
        _TOOL_DEDUP.clear()


def _tool_key(name: str, args: str) -> str:
    return f"{name}::{args}"


def _parse_generate_office_format(raw_arguments: str) -> str:
    """generate_office_document 的 output_format：docx / xlsx；解析失败返回空串。"""
    try:
        d = json.loads(raw_arguments or "{}")
        if isinstance(d, dict):
            fmt = str(d.get("output_format") or "").strip().lower()
            if fmt in ("docx", "xlsx"):
                return fmt
    except json.JSONDecodeError:
        pass
    return ""


def _tool_stream_call_label(tool_name: str, raw_arguments: str) -> str:
    if tool_name == "generate_office_document":
        fmt = _parse_generate_office_format(raw_arguments)
        if fmt == "docx":
            return "生成 Word 文档（.docx）"
        if fmt == "xlsx":
            return "生成 Excel 工作簿（.xlsx）"
    return _PLANNER_TOOL_STREAM_LABELS.get(tool_name, tool_name)


def _slow_tool_wait_message(tool_name: str, raw_arguments: str) -> str | None:
    """工具执行期间无 token 输出时的等待说明（按工具类型区分，避免合同场景误写「处理 Excel」）。"""
    if tool_name == "import_excel_to_database":
        return "\n（正在将 Excel 导入数据库，通常需数十秒至数分钟，请稍候勿关闭页面。）\n"
    if tool_name == "generate_office_document":
        fmt = _parse_generate_office_format(raw_arguments)
        if fmt == "docx":
            return "\n（正在生成 Word 文档（.docx），通常需数十秒至数分钟，请稍候勿关闭页面。）\n"
        if fmt == "xlsx":
            return (
                "\n（正在生成 Excel 工作簿（.xlsx），通常需数十秒至数分钟，请稍候勿关闭页面。）\n"
            )
        return (
            "\n（正在生成可下载文件（Word 或 Excel），通常需数十秒至数分钟，请稍候勿关闭页面。）\n"
        )
    return None


def _post_tool_round_hint(
    tcs: Sequence[object], tool_payloads: list[dict[str, Any]] | None = None
) -> str:
    """同一轮工具执行完毕后的单行提示；优先依据工具返回 JSON，避免失败仍显示「Word 已就绪」。"""
    payloads = tool_payloads or []
    docx_ok = False
    xlsx_ok = False
    import_ok = False
    fail_msgs: list[str] = []

    for i, t in enumerate(tcs):
        name = str(getattr(getattr(t, "function", None), "name", "") or "")
        raw = str(getattr(getattr(t, "function", None), "arguments", "") or "")
        pl: dict[str, Any] = payloads[i] if i < len(payloads) else {}

        if name == "generate_office_document":
            fmt = _parse_generate_office_format(raw)
            url = str(pl.get("download_url") or "").strip()
            if pl.get("success") is True and url:
                if fmt == "xlsx":
                    xlsx_ok = True
                else:
                    docx_ok = True
            else:
                err = str(pl.get("message") or pl.get("error") or "").strip()
                if pl.get("error") == "duplicate_tool_call":
                    err = err or "重复调用（相同参数已执行过）"
                if not err:
                    err = "文档生成未返回下载链接"
                if len(err) > 100:
                    err = err[:100] + "…"
                fail_msgs.append(err)

        elif name == "import_excel_to_database":
            if pl.get("requires_token"):
                continue
            if pl.get("success") is True:
                import_ok = True

    if fail_msgs and not (docx_ok or xlsx_ok):
        return f"\n[工具未成功：{fail_msgs[0]}，正在生成下一条回复…]\n"

    if docx_ok and not xlsx_ok and not import_ok:
        return "\n[工具已返回（Word 文档可下载），正在生成下一条回复…]\n"
    if xlsx_ok and not docx_ok and not import_ok:
        return "\n[工具已返回（Excel 文件可下载），正在生成下一条回复…]\n"
    if docx_ok and xlsx_ok:
        return "\n[工具已返回（Word 与 Excel 均可下载），正在生成下一条回复…]\n"
    if import_ok and not docx_ok and not xlsx_ok:
        return "\n[工具已返回（Excel 导入结果），正在生成下一条回复…]\n"
    return "\n[工具已返回结果，正在生成下一条回复…]\n"


def _planner_tools_max_workers() -> int:
    raw = (os.environ.get("FHD_PLANNER_TOOLS_MAX_PARALLEL") or "8").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 8
    return max(1, min(n, 32))


def append_tool_messages(
    messages: list[dict[str, Any]],
    tool_calls: list[Any],
    *,
    workspace_root: str | None,
    runtime_context: dict[str, Any] | None = None,
    execute_tool=None,
    db_write_token: str | None = None,
) -> dict[str, Any] | None:
    """执行工具调用并添加消息;如果需要令牌则返回令牌请求信息。

    同一轮次多个独立工具默认线程并行执行以缩短总耗时;含可能首轮即
    requires_token 的写入类工具时保持串行,避免破坏「未到令牌则不应执行
    后续工具」的语义。
    """
    if not tool_calls:
        return None

    if execute_tool is None:
        execute_tool = _resolve_chat_execute_tool()

    parsed: list[tuple[Any, str, str, str]] = []
    for tc in tool_calls:
        fn = getattr(tc, "function", None)
        name = str(getattr(fn, "name", "") or "").strip()
        raw_args = str(getattr(fn, "arguments", "") or "")
        try:
            args_dict = json.loads(raw_args) if raw_args.strip() else {}
            if not isinstance(args_dict, dict):
                args_dict = {}
        except json.JSONDecodeError:
            args_dict = {}
        if name in ("excel_analysis", "excel_schema_understand"):
            args_dict = enrich_excel_tool_arguments(name, args_dict, runtime_context)
        raw_eff = json.dumps(args_dict, ensure_ascii=False)
        key = _tool_key(name, raw_eff)
        parsed.append((tc, name, raw_eff, key))

    any_token_sensitive = any(n in _TOKEN_ORDER_SENSITIVE_TOOLS for _, n, _, _ in parsed)
    max_workers = _planner_tools_max_workers()
    use_parallel = len(parsed) > 1 and max_workers > 1 and not any_token_sensitive

    if not use_parallel:
        for tc, name, raw_eff, key in parsed:
            with _TOOL_DEDUP_LOCK:
                is_dup = key in _TOOL_DEDUP
                if not is_dup:
                    _TOOL_DEDUP.add(key)
            if is_dup:
                payload = {
                    "error": "duplicate_tool_call",
                    "hint": "same tool+arguments already executed",
                }
            else:
                payload = json.loads(
                    execute_tool(name, raw_eff, workspace_root, db_write_token=db_write_token)
                )
            if payload.get("requires_token"):
                return payload
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": str(getattr(tc, "id", "") or ""),
                    "content": json.dumps(payload, ensure_ascii=False),
                }
            )
        return None

    payloads: list[dict[str, Any] | None] = [None] * len(parsed)
    to_run: list[tuple[int, str, str]] = []

    with _TOOL_DEDUP_LOCK:
        for i, (_tc, name, raw_eff, key) in enumerate(parsed):
            if key in _TOOL_DEDUP:
                payloads[i] = {
                    "error": "duplicate_tool_call",
                    "hint": "same tool+arguments already executed",
                }
            else:
                _TOOL_DEDUP.add(key)
                to_run.append((i, name, raw_eff))

    def _execute_idx(idx: int, name: str, raw_eff: str) -> tuple[int, dict[str, Any]]:
        raw = execute_tool(name, raw_eff, workspace_root, db_write_token=db_write_token)
        return idx, json.loads(raw)

    if to_run:
        workers = min(max_workers, len(to_run))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for idx, payload in pool.map(lambda t: _execute_idx(*t), to_run):
                payloads[idx] = payload

    for i, (tc, _name, _raw_eff, _key) in enumerate(parsed):
        payload = payloads[i]
        if payload is None:
            continue
        if payload.get("requires_token"):
            return payload
        messages.append(
            {
                "role": "tool",
                "tool_call_id": str(getattr(tc, "id", "") or ""),
                "content": json.dumps(payload, ensure_ascii=False),
            }
        )
    return None


def _call_model_completion(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    client: OpenAI | None = None,
) -> str:
    if client is None:
        require_api_key()
        cli = get_openai_compatible_client()
    else:
        cli = client
    mdl = _resolve_chat_model_for_client(cli, model)
    c = cli.chat.completions.create(model=mdl, messages=messages)
    msg = c.choices[0].message
    return (msg.content or "").strip()


def chat(
    user_message: str,
    *,
    runtime_context: dict[str, Any] | None = None,
    system_prompt: str | None = None,
    workspace_root: str | None = None,
    max_iterations: int | None = None,
    db_write_token: str | None = None,
    model: str | None = None,
    client: OpenAI | None = None,
) -> Any:
    if max_iterations is None:
        max_iterations = 8
    sys = merge_system_prompt(system_prompt, runtime_context)
    messages: list[dict[str, Any]] = []
    if sys:
        messages.append({"role": "system", "content": sys})
    messages.append(
        {"role": "user", "content": build_openai_user_content(user_message, runtime_context)}
    )
    if client is None:
        require_api_key()
        cli = get_openai_compatible_client()
    else:
        cli = client
    mdl = _resolve_chat_model_for_client(cli, model)
    tools = _get_workflow_tool_registry()
    tool_outputs: list[str] = []
    for _ in range(max_iterations):
        c = cli.chat.completions.create(
            model=mdl,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
        )
        msg = c.choices[0].message
        tcs = getattr(msg, "tool_calls", None) or []
        formatted_tool_calls = None
        if tcs:
            formatted_tool_calls = [
                {
                    "id": str(getattr(tc, "id", "") or ""),
                    "type": "function",
                    "function": {
                        "name": str(getattr(getattr(tc, "function", None), "name", "") or ""),
                        "arguments": str(
                            getattr(getattr(tc, "function", None), "arguments", "") or ""
                        ),
                    },
                }
                for tc in tcs
            ]
        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": formatted_tool_calls,
            }
        )
        if tcs:
            for tc in tcs:
                fn = getattr(tc, "function", None)
                tool_name = str(getattr(fn, "name", "") or "").strip()
                if tool_name:
                    tool_outputs.append(f"[调用工具: {tool_name}]")
            token_request = append_tool_messages(
                messages,
                tcs,
                workspace_root=workspace_root,
                runtime_context=runtime_context,
                db_write_token=db_write_token,
            )
            if token_request and token_request.get("requires_token"):
                return json.dumps(
                    {
                        "requires_token": True,
                        "token_name": token_request.get("token_name"),
                        "token_description": token_request.get("token_description"),
                        "message": token_request.get("message"),
                        "tool_outputs": tool_outputs,
                    },
                    ensure_ascii=False,
                )
            continue
        result = str(msg.content or "").strip()
        full_response = result
        if tool_outputs:
            full_response = "\n".join(tool_outputs) + "\n\n" + result
        return {
            "response": full_response,
            "thinking_steps": "\n".join(tool_outputs) if tool_outputs else None,
            "text": result,
        }
    return {
        "response": "对话达到最大迭代次数，未完成。",
        "thinking_steps": None,
        "text": "对话达到最大迭代次数，未完成。",
    }


def chat_stream_text(
    user_message: str,
    *,
    runtime_context: dict[str, Any] | None = None,
    system_prompt: str | None = None,
    workspace_root: str | None = None,
    max_iterations: int | None = None,
    db_write_token: str | None = None,
    model: str | None = None,
    client: OpenAI | None = None,
) -> Iterable[str | dict[str, Any]]:
    if max_iterations is None:
        max_iterations = 8
    sys = merge_system_prompt(system_prompt, runtime_context)
    messages: list[dict[str, Any]] = []
    if sys:
        messages.append({"role": "system", "content": sys})
    messages.append(
        {"role": "user", "content": build_openai_user_content(user_message, runtime_context)}
    )
    if client is None:
        require_api_key()
        cli = get_openai_compatible_client()
    else:
        cli = client
    mdl = _resolve_chat_model_for_client(cli, model)
    tools = _get_workflow_tool_registry()
    for _ in range(max_iterations):
        stream = cli.chat.completions.create(
            model=mdl,
            messages=messages,
            stream=True,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
        )
        text_parts: list[str] = []
        tool_calls_by_idx: dict[int, Any] = {}
        finish_reason = None
        has_tool_call = False
        for chunk in stream:
            choice = chunk.choices[0]
            finish_reason = getattr(choice, "finish_reason", None)
            delta = getattr(choice, "delta", None)
            if delta is None:
                continue
            content = getattr(delta, "content", None)
            if content:
                text_parts.append(str(content))
                yield str(content)
            tc_list = getattr(delta, "tool_calls", None) or []
            for tc in tc_list:
                idx = int(getattr(tc, "index", 0) or 0)
                cur = tool_calls_by_idx.get(idx)
                if cur is None:
                    cur = {
                        "id": getattr(tc, "id", None),
                        "function": {
                            "name": getattr(getattr(tc, "function", None), "name", None),
                            "arguments": getattr(getattr(tc, "function", None), "arguments", "")
                            or "",
                        },
                    }
                    tool_calls_by_idx[idx] = cur
                else:
                    fn = getattr(tc, "function", None)
                    if getattr(fn, "name", None):
                        cur["function"]["name"] = fn.name
                    cur["function"]["arguments"] += str(getattr(fn, "arguments", "") or "")
                has_tool_call = True
        if has_tool_call and tool_calls_by_idx:
            for v in tool_calls_by_idx.values():
                tool_name = str(v.get("function", {}).get("name", "") or "")
                raw_args = str(v.get("function", {}).get("arguments") or "")
                if tool_name:
                    label = _tool_stream_call_label(tool_name, raw_args)
                    yield f"\n[正在调用工具: {label}]\n"
                    # 这些工具会同步跑 LLM / 读写大文件，期间不再向 SSE 吐 token，前端易误以为卡住
                    slow = _slow_tool_wait_message(tool_name, raw_args)
                    if slow:
                        yield slow
        if finish_reason == "tool_calls" or tool_calls_by_idx:

            class _Fn:
                def __init__(self, name: str, arguments: str) -> None:
                    self.name = name
                    self.arguments = arguments

            class _Tc:
                def __init__(self, tc_id: str, name: str, arguments: str) -> None:
                    self.id = tc_id
                    self.function = _Fn(name, arguments)

            tcs = []
            for v in tool_calls_by_idx.values():
                tcs.append(
                    _Tc(
                        v.get("id") or "",
                        v.get("function", {}).get("name") or "",
                        v.get("function", {}).get("arguments") or "",
                    )
                )
            formatted_tool_calls = [
                {
                    "id": t.id,
                    "type": "function",
                    "function": {"name": t.function.name, "arguments": t.function.arguments},
                }
                for t in tcs
            ]
            messages.append(
                {"role": "assistant", "content": "", "tool_calls": formatted_tool_calls}
            )
            token_request = append_tool_messages(
                messages,
                tcs,
                workspace_root=workspace_root,
                runtime_context=runtime_context,
                db_write_token=db_write_token,
            )
            if token_request and token_request.get("requires_token"):
                yield {
                    "_planner_sse": "requires_token",
                    "token_name": token_request.get("token_name") or "DB_WRITE_TOKEN",
                    "token_description": token_request.get("token_description")
                    or token_request.get("message")
                    or "数据库写入授权令牌",
                    "message": token_request.get("message"),
                }
                return
            n_tail = len(tcs)
            tool_payloads: list[dict[str, Any]] = []
            if n_tail:
                collected: list[dict[str, Any]] = []
                for j in range(len(messages) - 1, -1, -1):
                    m = messages[j]
                    if m.get("role") != "tool":
                        break
                    try:
                        collected.append(json.loads(str(m.get("content") or "{}")))
                    except json.JSONDecodeError:
                        collected.append({})
                    if len(collected) >= n_tail:
                        break
                collected.reverse()
                tool_payloads = collected
                while len(tool_payloads) < n_tail:
                    tool_payloads.append({})
            yield _post_tool_round_hint(tcs, tool_payloads)
            continue
        if text_parts:
            return
    return


def chat_stream_sse_events(
    user_message: str,
    *,
    runtime_context: dict[str, Any] | None = None,
    system_prompt: str | None = None,
    workspace_root: str | None = None,
    max_iterations: int | None = None,
    db_write_token: str | None = None,
    model: str | None = None,
    client: OpenAI | None = None,
):
    for item in chat_stream_text(
        user_message,
        runtime_context=runtime_context,
        system_prompt=system_prompt,
        workspace_root=workspace_root,
        max_iterations=max_iterations,
        db_write_token=db_write_token,
        model=model,
        client=client,
    ):
        if isinstance(item, dict) and item.get("_planner_sse") == "requires_token":
            td = str(
                item.get("token_description") or item.get("message") or "数据库写入授权令牌"
            ).strip()
            tn = str(item.get("token_name") or "DB_WRITE_TOKEN").strip()
            yield {"type": "token", "text": f"\n[需要授权: {td}]\n"}
            yield {"type": "requires_token", "token_name": tn, "token_description": td}
            return
        yield {"type": "token", "text": str(item)}
    yield {"type": "done"}


__all__ = [
    "reset_planner_tool_dedup_state",
    "append_tool_messages",
    "chat",
    "chat_stream_text",
    "chat_stream_sse_events",
]
