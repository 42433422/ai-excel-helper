"""
XCAGI 前端兼容 API — AI 聊天辅助函数与数据模型。

供 xcagi_compat_chat / xcagi_compat_misc 等模块复用。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import queue
import re
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request
from openai import APIConnectionError, APIError, AuthenticationError, RateLimitError
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.application.workflow.legacy_chat_adapter import chat_stream_sse_events
from app.domain.ai.tier import runtime_context_with_tier
from app.domain.context.session_context import (
    planner_workflow_interrupt_reply,
    runtime_context_after_workflow_interrupt,
)
from app.infrastructure.auth.db_token import effective_db_read_token
from app.infrastructure.llm.client import set_mode as set_llm_mode
from app.services.conversation.modstore_adapter import create_modstore_openai_client_from_request

logger = logging.getLogger(__name__)

_CHAT_DB_READ_GRACE_SEC = 5 * 60
_chat_db_read_grace_lock = threading.Lock()
_chat_db_read_grace_until: dict[str, float] = {}

_CHAT_DB_READ_INTENT_RE = re.compile(
    r"(查看|查询|检索|读取|看|浏览).*(数据库|数据表|产品库|客户库)|((数据库|数据表|产品库|客户库).*(查看|查询|检索|读取|看|浏览))",
    re.IGNORECASE,
)


def _chat_request_subject(request: Request) -> str:
    xff = str(request.headers.get("x-forwarded-for") or "").strip()
    ip = xff.split(",")[0].strip() if xff else ""
    if not ip:
        client = getattr(request, "client", None)
        ip = str(getattr(client, "host", "") or "").strip()
    if not ip:
        ip = "unknown"
    ua = str(request.headers.get("user-agent") or "").strip()
    ua_fingerprint = hashlib.sha1(ua.encode("utf-8")).hexdigest()[:12] if ua else "na"
    return f"{ip}|{ua_fingerprint}"


def _chat_db_read_grace_seconds_left(request: Request) -> int:
    now = time.time()
    subject = _chat_request_subject(request)
    with _chat_db_read_grace_lock:
        until = float(_chat_db_read_grace_until.get(subject) or 0.0)
        if until <= now:
            _chat_db_read_grace_until.pop(subject, None)
            return 0
        return int(until - now)


def _touch_chat_db_read_grace(request: Request) -> int:
    now = time.time()
    subject = _chat_request_subject(request)
    until = now + _CHAT_DB_READ_GRACE_SEC
    with _chat_db_read_grace_lock:
        _chat_db_read_grace_until[subject] = until
    return _CHAT_DB_READ_GRACE_SEC


def _message_requires_db_read_token(message: str) -> bool:
    text = str(message or "").strip()
    if not text:
        return False
    return bool(_CHAT_DB_READ_INTENT_RE.search(text))


def _chat_read_token_required_payload(message: str) -> dict[str, Any]:
    _ = message
    return {
        "requires_token": True,
        "token_name": "DB_READ_TOKEN",
        "token_description": "一级数据库查看令牌（授权后 5 分钟内可复用）",
        "message": "该操作需要一级数据库查看令牌。请先完成一级令牌验证后重试。",
    }


def _ensure_chat_db_read_authorized(
    request: Request,
    *,
    message: str,
    provided_token: str | None,
) -> tuple[bool, dict[str, Any] | None]:
    expected = effective_db_read_token()
    if not expected:
        return True, None
    if not _message_requires_db_read_token(message):
        return True, None
    if _chat_db_read_grace_seconds_left(request) > 0:
        return True, None
    got = str(provided_token or "").strip()
    if got and got == expected:
        _touch_chat_db_read_grace(request)
        return True, None
    return False, _chat_read_token_required_payload(message)


class XcagiCompatChatBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("message", "user_message", "content", "text", "query"),
    )
    context: dict | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "context",
            "runtime_context",
            "session_context",
            "ddd_context",
            "neuro_context",
            "neuro_ddd_context",
        ),
    )
    system_prompt: str | None = Field(
        default=None,
        validation_alias=AliasChoices("system_prompt", "system", "instructions"),
    )
    mode: str | None = Field(
        default=None,
        validation_alias=AliasChoices("mode", "llm_mode"),
    )
    db_read_token: str | None = Field(
        default=None,
        description="与 FHD_DB_READ_TOKEN 一致时允许执行受保护的数据库查看操作（有效期 5 分钟）",
    )
    db_write_token: str | None = Field(
        default=None,
        description="与 FHD_DB_WRITE_TOKEN 一致时允许 Planner 调用 products_bulk_import",
    )


class XcagiCompatChatBatchBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    messages: list[str] = Field(default_factory=list)
    context: dict | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "context",
            "runtime_context",
            "session_context",
            "ddd_context",
            "neuro_context",
            "neuro_ddd_context",
        ),
    )
    system_prompt: str | None = Field(
        default=None,
        validation_alias=AliasChoices("system_prompt", "system", "instructions"),
    )
    mode: str | None = Field(
        default=None,
        validation_alias=AliasChoices("mode", "llm_mode"),
    )
    db_read_token: str | None = Field(default=None)
    db_write_token: str | None = Field(default=None)
    user_id: str | None = None
    source: str | None = None


def _xcagi_chat_http_exc(exc: BaseException) -> HTTPException:
    if isinstance(exc, TimeoutError):
        msg = str(exc).strip() or "大模型响应超时，请稍后重试。"
        return HTTPException(status_code=504, detail=msg)
    if isinstance(exc, AuthenticationError):
        return HTTPException(status_code=401, detail=f"大模型鉴权失败: {exc}")
    if isinstance(exc, RateLimitError):
        return HTTPException(status_code=429, detail=f"大模型限流: {exc}")
    if isinstance(exc, APIConnectionError):
        return HTTPException(status_code=503, detail=f"无法连接大模型服务: {exc}")
    if isinstance(exc, APIError):
        return HTTPException(status_code=502, detail=f"大模型接口错误: {exc}")
    if isinstance(exc, RuntimeError):
        return HTTPException(status_code=503, detail=str(exc))
    logger.exception("xcagi ai chat compat unexpected error")
    return HTTPException(status_code=500, detail=f"对话处理失败: {exc}")


def _xcagi_compat_reply_payload(
    reply: str | dict,
    *,
    runtime_context_update: dict[str, Any] | None = None,
    kitten_attachments: dict[str, Any] | None = None,
) -> dict:
    thinking_steps: str | None = None
    if isinstance(reply, dict):
        thinking_steps = reply.get("thinking_steps")
        text = str(reply.get("response") or reply.get("text") or "")
    else:
        text = str(reply or "")

    tool_data: dict = {}
    last_result: dict = {}
    try:
        from app.application.workflow.legacy_chat_adapter import get_last_tool_result

        raw = get_last_tool_result()
        if isinstance(raw, dict) and raw:
            last_result = raw
            from app.application.tools import flatten_tool_result_dict_for_client

            tool_data = flatten_tool_result_dict_for_client(raw)
            errs = raw.get("errors")
            if isinstance(errs, list) and errs:
                preview = errs[:5]
                joined = "; ".join(str(x) for x in preview if x is not None)
                tool_data["errors_preview"] = joined[:2000]
                if len(errs) > 5:
                    tool_data["errors_truncated"] = True
    except Exception:
        logger.debug("compat: last tool result unavailable", exc_info=True)

    err_code = str(last_result.get("error") or "").strip()
    err_msg = str(last_result.get("message") or "").strip()
    tool_key = str(last_result.get("tool_key") or "").strip()
    if err_code or (last_result.get("success") is False):
        notice_lines = ["---", "**工具反馈**（最近一次）"]
        if tool_key:
            notice_lines.append(f"- 工具：`{tool_key}`")
        if err_code:
            notice_lines.append(f"- 错误码：`{err_code}`")
        if err_msg:
            notice_lines.append(f"- 说明：{err_msg}")
        ep = tool_data.get("errors_preview")
        if ep:
            notice_lines.append(f"- 明细摘要：{ep}")
        notice = "\n".join(notice_lines)
        if notice not in text:
            text = f"{text.rstrip()}\n\n{notice}".strip()

    data: dict[str, Any] = {
        "response": text,
        "text": text,
        "thinking_steps": thinking_steps,
        **tool_data,
    }
    if runtime_context_update is not None:
        data["runtime_context"] = runtime_context_update
    if kitten_attachments:
        for k, v in kitten_attachments.items():
            if v is not None:
                data[k] = v

    return {"success": True, "response": text, "data": data}


_EXCEL_PATH_PATTERN = re.compile(
    r"@?([^\s'\"<>]+?\.(?:xlsx|xlsm|xls))(?=$|[\s,，。.!！?？])",
    re.IGNORECASE,
)


def _extract_excel_paths_from_message(message: str) -> list[str]:
    paths: list[str] = []
    for m in _EXCEL_PATH_PATTERN.finditer(message or ""):
        p = m.group(1).strip().strip("`\"'[](){}<>")
        if not p:
            continue
        p = p.replace("\\", "/")
        if p not in paths:
            paths.append(p)
    return paths


def _extract_excel_paths_from_context(runtime_context: dict) -> list[str]:
    paths: list[str] = []

    def _push(raw: object) -> None:
        s = str(raw or "").strip().replace("\\", "/")
        if not s:
            return
        if not re.search(r"\.(xlsx|xlsm|xls)$", s, re.IGNORECASE):
            return
        if s not in paths:
            paths.append(s)

    existing_single = runtime_context.get("excel_file_path")
    if isinstance(existing_single, str):
        _push(existing_single)
    existing_multi = runtime_context.get("excel_file_paths")
    if isinstance(existing_multi, (list, tuple)):
        for p in existing_multi:
            _push(p)
    excel_analysis = runtime_context.get("excel_analysis")
    if isinstance(excel_analysis, dict):
        _push(excel_analysis.get("file_path"))
        preview = excel_analysis.get("preview_data")
        if isinstance(preview, dict):
            _push(preview.get("file_path"))
    return paths


def _merge_runtime_context_with_message_paths(
    runtime_context: dict | None,
    message: str,
) -> tuple[dict, list[str]]:
    merged_ctx = dict(runtime_context or {})
    found = _extract_excel_paths_from_message(message)
    ctx_paths = _extract_excel_paths_from_context(merged_ctx)
    if not found and not ctx_paths:
        return merged_ctx, []
    all_paths: list[str] = []
    message_basenames = {Path(p).name.lower(): p for p in found}
    for cp in ctx_paths:
        base = Path(cp).name.lower()
        if base in message_basenames and cp not in all_paths:
            all_paths.append(cp)
    for p in found:
        if p not in all_paths:
            all_paths.append(p)
    for cp in ctx_paths:
        if cp not in all_paths:
            all_paths.append(cp)
    if all_paths:
        merged_ctx["excel_file_path"] = all_paths[0]
        merged_ctx["excel_file_paths"] = all_paths
    return merged_ctx, found


def _looks_like_vector_request(message: str) -> bool:
    text = (message or "").lower()
    keywords = ("向量", "索引", "语义检索", "embedding", "vector", "semantic search")
    return any(k in text for k in keywords)


def _ensure_vector_index_if_needed(message: str, runtime_context: dict) -> str | None:
    if not _looks_like_vector_request(message):
        return None
    file_path = str(runtime_context.get("excel_file_path") or "").strip()
    if not file_path:
        return "我识别到您在请求向量索引，但没有拿到 Excel 路径。请发送类似 `@424/26年出货单打印/鸿瑞达报价26年.xlsx` 的路径。"
    root = os.environ.get("WORKSPACE_ROOT", os.getcwd())
    try:
        from app.mod_sdk.planner_tools import resolve_planner_tool_executor

        raw = resolve_planner_tool_executor()(
            "excel_vector_index",
            {"file_path": file_path},
            workspace_root=root,
        )
        result = json.loads(raw)
    except Exception as e:
        logger.exception("xcagi vector pre-index failed")
        return f"我尝试为 `{file_path}` 建立向量索引时失败：{e}。请确认文件路径是否存在，或告诉我要索引的工作表名。"
    if isinstance(result, dict) and result.get("error"):
        msg = result.get("message") or result.get("error")
        return f"我尝试为 `{file_path}` 建立向量索引失败：{msg}。请确认路径正确，或把目标工作表名发我。"
    return None


def _xcagi_chat_timeout_seconds() -> float:
    raw = os.environ.get("XCAGI_CHAT_TIMEOUT_SEC", "120").strip()
    try:
        v = float(raw)
        return max(5.0, min(v, 600.0))
    except ValueError:
        return 120.0


def _xcagi_stream_first_token_timeout_seconds() -> float:
    raw = os.environ.get("XCAGI_CHAT_STREAM_FIRST_TOKEN_TIMEOUT_SEC", "20").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 20.0
    return max(3.0, min(value, 120.0))


def _xcagi_stream_idle_notice_seconds() -> float:
    raw = os.environ.get("XCAGI_CHAT_STREAM_IDLE_NOTICE_SEC", "12").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 12.0
    return max(5.0, min(value, 60.0))


def _xcagi_chat_timeout_error_payload(timeout: float) -> dict:
    msg = f"对话处理超时（>{int(timeout)} 秒）。可缩短问题后重试，或由管理员调大环境变量 XCAGI_CHAT_TIMEOUT_SEC。"
    return {
        "success": False,
        "message": msg,
        "response": msg,
        "data": {"text": msg, "response": msg},
    }


def _xcagi_guarded_planner_stream_events(
    body: XcagiCompatChatBody,
    *,
    runtime_context: dict[str, Any] | None,
    workspace_root: str,
    client: Any,
):
    event_queue: queue.Queue[Any] = queue.Queue()
    done_marker = object()

    def _worker() -> None:
        try:
            for ev in chat_stream_sse_events(
                body.message,
                runtime_context=runtime_context or None,
                system_prompt=body.system_prompt,
                workspace_root=workspace_root,
                db_write_token=body.db_write_token,
                client=client,
            ):
                event_queue.put(ev)
        except BaseException as exc:  # noqa: BLE001
            event_queue.put(exc)
        finally:
            event_queue.put(done_marker)

    threading.Thread(target=_worker, daemon=True, name="xcagi-chat-stream-guard").start()

    total_timeout = _xcagi_chat_timeout_seconds()
    first_token_timeout = min(_xcagi_stream_first_token_timeout_seconds(), total_timeout)
    idle_notice_seconds = _xcagi_stream_idle_notice_seconds()
    started_at = time.monotonic()
    first_event_seen = False

    while True:
        elapsed = time.monotonic() - started_at
        if elapsed >= total_timeout:
            raise TimeoutError(
                f"流式对话总超时（>{int(total_timeout)} 秒）。请稍后重试，或缩短问题范围。"
            )

        wait_timeout = first_token_timeout if not first_event_seen else idle_notice_seconds
        wait_timeout = max(0.2, min(wait_timeout, total_timeout - elapsed))
        try:
            item = event_queue.get(timeout=wait_timeout)
        except queue.Empty:
            elapsed_int = int(time.monotonic() - started_at)
            if not first_event_seen:
                raise TimeoutError(
                    f"流式对话首包超时（>{int(first_token_timeout)} 秒）。模型服务暂未返回首个分片，请稍后重试。"
                )
            yield {
                "type": "token",
                "text": f"\n（仍在处理中，已等待 {elapsed_int} 秒，请稍候…）\n",
                "ephemeral": True,
            }
            continue

        if item is done_marker:
            return
        if isinstance(item, BaseException):
            raise item

        first_event_seen = True
        yield item


def _sse_event_line(payload: dict) -> bytes:
    return ("data: " + json.dumps(payload, ensure_ascii=False) + "\n\n").encode("utf-8")


def _thinking_steps_from_planner_stream_text(merged: str) -> str | None:
    if not (merged or "").strip():
        return None
    lines: list[str] = []
    for m in re.finditer(r"\[正在调用工具:[^\]\n]+\]", merged):
        s = m.group(0).strip()
        if s and s not in lines:
            lines.append(s)
    for m in re.finditer(r"\[工具已返回[^\]\n]*\]|\[工具未成功[^\]\n]*\]", merged):
        s = m.group(0).strip()
        if s and s not in lines:
            lines.append(s)
    for m in re.finditer(r"\[需要授权:[^\]\n]+\]|\[请提供令牌:[^\]\n]+\]", merged):
        s = m.group(0).strip()
        if s and s not in lines:
            lines.append(s)
    if not lines:
        return None
    return "\n".join(lines)


async def _xcagi_planner_stream_bytes_async(
    request: Request, body: XcagiCompatChatBody, *, ai_tier: str
):
    """Async generator wrapper around _xcagi_planner_stream_bytes.

    Runs the sync generator in a background thread and feeds items through an
    asyncio.Queue so the event loop is NEVER blocked.  This avoids the
    Starlette BaseHTTPMiddleware / anyio thread-pool deadlock that occurs when
    a sync StreamingResponse generator is iterated via iterate_in_threadpool
    while the middleware task-group is still open.
    """
    _SENTINEL = object()
    async_q: asyncio.Queue = asyncio.Queue(maxsize=128)
    loop = asyncio.get_running_loop()

    def _feed_queue() -> None:
        try:
            for chunk in _xcagi_planner_stream_bytes(request, body, ai_tier=ai_tier):
                asyncio.run_coroutine_threadsafe(async_q.put(chunk), loop).result(timeout=120)
        except Exception as exc:
            asyncio.run_coroutine_threadsafe(async_q.put(exc), loop).result(timeout=5)
        finally:
            asyncio.run_coroutine_threadsafe(async_q.put(_SENTINEL), loop).result(timeout=5)

    thread = threading.Thread(target=_feed_queue, daemon=True, name="xcagi-stream-async-bridge")
    thread.start()

    while True:
        item = await async_q.get()
        if item is _SENTINEL:
            break
        if isinstance(item, BaseException):
            raise item
        yield item


def _xcagi_planner_stream_bytes(request: Request, body: XcagiCompatChatBody, *, ai_tier: str):
    m = (body.mode or "").strip().lower()
    if m in ("online", "offline"):
        set_llm_mode(m)
    runtime_context, _ = _merge_runtime_context_with_message_paths(body.context, body.message)
    runtime_context = runtime_context_with_tier(runtime_context, ai_tier)
    ok_read, read_req = _ensure_chat_db_read_authorized(
        request,
        message=body.message,
        provided_token=body.db_read_token,
    )
    if not ok_read and read_req:
        yield _sse_event_line(
            {"type": "token", "text": f"[需要授权: {read_req.get('token_description')}]"}
        )
        yield _sse_event_line(
            {
                "type": "requires_token",
                "token_name": read_req.get("token_name"),
                "token_description": read_req.get("token_description"),
            }
        )
        return
    if ok_read and _message_requires_db_read_token(body.message):
        runtime_context["chat_db_read_authorized"] = True
    intr = planner_workflow_interrupt_reply(body.message)
    if intr is not None:
        cleared = runtime_context_after_workflow_interrupt(runtime_context)
        yield _sse_event_line({"type": "token", "text": intr})
        yield _sse_event_line(
            {
                "type": "done",
                "result": _xcagi_compat_reply_payload(intr, runtime_context_update=cleared),
            }
        )
        return
    vector_error = _ensure_vector_index_if_needed(body.message, runtime_context)
    if vector_error:
        yield _sse_event_line({"type": "error", "message": vector_error})
        return
    workspace_root = os.environ.get("WORKSPACE_ROOT", os.getcwd())
    llm_client = create_modstore_openai_client_from_request(request)
    reply_parts: list[str] = []
    try:
        halted_for_write_token = False
        for ev in _xcagi_guarded_planner_stream_events(
            body,
            runtime_context=runtime_context,
            workspace_root=workspace_root,
            client=llm_client,
        ):
            et = ev.get("type")
            if et == "token":
                text = str(ev.get("text") or "")
                if not ev.get("ephemeral"):
                    reply_parts.append(text)
                yield _sse_event_line(ev)
            elif et == "requires_token":
                yield _sse_event_line(ev)
                halted_for_write_token = True
                break
            elif et == "done":
                continue
            else:
                yield _sse_event_line(ev)
        if halted_for_write_token:
            return
        merged = "".join(reply_parts)
        thinking = _thinking_steps_from_planner_stream_text(merged)
        if thinking:
            done_reply: str | dict = {"response": merged, "thinking_steps": thinking}
        else:
            done_reply = merged
        yield _sse_event_line({"type": "done", "result": _xcagi_compat_reply_payload(done_reply)})
    except Exception as e:
        exc = _xcagi_chat_http_exc(e)
        yield _sse_event_line(
            {
                "type": "error",
                "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                "status_code": exc.status_code,
            }
        )
