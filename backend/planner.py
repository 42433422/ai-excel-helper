"""
Agentic chat: repeatedly call the LLM with registered tools until a final reply.

Uses OpenAI-compatible Chat Completions (tools + tool_calls loop).

---
原则清单（对照 LangChain / LangGraph 思路，本模块自研实现，不引入框架）

消息生命周期
  - system / user / assistant / tool 角色与 OpenAI 格式一致；含 tool_calls 的 assistant
    必须在每条 tool 消息上带对应 tool_call_id。
  - 辅助函数 append_assistant_message / append_tool_messages 集中维护该结构。

终止条件（类似预置 agent 图的 END 判定）
  - 若 assistant 无 tool_calls：取 content 为最终回答（可空字符串）；结束循环。
  - 若有 tool_calls：执行工具、追加 tool 消息，继续下一轮；不得超过 max_iterations。
  - 超过 max_iterations：返回固定提示文本。

流式分层
  - 工具轮次：流式消费 API 时先聚合 delta，待 finish_reason 确定后再分支；若为 tool_calls
    不向客户端下发中间 content（避免与工具轮 UI 混淆）。
  - 仅当最终轮为纯文本（无 tool_calls）时，将 content 分片交给回调或生成器供 SSE 使用。
  - 默认 chat() 仍为非流式 API，行为与重构前一致。
"""

from __future__ import annotations

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Mapping

_last_tool_result: dict[str, Any] = {}

# 同一用户轮次内：若模型连续以完全相同参数调用 excel_analysis，则跳过重跑（省时并打断无效循环）。
_last_tool_round_signature: tuple[str, str] | None = None


def get_last_tool_result() -> dict[str, Any]:
    return _last_tool_result


def reset_planner_tool_dedup_state() -> None:
    """新的一条用户消息进入 Planner 循环时清空（由 chat / chat_stream_sse_events 开头调用）。"""
    global _last_tool_round_signature
    _last_tool_round_signature = None


def _normalized_tool_args_json(raw: str) -> str:
    try:
        return json.dumps(json.loads(raw or "{}"), sort_keys=True, ensure_ascii=False)
    except Exception:
        return (raw or "").strip()


def _tool_calls_display_suffix(assistant_dict: dict[str, Any], *, max_len: int = 160) -> str:
    """供 SSE 展示：工具名 + 截断后的 arguments 片段。"""
    tcs = assistant_dict.get("tool_calls") or []
    if not tcs:
        return ""
    parts: list[str] = []
    for tc in tcs:
        fn = tc.get("function") or {}
        name = str(fn.get("name") or "").strip() or "(未命名)"
        raw = str(fn.get("arguments") or "").strip()
        if not raw:
            parts.append(name)
            continue
        frag = raw if len(raw) <= max_len else raw[: max_len - 1] + "…"
        parts.append(f"{name} {frag}")
    return " — " + " | ".join(parts) if parts else ""


from openai import OpenAI

from backend.llm_config import get_llm_client, require_api_key, resolve_chat_model, resolve_mode
from backend.runtime_context import merge_system_prompt, planner_workflow_interrupt_reply
from backend.ai_tier import (
    P1_BLOCKED_TOOL_NAMES,
    effective_tier_from_runtime,
    filter_tools_for_tier,
    tier_denied_tool_json,
)
from backend.tools import execute_workflow_tool, flatten_tool_result_dict_for_client, get_workflow_tool_registry

logger = logging.getLogger(__name__)


def _default_max_iterations() -> int:
    """Agent 轮数上限；可用环境变量 PLANNER_MAX_ITERATIONS（1–30）覆盖。"""
    fallback = 8 if resolve_mode() == "offline" else 15
    raw = os.environ.get("PLANNER_MAX_ITERATIONS", "").strip()
    if not raw:
        return fallback
    try:
        n = int(raw)
    except ValueError:
        return fallback
    return max(1, min(n, 30))


def _parallel_tool_calls_enabled() -> bool:
    """
    同一轮 assistant 返回多条 tool_calls 时是否并行执行。
    默认：在线开启（多数网关可并行 HTTP），离线关闭（避免 Ollama 单卡争用）。
    显式设置 PLANNER_PARALLEL_TOOLS=1|0 可强制开关。
    """
    raw = os.environ.get("PLANNER_PARALLEL_TOOLS", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    return resolve_mode() != "offline"


def assistant_message_from_sdk(msg: Any) -> dict[str, Any]:
    """Build a chat message dict from an OpenAI SDK assistant message."""
    d: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
    if getattr(msg, "tool_calls", None):
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments or "{}",
                },
            }
            for tc in msg.tool_calls
        ]
    return d


def append_assistant_message(messages: list[dict[str, Any]], assistant_dict: dict[str, Any]) -> None:
    messages.append(assistant_dict)


def append_tool_messages(
    messages: list[dict[str, Any]],
    tool_calls: list[Any],
    *,
    workspace_root: str,
    db_write_token: str | None = None,
    planner_user_utterance: str | None = None,
    execute_tool: Callable[..., str] | None = None,
    ai_tier: str = "p1",
) -> None:
    """Execute each tool call and append role=tool messages. ``execute_tool`` defaults to execute_workflow_tool."""
    global _last_tool_result, _last_tool_round_signature
    if execute_tool is None:

        def _default_run(name: str, raw: str, root: str | None) -> str:
            if (ai_tier or "p1").lower() != "p2" and name in P1_BLOCKED_TOOL_NAMES:
                return tier_denied_tool_json(name)
            return execute_workflow_tool(
                name,
                raw,
                workspace_root=root,
                db_write_token=db_write_token,
                planner_user_utterance=planner_user_utterance,
            )

        run = _default_run
    else:
        run = execute_tool

    n_tools = len(tool_calls)

    def _one_content(tc: Any) -> str:
        global _last_tool_round_signature
        name = tc.function.name
        raw_args = tc.function.arguments or "{}"
        if n_tools == 1 and name == "excel_analysis":
            sig = _normalized_tool_args_json(raw_args)
            key = (name, sig)
            if _last_tool_round_signature == key:
                logger.info("planner: skip duplicate excel_analysis (same normalized arguments)")
                return json.dumps(
                    {
                        "error": "duplicate_tool_call",
                        "tool": name,
                        "hint": (
                            "你已连续使用完全相同的参数调用 excel_analysis，本轮未重复执行。"
                            "请阅读上一条 role=tool 的 JSON 结果；改换不同 action（如 aggregate/query）、"
                            "调用 products_bulk_import，或直接输出对用户的中文最终回答。"
                            "不要再次使用相同参数调用本工具。"
                        ),
                    },
                    ensure_ascii=False,
                )
            try:
                content = run(name, raw_args, workspace_root)
            except Exception as e:
                logger.exception("tool execution failed: %s", name)
                return json.dumps(
                    {"error": "tool_execution_exception", "message": str(e)},
                    ensure_ascii=False,
                )
            _last_tool_round_signature = key
            return content

        try:
            content = run(name, raw_args, workspace_root)
        except Exception as e:
            logger.exception("tool execution failed: %s", name)
            return json.dumps(
                {"error": "tool_execution_exception", "message": str(e)},
                ensure_ascii=False,
            )
        if n_tools == 1:
            _last_tool_round_signature = (name, _normalized_tool_args_json(raw_args))
        return content

    def _record_last_tool(name: str, content: str) -> None:
        global _last_tool_result
        try:
            parsed = json.loads(content) if isinstance(content, str) else content
            if isinstance(parsed, dict) and parsed.get("error") != "duplicate_tool_call":
                _last_tool_result = {"tool_key": name, **parsed}
        except (json.JSONDecodeError, TypeError):
            pass

    if len(tool_calls) > 1 and _parallel_tool_calls_enabled():
        max_workers = min(8, len(tool_calls))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            contents = list(pool.map(_one_content, tool_calls))
        for tc, content in zip(tool_calls, contents):
            _record_last_tool(tc.function.name, content)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": content,
                }
            )
        _last_tool_round_signature = None
        return

    for tc in tool_calls:
        content = _one_content(tc)
        _record_last_tool(tc.function.name, content)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": content,
            }
        )


def _tool_names_from_assistant_dict(assistant_dict: dict[str, Any]) -> list[str]:
    tcs = assistant_dict.get("tool_calls") or []
    out: list[str] = []
    for tc in tcs:
        fn = tc.get("function") or {}
        n = fn.get("name")
        if n:
            out.append(n)
    return out


def _call_model_completion(
    cli: OpenAI,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> Any:
    """Single non-streaming chat completion; returns SDK chat completion object."""
    return cli.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )


def _assistant_dict_from_stream_accumulation(
    *,
    content: str,
    tool_calls_by_index: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Build OpenAI-shaped assistant message dict from streamed accumulation."""
    d: dict[str, Any] = {"role": "assistant", "content": content}
    if not tool_calls_by_index:
        return d
    ordered = [tool_calls_by_index[i] for i in sorted(tool_calls_by_index.keys())]
    d["tool_calls"] = [
        {
            "id": tc["id"],
            "type": "function",
            "function": {"name": tc["name"], "arguments": tc["arguments"]},
        }
        for tc in ordered
    ]
    return d


def _consume_chat_stream(
    stream: Any,
) -> tuple[dict[str, Any], str | None, list[str]]:
    """
    Consume a chat completion stream; return (assistant_message_dict, finish_reason, content_parts).
    Buffers tool call fragments by index until the stream ends.
    ``content_parts`` preserves stream order for SSE chunk replay when the turn is text-only.
    """
    content_parts: list[str] = []
    tool_calls_by_index: dict[int, dict[str, Any]] = {}
    finish_reason: str | None = None

    for chunk in stream:
        if not chunk.choices:
            continue
        ch0 = chunk.choices[0]
        if ch0.finish_reason:
            finish_reason = ch0.finish_reason
        delta = ch0.delta
        if getattr(delta, "content", None):
            content_parts.append(delta.content or "")
        if getattr(delta, "tool_calls", None):
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in tool_calls_by_index:
                    tool_calls_by_index[idx] = {"id": "", "name": "", "arguments": ""}
                if tc.id:
                    tool_calls_by_index[idx]["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        tool_calls_by_index[idx]["name"] = tc.function.name
                    if tc.function.arguments:
                        tool_calls_by_index[idx]["arguments"] += tc.function.arguments

    content = "".join(content_parts)
    assistant_dict = _assistant_dict_from_stream_accumulation(
        content=content,
        tool_calls_by_index=tool_calls_by_index,
    )
    return assistant_dict, finish_reason, content_parts


def _call_model_stream(
    cli: OpenAI,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> Any:
    return cli.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        stream=True,
    )


def _log_turn(
    iteration: int,
    model: str,
    t0: float,
    *,
    mode: str,
    finish_reason: str | None,
    tool_names: list[str] | None,
) -> None:
    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    logger.info(
        "planner_turn iteration=%s model=%s duration_ms=%s mode=%s finish_reason=%s tools=%s",
        iteration,
        model,
        duration_ms,
        mode,
        finish_reason,
        tool_names,
    )


@dataclass
class _LoopState:
    messages: list[dict[str, Any]] = field(default_factory=list)
    workspace_root: str = ""
    db_write_token: str | None = None
    planner_user_utterance: str = ""
    ai_tier: str = "p1"

    def append_tools_from_assistant_dict(self, assistant_dict: dict[str, Any]) -> None:
        tcs = assistant_dict.get("tool_calls")
        if not tcs:
            return

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

        mocks = []
        for tc in tcs:
            fn = tc.get("function") or {}
            mocks.append(_Tc(tc.get("id", ""), fn.get("name", ""), fn.get("arguments") or "{}"))
        append_tool_messages(
            self.messages,
            mocks,
            workspace_root=self.workspace_root,
            db_write_token=self.db_write_token,
            planner_user_utterance=self.planner_user_utterance or None,
            ai_tier=self.ai_tier,
        )


def chat(
    user_message: str,
    *,
    workspace_root: str | None = None,
    max_iterations: int | None = None,
    system_prompt: str | None = None,
    runtime_context: dict[str, Any] | None = None,
    db_write_token: str | None = None,
    model: str | None = None,
    client: OpenAI | None = None,
    messages_out: list[dict[str, Any]] | None = None,
) -> str:
    """
    Run an agentic tool loop: LLM may call workflow tools until it responds without tool_calls.

    runtime_context:
      上传 Excel 后由接口填入，例如 {"excel_file_path": "uploads/xxx.xlsx"}（相对 WORKSPACE_ROOT），
      会并入 system，使模型知道应使用的 file_path。

    db_write_token:
      与服务器 ``FHD_DB_WRITE_TOKEN`` 一致时，Planner 可执行 ``products_bulk_import`` 工具写入 PostgreSQL。

    Environment:
      DP_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY — 任选一个
      DP_BASE_URL / DEEPSEEK_BASE_URL / OPENAI_BASE_URL — 可选；仅配 DP/DeepSeek key 时默认 https://api.deepseek.com
      DP_MODEL / DEEPSEEK_MODEL / LLM_MODEL — 可选（DeepSeek 网关默认 deepseek-chat）
      WORKSPACE_ROOT — excel 沙箱根目录
      PLANNER_MAX_ITERATIONS — 可选，1–30，限制 agent 最大轮数（默认在线 15 / 离线 8）
      PLANNER_PARALLEL_TOOLS — 可选 1/0，强制开/关「同一轮多条 tool 并行执行」
    """
    global _last_tool_result

    intr = planner_workflow_interrupt_reply(user_message)
    if intr is not None:
        _last_tool_result = {}
        reset_planner_tool_dedup_state()
        return intr

    if client is None:
        require_api_key()
        cli = get_llm_client()
    else:
        cli = client
    mdl = model or resolve_chat_model()
    tier = effective_tier_from_runtime(runtime_context)
    tools = filter_tools_for_tier(get_workflow_tool_registry(), tier)

    logger.info("planner chat start mode=%s model=%s", resolve_mode(), mdl)

    if max_iterations is None:
        max_iterations = _default_max_iterations()

    _last_tool_result = {}
    reset_planner_tool_dedup_state()

    try:
        from backend.sales_contract_intent_bridge import set_planner_contract_user_utterance

        set_planner_contract_user_utterance(user_message)
    except Exception:
        pass

    combined_system = merge_system_prompt(system_prompt, runtime_context)
    messages: list[dict[str, Any]] = []
    if combined_system:
        messages.append({"role": "system", "content": combined_system})
    messages.append({"role": "user", "content": user_message})

    root = workspace_root or os.environ.get("WORKSPACE_ROOT") or os.getcwd()

    try:
        for iteration in range(max_iterations):
            t0 = time.perf_counter()
            logger.debug("planner iteration %s", iteration + 1)
            completion = _call_model_completion(cli, mdl, messages, tools)
            choice = completion.choices[0]
            msg = choice.message

            if messages_out is not None:
                messages_out.append(assistant_message_from_sdk(msg))

            finish = getattr(choice, "finish_reason", None)
            ad = assistant_message_from_sdk(msg)
            names = _tool_names_from_assistant_dict(ad) if msg.tool_calls else None
            _log_turn(iteration + 1, mdl, t0, mode="non_stream", finish_reason=finish, tool_names=names)

            if msg.tool_calls:
                append_assistant_message(messages, ad)
                append_tool_messages(
                    messages,
                    msg.tool_calls,
                    workspace_root=root,
                    db_write_token=db_write_token,
                    planner_user_utterance=user_message,
                    ai_tier=tier,
                )
                continue

            text = (msg.content or "").strip()
            if text:
                return text
            logger.warning(
                "planner iteration %s returned empty content, finish_reason=%s, remaining_iterations=%s",
                iteration + 1,
                finish,
                max_iterations - iteration - 1,
            )
            if iteration < max_iterations - 1:
                continue
            return "抱歉，暂时无法生成回复，请稍后重试。"

        return f"[planner stopped after {max_iterations} iterations without a final answer]"
    finally:
        try:
            from backend.sales_contract_intent_bridge import set_planner_contract_user_utterance

            set_planner_contract_user_utterance(None)
        except Exception:
            pass


def chat_stream_sse_events(
    user_message: str,
    *,
    workspace_root: str | None = None,
    max_iterations: int | None = None,
    system_prompt: str | None = None,
    runtime_context: Mapping[str, Any] | None = None,
    db_write_token: str | None = None,
    model: str | None = None,
    client: OpenAI | None = None,
) -> Iterator[dict[str, Any]]:
    """
    与 ``chat_stream_text`` 同一 agent 循环，产出结构化事件供 SSE：
    ``phase`` / ``tool_calls`` / ``tool_done`` / ``token``（仅最终轮正文分片）。
    """
    global _last_tool_result

    intr = planner_workflow_interrupt_reply(user_message)
    if intr is not None:
        _last_tool_result = {}
        reset_planner_tool_dedup_state()
        yield {"type": "phase", "phase": "answer", "iteration": 1, "message": "正在生成回复…"}
        yield {"type": "token", "text": intr}
        return

    if client is None:
        require_api_key()
        cli = get_llm_client()
    else:
        cli = client
    mdl = model or resolve_chat_model()
    tier = effective_tier_from_runtime(runtime_context)
    tools = filter_tools_for_tier(get_workflow_tool_registry(), tier)

    logger.info("planner chat_stream_events mode=%s model=%s", resolve_mode(), mdl)

    if max_iterations is None:
        max_iterations = _default_max_iterations()

    _last_tool_result = {}
    reset_planner_tool_dedup_state()

    try:
        from backend.sales_contract_intent_bridge import set_planner_contract_user_utterance

        set_planner_contract_user_utterance(user_message)
    except Exception:
        pass

    combined_system = merge_system_prompt(system_prompt, runtime_context)
    state = _LoopState(
        messages=[],
        workspace_root=workspace_root or os.environ.get("WORKSPACE_ROOT") or os.getcwd(),
        db_write_token=db_write_token,
        planner_user_utterance=user_message or "",
        ai_tier=tier,
    )
    if combined_system:
        state.messages.append({"role": "system", "content": combined_system})
    state.messages.append({"role": "user", "content": user_message})

    try:
        for iteration in range(max_iterations):
            it = iteration + 1
            t0 = time.perf_counter()
            yield {
                "type": "phase",
                "phase": "llm",
                "iteration": it,
                "message": f"第 {it} 轮：正在请求大模型…",
            }
            logger.debug("planner stream iteration %s", it)
            stream = _call_model_stream(cli, mdl, state.messages, tools)
            assistant_dict, finish_reason, content_parts = _consume_chat_stream(stream)
            names = _tool_names_from_assistant_dict(assistant_dict)
            _log_turn(it, mdl, t0, mode="stream", finish_reason=finish_reason, tool_names=names or None)

            if assistant_dict.get("tool_calls"):
                arg_hint = _tool_calls_display_suffix(assistant_dict)
                yield {
                    "type": "tool_calls",
                    "iteration": it,
                    "tools": names,
                    "message": (f"调用工具：{', '.join(names) if names else '(未命名)'}" + arg_hint),
                }
                append_assistant_message(state.messages, assistant_dict)
                state.append_tools_from_assistant_dict(assistant_dict)
                try:
                    last_tool = flatten_tool_result_dict_for_client(get_last_tool_result())
                except Exception:
                    last_tool = {}
                yield {
                    "type": "tool_done",
                    "iteration": it,
                    "tools": names,
                    "message": (f"工具执行完成：{', '.join(names) if names else '—'}" + arg_hint),
                    "last_tool": last_tool,
                }
                continue

            if not "".join(content_parts).strip():
                logger.warning(
                    "planner stream iteration %s returned empty content, finish_reason=%s",
                    it,
                    finish_reason,
                )
                if iteration < max_iterations - 1:
                    continue
                yield {"type": "token", "text": "抱歉，暂时无法生成回复，请稍后重试。"}
                return

            yield {"type": "phase", "phase": "answer", "iteration": it, "message": "正在生成回复…"}
            for part in content_parts:
                if part:
                    yield {"type": "token", "text": part}
            return

        yield {
            "type": "token",
            "text": f"[planner stopped after {max_iterations} iterations without a final answer]",
        }
    finally:
        try:
            from backend.sales_contract_intent_bridge import set_planner_contract_user_utterance

            set_planner_contract_user_utterance(None)
        except Exception:
            pass


def chat_stream_text(
    user_message: str,
    *,
    workspace_root: str | None = None,
    max_iterations: int | None = None,
    system_prompt: str | None = None,
    runtime_context: dict[str, Any] | None = None,
    db_write_token: str | None = None,
    model: str | None = None,
    client: OpenAI | None = None,
) -> Iterator[str]:
    """
    Same agent loop as chat(), but yields UTF-8 text fragments from the final assistant turn only.
    Tool rounds use streaming API internally with content buffered until finish_reason is known;
    no fragments are yielded during tool rounds.
    """
    for ev in chat_stream_sse_events(
        user_message,
        workspace_root=workspace_root,
        max_iterations=max_iterations,
        system_prompt=system_prompt,
        runtime_context=runtime_context,
        db_write_token=db_write_token,
        model=model,
        client=client,
    ):
        if ev.get("type") == "token" and ev.get("text"):
            yield str(ev["text"])
