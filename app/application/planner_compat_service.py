# -*- coding: utf-8 -*-
"""Planner 兼容对话服务（3d）：供宿主 /api/ai/* 与 Mod facade 共用。"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from fastapi import HTTPException, Request

from app.application.workflow.legacy_chat_adapter import chat as run_agent_chat
from app.domain.ai.tier import (
    assert_p2_elevated_claim_or_raise,
    resolve_ai_tier,
    runtime_context_with_tier,
)
from app.domain.context.session_context import (
    planner_workflow_interrupt_reply,
    runtime_context_after_workflow_interrupt,
)
from app.fastapi_routes.xcagi_compat_chat_helpers import (
    XcagiCompatChatBatchBody,
    XcagiCompatChatBody,
    _ensure_chat_db_read_authorized,
    _ensure_vector_index_if_needed,
    _merge_runtime_context_with_message_paths,
    _message_requires_db_read_token,
    _xcagi_chat_http_exc,
    _xcagi_chat_timeout_error_payload,
    _xcagi_chat_timeout_seconds,
    _xcagi_compat_reply_payload,
    _xcagi_planner_stream_bytes_async,
)
from app.infrastructure.llm.client import set_mode as set_llm_mode
from app.services.conversation.modstore_adapter import create_modstore_openai_client_from_request

logger = logging.getLogger(__name__)


async def execute_compat_chat(request: Request, body: XcagiCompatChatBody) -> dict[str, Any]:
    m = (body.mode or "").strip().lower()
    if m in ("online", "offline"):
        set_llm_mode(m)

    runtime_context, _ = _merge_runtime_context_with_message_paths(body.context, body.message)
    assert_p2_elevated_claim_or_raise(request)
    tier = resolve_ai_tier(request)
    runtime_context = runtime_context_with_tier(runtime_context, tier)
    try:
        from app.application.kitten_planner_context import (
            enrich_kitten_analyzer_runtime,
            kitten_reply_attachments,
        )

        runtime_context = await enrich_kitten_analyzer_runtime(runtime_context, body.message)
        kitten_extra = kitten_reply_attachments(runtime_context)
    except Exception:
        logger.debug("kitten planner context enrich skipped", exc_info=True)
        kitten_extra = {}
    ok_read, read_req = _ensure_chat_db_read_authorized(
        request,
        message=body.message,
        provided_token=body.db_read_token,
    )
    if not ok_read and read_req:
        return {
            "success": True,
            "requires_token": True,
            "token_name": read_req.get("token_name"),
            "token_description": read_req.get("token_description"),
            "message": read_req.get("message"),
            "response": read_req.get("message"),
            "data": {
                "requires_token": True,
                "token_name": read_req.get("token_name"),
                "token_description": read_req.get("token_description"),
            },
        }
    if ok_read and _message_requires_db_read_token(body.message):
        runtime_context["chat_db_read_authorized"] = True
    intr = planner_workflow_interrupt_reply(body.message)
    if intr is not None:
        cleared = runtime_context_after_workflow_interrupt(runtime_context)
        return _xcagi_compat_reply_payload(
            intr, runtime_context_update=cleared, kitten_attachments=kitten_extra or None
        )

    vector_error = _ensure_vector_index_if_needed(body.message, runtime_context)
    if vector_error:
        return _xcagi_compat_reply_payload(vector_error, kitten_attachments=kitten_extra or None)

    timeout = _xcagi_chat_timeout_seconds()
    try:
        workspace_root = os.environ.get("WORKSPACE_ROOT", os.getcwd())
        llm_client = create_modstore_openai_client_from_request(request)
        reply = await asyncio.wait_for(
            asyncio.to_thread(
                run_agent_chat,
                body.message,
                runtime_context=runtime_context or None,
                system_prompt=body.system_prompt,
                workspace_root=workspace_root,
                db_write_token=body.db_write_token,
                client=llm_client,
            ),
            timeout=timeout,
        )
        try:
            parsed = reply if isinstance(reply, dict) else None
            if parsed is None and isinstance(reply, str):
                parsed = json.loads(reply)
            if isinstance(parsed, dict) and parsed.get("requires_token"):
                return {
                    "success": True,
                    "requires_token": True,
                    "token_name": parsed.get("token_name"),
                    "token_description": parsed.get("token_description"),
                    "message": parsed.get("message"),
                    "response": parsed.get("message"),
                    "data": {
                        "requires_token": True,
                        "token_name": parsed.get("token_name"),
                        "token_description": parsed.get("token_description"),
                    },
                }
        except json.JSONDecodeError:
            pass
    except TimeoutError:
        return _xcagi_chat_timeout_error_payload(timeout)
    except Exception as e:
        raise _xcagi_chat_http_exc(e) from e
    return _xcagi_compat_reply_payload(reply, kitten_attachments=kitten_extra or None)


async def execute_compat_chat_batch(
    request: Request, body: XcagiCompatChatBatchBody
) -> dict[str, Any]:
    msgs = [str(x).strip() for x in (body.messages or []) if str(x).strip()]
    if not msgs:
        raise HTTPException(status_code=400, detail="messages 须为非空字符串数组")
    assert_p2_elevated_claim_or_raise(request)
    batch_tier = resolve_ai_tier(request)
    m = (body.mode or "").strip().lower()
    if m in ("online", "offline"):
        set_llm_mode(m)
    results: list[dict[str, Any]] = []
    timeout = _xcagi_chat_timeout_seconds()
    rolling_ctx = body.context
    llm_client = create_modstore_openai_client_from_request(request)
    for txt in msgs:
        runtime_context, _ = _merge_runtime_context_with_message_paths(rolling_ctx, txt)
        runtime_context = runtime_context_with_tier(runtime_context, batch_tier)
        ok_read, read_req = _ensure_chat_db_read_authorized(
            request,
            message=txt,
            provided_token=body.db_read_token,
        )
        if not ok_read and read_req:
            results.append(
                {
                    "success": True,
                    "requires_token": True,
                    "token_name": read_req.get("token_name"),
                    "token_description": read_req.get("token_description"),
                    "message": read_req.get("message"),
                    "response": read_req.get("message"),
                    "data": {
                        "requires_token": True,
                        "token_name": read_req.get("token_name"),
                        "token_description": read_req.get("token_description"),
                    },
                }
            )
            continue
        if ok_read and _message_requires_db_read_token(txt):
            runtime_context["chat_db_read_authorized"] = True
        intr = planner_workflow_interrupt_reply(txt)
        if intr is not None:
            cleared = runtime_context_after_workflow_interrupt(runtime_context)
            rolling_ctx = cleared
            results.append(_xcagi_compat_reply_payload(intr, runtime_context_update=cleared))
            continue
        vector_error = _ensure_vector_index_if_needed(txt, runtime_context)
        if vector_error:
            results.append(_xcagi_compat_reply_payload(vector_error))
            continue
        try:
            reply = await asyncio.wait_for(
                asyncio.to_thread(
                    run_agent_chat,
                    txt,
                    runtime_context=runtime_context or None,
                    system_prompt=body.system_prompt,
                    db_write_token=body.db_write_token,
                    client=llm_client,
                ),
                timeout=timeout,
            )
            results.append(_xcagi_compat_reply_payload(reply))
        except TimeoutError:
            results.append(_xcagi_chat_timeout_error_payload(timeout))
        except Exception as e:
            err = _xcagi_chat_http_exc(e)
            results.append(
                {
                    "success": False,
                    "message": err.detail if isinstance(err.detail, str) else str(err.detail),
                }
            )
    ok = all(r.get("success") for r in results)
    return {"success": ok, "batch": True, "results": results, "count": len(results)}


async def compat_chat_stream_async(
    request: Request, body: XcagiCompatChatBody, *, ai_tier: str | None = None
):
    tier = ai_tier or resolve_ai_tier(request)
    async for chunk in _xcagi_planner_stream_bytes_async(request, body, ai_tier=tier):
        yield chunk
