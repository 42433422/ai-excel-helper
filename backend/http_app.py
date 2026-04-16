"""
最小 HTTP 层：Excel 上传后返回 runtime_context，供前端在调 /api/chat 时带回。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading

# 早于可能加载 torch / sentence-transformers 的其它 backend 导入（客户 BGE、向量索引等）
from backend.torch_runtime_env import (
    apply_sentence_transformers_compat_env,
    suppress_torch_elastic_redirect_notes,
)

apply_sentence_transformers_compat_env()
suppress_torch_elastic_redirect_notes()
import time
import uuid
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
import httpx
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from starlette.types import ASGIApp

from backend.llm_config import (
    get_llm_client,
    get_offline_status,
    require_api_key,
    resolve_mode as resolve_llm_mode,
    set_mode as set_llm_mode,
)
from backend.database import (
    get_db_status,
    resolve_mode as resolve_db_mode,
    reset_test_db,
    set_mode as set_db_mode,
    switch_to_production_mode,
    switch_to_test_mode,
)
from backend.ai_tier import assert_p2_elevated_claim_or_raise, resolve_ai_tier, runtime_context_with_tier
from backend.planner import chat, chat_stream_text
from backend.runtime_context import (
    planner_workflow_interrupt_reply,
    runtime_context_after_workflow_interrupt,
)
from backend.routers import xcagi_compat_router, xcagi_shell_router
from backend.routers.ai_approval import router as ai_approval_router
from backend.routers.mod_taiyangniao_pro import router as mod_taiyangniao_pro_router
from backend.routers.mod_store import router as mod_store_router
from backend.routers.document_templates import admin_router as document_templates_admin_router
from backend.routers.document_templates import public_router as document_templates_public_router
from backend.routers.api_security import is_api_public_path
from backend.routers.print import router as print_router
from backend.routers.materials import router as materials_router
from backend.routers.products_admin import router as products_admin_router
from backend.routers.sales_contract import router as sales_contract_router
from backend.routers.price_list import router as price_list_router
from backend.routers.model_payment import router as model_payment_router
from backend.routers.fhd_ai_policy import router as fhd_ai_policy_router
from backend.routers.code_editor import router as code_editor_router
from backend.workspace import traditional_resolve_path
from backend.word_template import handle_word_template, get_word_tool_registry
from backend.template_handler import handle_template, get_template_tool_registry, detect_template_type
from backend.template_api import router as template_router
from backend.request_client_mods_ctx import (
    parse_client_mods_off_header,
    reset_request_client_mods_ui_off,
    set_request_client_mods_ui_off,
)
from backend.request_active_mod_ctx import (
    parse_active_mod_header,
    reset_request_active_mod_id,
    set_request_active_mod_id,
)
from backend.http_request_context import (
    install_log_record_request_id,
    reset_http_request_id,
    set_http_request_id,
)
from backend.http_rate_limit import check_http_rate_limit
from backend.chat_idempotency import (
    CHAT_JSON_ROUTE,
    CHAT_STREAM_ROUTE,
    IDEMPOTENCY_CONFLICT,
    fingerprint_chat,
    normalize_idempotency_key,
    store_json,
    store_stream,
    try_get_json,
    try_get_stream,
)

logger = logging.getLogger(__name__)
install_log_record_request_id()

_ALLOWED_SUFFIX = {".xlsx", ".xlsm", ".xls"}
_WORD_SUFFIX = {".docx"}
_TEMPLATE_SUFFIX = {".docx", ".xlsx", ".xlsm"}

_audit_lock = threading.Lock()


def _http_exc_from_chat_error(exc: BaseException) -> HTTPException:
    """将 Planner / LLM 异常转为明确 HTTP 状态与 detail，避免前端只看到笼统 500。"""
    # 子类须先于 APIError 判断（AuthenticationError 等均为 APIError 子类）
    if isinstance(exc, AuthenticationError):
        return HTTPException(status_code=401, detail=f"大模型鉴权失败: {exc}")
    if isinstance(exc, RateLimitError):
        return HTTPException(status_code=429, detail=f"大模型限流: {exc}")
    if isinstance(exc, APIConnectionError):
        return HTTPException(status_code=503, detail=f"无法连接大模型服务: {exc}")
    if isinstance(exc, APITimeoutError):
        return HTTPException(status_code=504, detail=f"大模型请求超时: {exc}")
    if isinstance(exc, httpx.TimeoutException):
        return HTTPException(status_code=504, detail=f"大模型请求超时: {exc}")
    if isinstance(exc, APIError):
        return HTTPException(status_code=502, detail=f"大模型接口错误: {exc}")
    if isinstance(exc, RuntimeError):
        return HTTPException(status_code=503, detail=str(exc))
    logger.exception("chat endpoint unexpected error")
    return HTTPException(status_code=500, detail=f"对话处理失败: {exc}")


def _parse_api_keys() -> frozenset[str]:
    raw = os.environ.get("FHD_API_KEYS", "").strip()
    if not raw:
        return frozenset()
    return frozenset(k.strip() for k in raw.split(",") if k.strip())


def _append_audit_line(record: dict) -> None:
    path = os.environ.get("AUDIT_LOG_PATH", "").strip()
    if not path:
        return
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with _audit_lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)


class AuditMiddleware:
    """Request ID + optional JSON Lines audit log; API key gate when FHD_API_KEYS is set."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        method = scope.get("method", "")
        t0 = time.perf_counter()
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        request_id = headers.get("x-request-id") or str(uuid.uuid4())
        ua = headers.get("user-agent", "")[:512]
        api_keys = _parse_api_keys()
        path_norm = (path.rstrip("/") or "/") if path else "/"
        _api_public = is_api_public_path(path_norm)
        if api_keys and path.startswith("/api/") and not _api_public:
            auth = headers.get("authorization", "")
            key = headers.get("x-api-key", "")
            if auth.lower().startswith("bearer "):
                key = auth[7:].strip() or key
            if key not in api_keys:
                body = json.dumps({"detail": "invalid or missing API key"}).encode("utf-8")
                host = None
                client = scope.get("client")
                if client:
                    host = client[0]
                ff = headers.get("x-forwarded-for")
                if ff:
                    host = ff.split(",")[0].strip() or host
                _append_audit_line(
                    {
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "request_id": request_id,
                        "method": method,
                        "path": path,
                        "status_code": 401,
                        "duration_ms": round((time.perf_counter() - t0) * 1000, 3),
                        "streaming": False,
                        "client_host": host,
                        "user_agent": ua,
                        "audit_note": "api_key_denied",
                    }
                )

                async def short_send(message):
                    await send(message)

                await short_send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"x-request-id", request_id.encode("ascii")),
                        ],
                    }
                )
                await short_send({"type": "http.response.body", "body": body})
                return

        off = parse_client_mods_off_header(headers)
        cm_token = set_request_client_mods_ui_off(off)
        active_mod = parse_active_mod_header(headers)
        am_token = set_request_active_mod_id(active_mod)
        rid_token = set_http_request_id(request_id)
        try:
            rl_ok, rl_retry = check_http_rate_limit(
                method=method,
                path_norm=path_norm,
                scope=scope,
                headers_lower=headers,
            )
            if not rl_ok:
                body = json.dumps({"detail": "rate limit exceeded"}).encode("utf-8")
                host = None
                client = scope.get("client")
                if client:
                    host = client[0]
                ff = headers.get("x-forwarded-for")
                if ff:
                    host = ff.split(",")[0].strip() or host
                _append_audit_line(
                    {
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "request_id": request_id,
                        "method": method,
                        "path": path,
                        "status_code": 429,
                        "duration_ms": round((time.perf_counter() - t0) * 1000, 3),
                        "streaming": False,
                        "client_host": host,
                        "user_agent": ua,
                        "audit_note": "rate_limited",
                    }
                )
                ra_hdrs: list[tuple[bytes, bytes]] = [
                    (b"content-type", b"application/json"),
                    (b"x-request-id", request_id.encode("ascii")),
                ]
                if rl_retry is not None and rl_retry > 0:
                    ra_hdrs.append((b"retry-after", str(int(rl_retry)).encode("ascii")))

                async def rl_send(message):
                    await send(message)

                await rl_send(
                    {
                        "type": "http.response.start",
                        "status": 429,
                        "headers": ra_hdrs,
                    }
                )
                await rl_send({"type": "http.response.body", "body": body})
                return

            streaming = path.rstrip("/").endswith("/stream")
            start = time.perf_counter()

            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    status = message.get("status", 0)
                    hdrs = list(message.get("headers", []))
                    if not any(n.lower() == b"x-request-id" for n, _ in hdrs):
                        hdrs.append((b"x-request-id", request_id.encode("ascii")))
                    message = {**message, "headers": hdrs}
                    duration_ms = round((time.perf_counter() - start) * 1000, 3)
                    host = None
                    client = scope.get("client")
                    if client:
                        host = client[0]
                    ff = headers.get("x-forwarded-for")
                    if ff:
                        host = ff.split(",")[0].strip() or host
                    _append_audit_line(
                        {
                            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "request_id": request_id,
                            "method": method,
                            "path": path,
                            "status_code": status,
                            "duration_ms": duration_ms,
                            "streaming": streaming,
                            "client_host": host,
                            "user_agent": ua,
                        }
                    )
                await send(message)

            await self.app(scope, receive, send_wrapper)
        finally:
            reset_http_request_id(rid_token)
            reset_request_active_mod_id(am_token)
            reset_request_client_mods_ui_off(cm_token)


app = FastAPI(title="FHD Backend", version="0.1.0")
app.add_middleware(AuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(xcagi_shell_router, prefix="/api")
app.include_router(mod_taiyangniao_pro_router, prefix="/api")
app.include_router(ai_approval_router, prefix="/api")
app.include_router(materials_router, prefix="/api")
app.include_router(products_admin_router, prefix="/api")
app.include_router(document_templates_admin_router)
app.include_router(document_templates_public_router)
app.include_router(xcagi_compat_router, prefix="/api")
app.include_router(mod_store_router, prefix="/api/mod-store")
app.include_router(print_router, prefix="/api/print")
app.include_router(template_router)
app.include_router(sales_contract_router)
app.include_router(price_list_router)
app.include_router(model_payment_router)
app.include_router(fhd_ai_policy_router, prefix="/api/fhd")
app.include_router(code_editor_router)


class ChatRequest(BaseModel):
    """
    与 Planner 对话请求体。除标准字段外，兼容自旧版 DDD/会话客户端迁移的 JSON 键名
    （如 content / context / neuro_context），避免前后端重构后请求体对不齐。
    """

    model_config = ConfigDict(extra="ignore")

    message: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("message", "user_message", "content", "text", "query"),
    )
    runtime_context: dict | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "runtime_context",
            "context",
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
        description="覆盖全局模式: online 或 offline",
        validation_alias=AliasChoices("mode", "llm_mode"),
    )
    db_write_token: str | None = Field(
        default=None,
        description="与服务器 FHD_DB_WRITE_TOKEN 一致时，允许 Planner 调用 products_bulk_import 写入数据库",
    )


@app.get("/api/health")
async def api_health() -> dict:
    """Liveness/readiness for probes and load-test baselines."""
    return {"status": "ok"}


@app.get("/api/fhd/db-tokens/status")
async def api_fhd_db_tokens_status() -> dict:
    """是否已配置只读/写入令牌（不返回密钥明文）。"""
    from backend.db_read_auth import configured_db_read_token
    from backend.db_write_auth import configured_db_write_token

    return {
        "read_token_configured": bool(configured_db_read_token()),
        "write_token_configured": bool(configured_db_write_token()),
    }


@app.get("/api/fhd/identity")
async def api_fhd_identity() -> dict:
    """
    辨认当前 8000 进程是否为本仓库的 backend.http_app（若此地址 404，说明跑的不是 FHD 后端或未重启）。
    """
    return {
        "backend": "fhd-http-app",
        "xcagi_compat": True,
        "routers": [
            "backend.routers.xcagi_shell",
            "backend.routers.xcagi_mods",
            "backend.routers.xcagi_traditional",
            "backend.routers.xcagi_compat",
        ],
        "endpoints": {
            "db_tokens_status": "GET /api/fhd/db-tokens/status",
            "ai_tier_status": "GET /api/fhd/ai-tier/status",
            "ai_models_public": "GET /api/fhd/ai/models",
            "code_editor_status": "GET /api/code-editor/status",
            "code_editor_analyze": "POST /api/code-editor/analyze（占位）",
            "code_editor_edit": "POST /api/code-editor/edit（占位）",
            "code_editor_diff": "GET /api/code-editor/diff/{id}（占位）",
            "code_editor_apply": "POST /api/code-editor/apply/{id}（占位）",
            "mods_list": "GET /api/mods",
            "client_mods_off": "POST /api/state/client-mods-off",
            "mods_loading_status": "GET /api/mods/loading-status",
            "startup_status": "GET /api/startup/status",
            "mods_routes": "GET /api/mods/routes",
            "mod_agent_status": "GET /api/mods/{project_id}/{agent_name}/status",
            "shipment_records_units": "GET /api/shipment/shipment-records/units",
            "traditional_list": "GET /api/traditional-mode/list",
            "traditional_watch": "GET /api/traditional-mode/watch",
            "system_industries": "GET /api/system/industries",
            "system_industry": "GET|POST /api/system/industry",
            "products_list": "GET /api/products/list",
            "products_resolve_name_hints": "POST /api/products/resolve-name-hints（品名→型号，一级读锁）",
            "products_export_docx": "GET /api/products/export.docx",
            "products_price_list_export": "GET /api/products/price-list-export",
            "products_price_list_template_preview": "GET /api/products/price-list-template-preview",
            "products_bulk_import": "POST /api/admin/products/bulk-import（需 X-FHD-Db-Write-Token）",
            "products_units": "GET /api/products/units",
            "products_write": "POST /api/products/add|update|delete|batch-delete",
            "sales_contract_templates": "GET /api/sales-contract/templates（兼容，同源 PG）",
            "document_templates": "GET /api/document-templates",
            "document_templates_admin": "POST /api/admin/document-templates（需 X-FHD-Db-Write-Token）",
            "templates_list": "GET /api/templates 或 GET /api/templates/list（模板预览，PG document_templates excel_export）",
            "wechat_work_mode_feed": "GET /api/wechat_contacts/work_mode_feed",
            "conversations_get": "GET /api/conversations/{id}",
            "conversations_message": "POST /api/conversations/message",
            "conversations_sessions": "GET /api/conversations/sessions",
            "ai_chat_compat": "POST /api/ai/chat|/api/ai/chat/v2|/api/ai/unified_chat",
            "ai_unified_chat_stream": "POST /api/ai/unified_chat/stream|/api/ai/chat/stream（Planner SSE；若 404 请重启本仓库 http_app）",
            "ai_chat_batch_compat": "POST /api/ai/chat/batch|/api/ai/chat/v2/batch|/api/ai/unified_chat/batch",
            "tts_synthesize_stub": "POST /api/tts/synthesize",
            "purchase_units": "GET /api/purchase_units",
            "customers": "GET /api/customers",
            "customers_list": "GET /api/customers/list",
            "preferences": "GET|POST /api/preferences",
            "test_db_status": "GET /api/system/test-db/status",
            "test_db_enable": "POST /api/system/test-db/enable",
            "distillation_versions": "GET /api/distillation/versions",
            "intent_packages": "GET /api/intent-packages",
        },
    }


class ModeSwitchRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mode: str = Field(
        ...,
        description="online 或 offline",
        validation_alias=AliasChoices("mode", "llm_mode"),
    )
    model: str | None = Field(default=None, description="离线模式下指定模型名")


@app.get("/api/mode")
async def api_get_mode() -> dict:
    """查询当前 LLM 模式和离线状态。"""
    return {
        "mode": resolve_llm_mode(),
        "available_modes": ["online", "offline"],
        "offline_status": get_offline_status(),
    }


@app.post("/api/mode")
async def api_set_mode(body: ModeSwitchRequest) -> dict:
    """动态切换 LLM 模式（运行时生效）。"""
    if body.mode not in ("online", "offline"):
        raise HTTPException(status_code=400, detail="mode 必须为 online 或 offline")
    set_llm_mode(body.mode, body.model)
    return {"mode": body.mode, "model": body.model, "status": "ok"}


class DbModeSwitchRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mode: str = Field(
        ...,
        description="production 或 test",
        validation_alias=AliasChoices("mode", "db_mode"),
    )


@app.get("/api/db/mode")
async def api_get_db_mode() -> dict:
    """查询当前数据库模式。"""
    return get_db_status()


@app.post("/api/db/mode")
async def api_set_db_mode(body: DbModeSwitchRequest) -> dict:
    """切换数据库模式：
    - production: 使用 products.db，关闭时重置测试数据库
    - test: 使用 products_test.db（空白测试数据库）
    """
    if body.mode not in ("production", "test"):
        raise HTTPException(status_code=400, detail="mode 必须为 production 或 test")
    if body.mode == "production":
        return switch_to_production_mode()
    return switch_to_test_mode()


@app.post("/api/db/reset-test")
async def api_reset_test_db() -> dict:
    """重置测试数据库（删除并创建新的空白数据库）。"""
    return reset_test_db()


class PullModelRequest(BaseModel):
    model: str = Field(default="qwen2.5:7b", description="要下载的模型名")


@app.post("/api/ollama/pull")
async def api_pull_model(body: PullModelRequest) -> dict:
    """
    下载 Ollama 模型（同步版本，下载完成返回结果）。
    """
    from backend.offline_llm import pull_model_stream
    result = None
    error = None
    try:
        for line in pull_model_stream(body.model):
            data = json.loads(line)
            if "error" in data:
                error = data["error"]
                break
            if data.get("status") == "success":
                result = {"status": "success", "model": body.model}
                break
    except Exception as e:
        error = str(e)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return result or {"status": "success", "model": body.model}


@app.post("/api/ollama/pull/stream")
async def api_pull_model_stream(body: PullModelRequest):
    """
    流式下载 Ollama 模型，前端可通过 SSE 实时看到下载进度。
    """
    from backend.offline_llm import pull_model_stream

    async def event_generator():
        try:
            for line in pull_model_stream(body.model):
                yield f"data: {line}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@app.post("/api/upload/excel")
async def upload_excel(file: UploadFile = File(...)) -> dict:
    """
    保存到 WORKSPACE_ROOT/uploads/，返回 file_path（相对工作区）与 runtime_context。
    前端应在后续对话请求体中携带 runtime_context，使 Planner 把路径注入 LLM。
    """
    name = (file.filename or "").strip()
    suffix = Path(name).suffix.lower()
    if suffix not in _ALLOWED_SUFFIX:
        raise HTTPException(status_code=400, detail="only .xlsx .xlsm .xls allowed")

    root = Path(os.environ.get("WORKSPACE_ROOT", os.getcwd())).resolve()
    upload_dir = root / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest = upload_dir / f"{uuid.uuid4().hex}{suffix}"
    raw = await file.read()
    if len(raw) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="file too large (max 50MB)")
    dest.write_bytes(raw)

    try:
        rel = dest.relative_to(root).as_posix()
    except ValueError as e:
        raise HTTPException(status_code=500, detail="workspace path error") from e

    runtime_context = {"excel_file_path": rel}
    return {
        "file_path": rel,
        "runtime_context": runtime_context,
        # 兼容旧客户端字段名（与 Neuro-DDD / 早期前端对齐）
        "path": rel,
        "context": runtime_context,
    }


@app.post("/api/upload/word")
async def upload_word(file: UploadFile = File(...)) -> dict:
    """
    保存 Word 模板到 WORKSPACE_ROOT/uploads/，返回 file_path（相对工作区）与 runtime_context。
    """
    name = (file.filename or "").strip()
    suffix = Path(name).suffix.lower()
    if suffix not in _WORD_SUFFIX:
        raise HTTPException(status_code=400, detail="only .docx allowed")

    root = Path(os.environ.get("WORKSPACE_ROOT", os.getcwd())).resolve()
    upload_dir = root / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest = upload_dir / f"{uuid.uuid4().hex}{suffix}"
    raw = await file.read()
    if len(raw) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="file too large (max 50MB)")
    dest.write_bytes(raw)

    try:
        rel = dest.relative_to(root).as_posix()
    except ValueError as e:
        raise HTTPException(status_code=500, detail="workspace path error") from e

    runtime_context = {"word_template_path": rel}
    return {
        "file_path": rel,
        "runtime_context": runtime_context,
        "path": rel,
        "context": runtime_context,
    }


@app.post("/api/upload/template")
async def upload_template(file: UploadFile = File(...)) -> dict:
    """
    统一模板上传接口：自动识别 Word (.docx) 和 Excel (.xlsx/.xlsm) 模板，
    保存到 WORKSPACE_ROOT/uploads/，返回 file_path（相对工作区）与 runtime_context。
    """
    name = (file.filename or "").strip()
    suffix = Path(name).suffix.lower()
    if suffix not in _TEMPLATE_SUFFIX:
        raise HTTPException(status_code=400, detail=f"only {', '.join(_TEMPLATE_SUFFIX)} allowed")

    root = Path(os.environ.get("WORKSPACE_ROOT", os.getcwd())).resolve()
    upload_dir = root / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest = upload_dir / f"{uuid.uuid4().hex}{suffix}"
    raw = await file.read()
    if len(raw) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="file too large (max 50MB)")
    dest.write_bytes(raw)

    try:
        rel = dest.relative_to(root).as_posix()
    except ValueError as e:
        raise HTTPException(status_code=500, detail="workspace path error") from e

    template_type = detect_template_type(name)
    template_color = "blue" if template_type == "word" else "green" if template_type == "excel" else None
    runtime_context = {
        "template_path": rel,
        "template_type": template_type,
        "template_color": template_color,
    }

    return {
        "file_path": rel,
        "runtime_context": runtime_context,
        "path": rel,
        "context": runtime_context,
        "template_type": template_type,
        "template_color": template_color,
    }


@app.post("/api/template")
async def api_template(request: Request) -> dict:
    """
    统一模板处理接口：
    - parse: 解析模板表格结构（自动识别 Word/Excel）
    - fill: 填充模板占位符
    - export: DataFrame 导出为 Word/Excel
    - cleanup: 清理价格表数据
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON body")

    workspace_root = os.environ.get("WORKSPACE_ROOT", os.getcwd())
    result = handle_template(body, workspace_root=workspace_root)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@app.post("/api/word/template")
async def api_word_template(request: Request) -> dict:
    """
    处理 Word 模板操作（保持向后兼容）：
    - parse: 解析模板表格结构
    - fill: 填充模板占位符
    - export: DataFrame 导出为 Word
    - cleanup: 清理价格表数据
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON body")

    workspace_root = os.environ.get("WORKSPACE_ROOT", os.getcwd())
    result = handle_word_template(body, workspace_root=workspace_root)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    result["template_color"] = "blue"
    result["template_type"] = "word"
    return result


@app.post("/api/excel/template")
async def api_excel_template(request: Request) -> dict:
    """
    处理 Excel 模板操作：
    - parse: 解析模板表格结构
    - fill: 填充模板占位符
    - export: DataFrame 导出为 Excel
    - cleanup: 清理价格表数据
    """
    from backend.excel_template import handle_excel_template

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON body")

    workspace_root = os.environ.get("WORKSPACE_ROOT", os.getcwd())
    result = handle_excel_template(body, workspace_root=workspace_root)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    result["template_color"] = "green"
    result["template_type"] = "excel"
    return result


@app.get("/api/word/download")
async def api_word_download(path: str = "") -> StreamingResponse:
    """
    下载已导出的 Word 文件。
    """
    if not path:
        raise HTTPException(status_code=400, detail="missing path")

    target = traditional_resolve_path(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")

    filename = target.name
    from starlette.responses import FileResponse
    return FileResponse(
        path=str(target),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.post("/api/chat")
async def api_chat(request: Request, body: ChatRequest) -> dict | JSONResponse:
    """Agentic chat；请把上传接口返回的 runtime_context 原样传入。"""
    if body.mode:
        set_llm_mode(body.mode)
    assert_p2_elevated_claim_or_raise(request)
    tier = resolve_ai_tier(request)
    rc = runtime_context_with_tier(body.runtime_context, tier)
    idem = normalize_idempotency_key(
        request.headers.get("idempotency-key") or request.headers.get("x-idempotency-key")
    )
    fp = fingerprint_chat(
        message=body.message,
        runtime_context=rc,
        system_prompt=body.system_prompt,
        mode=body.mode,
        db_write_token=body.db_write_token,
    )
    if idem:
        cached = try_get_json(CHAT_JSON_ROUTE, idem, fp)
        if cached is IDEMPOTENCY_CONFLICT:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key was reused with a different request body",
            )
        if isinstance(cached, dict):
            return JSONResponse(
                content=cached,
                headers={"Idempotency-Replayed": "true"},
            )
    intr = planner_workflow_interrupt_reply(body.message)
    if intr is not None:
        cleared = runtime_context_after_workflow_interrupt(rc)
        out: dict = {"reply": intr, "runtime_context": cleared}
        if idem:
            store_json(CHAT_JSON_ROUTE, idem, fp, out)
        return out
    try:
        reply = chat(
            body.message,
            runtime_context=rc,
            system_prompt=body.system_prompt,
            db_write_token=body.db_write_token,
        )
    except Exception as e:
        raise _http_exc_from_chat_error(e) from e
    out = {"reply": reply}
    if idem:
        store_json(CHAT_JSON_ROUTE, idem, fp, out)
    return out


def _sse_line(payload: dict) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


@app.post("/api/chat/stream")
async def api_chat_stream(request: Request, body: ChatRequest) -> StreamingResponse:
    """
    Same agent as /api/chat; response is text/event-stream.
    Emits JSON lines: {"type":"token","text":...} per content delta on the final assistant turn;
    tool rounds produce no events until the final text stream. Ends with {"type":"done"} or {"type":"error",...}.
    """
    if body.mode:
        set_llm_mode(body.mode)
    try:
        if resolve_llm_mode() != "offline":
            require_api_key()
        get_llm_client()
    except Exception as e:
        raise _http_exc_from_chat_error(e) from e

    assert_p2_elevated_claim_or_raise(request)
    tier = resolve_ai_tier(request)
    rc = runtime_context_with_tier(body.runtime_context, tier)
    idem = normalize_idempotency_key(
        request.headers.get("idempotency-key") or request.headers.get("x-idempotency-key")
    )
    fp = fingerprint_chat(
        message=body.message,
        runtime_context=rc,
        system_prompt=body.system_prompt,
        mode=body.mode,
        db_write_token=body.db_write_token,
    )
    if idem:
        cached = try_get_stream(CHAT_STREAM_ROUTE, idem, fp)
        if cached is IDEMPOTENCY_CONFLICT:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key was reused with a different request body",
            )
        if isinstance(cached, (bytes, bytearray)) and cached:

            def _replay():
                yield bytes(cached)

            return StreamingResponse(
                _replay(),
                media_type="text/event-stream",
                headers={"Idempotency-Replayed": "true"},
            )

    def event_gen():
        buf = bytearray()
        try:
            intr = planner_workflow_interrupt_reply(body.message)
            if intr is not None:
                cleared = runtime_context_after_workflow_interrupt(rc)
                t1 = _sse_line({"type": "token", "text": intr})
                t2 = _sse_line({"type": "done", "runtime_context": cleared})
                buf.extend(t1)
                buf.extend(t2)
                yield t1
                yield t2
                if idem:
                    store_stream(CHAT_STREAM_ROUTE, idem, fp, bytes(buf))
                return
            for fragment in chat_stream_text(
                body.message,
                runtime_context=rc,
                system_prompt=body.system_prompt,
                db_write_token=body.db_write_token,
            ):
                line = _sse_line({"type": "token", "text": fragment})
                buf.extend(line)
                yield line
            done_line = _sse_line({"type": "done"})
            buf.extend(done_line)
            yield done_line
            if idem:
                store_stream(CHAT_STREAM_ROUTE, idem, fp, bytes(buf))
        except Exception as e:
            err = _http_exc_from_chat_error(e)
            line = _sse_line(
                {
                    "type": "error",
                    "message": err.detail if isinstance(err.detail, str) else str(err.detail),
                    "status_code": err.status_code,
                }
            )
            yield line

    return StreamingResponse(event_gen(), media_type="text/event-stream")


def main() -> None:
    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("backend.http_app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
