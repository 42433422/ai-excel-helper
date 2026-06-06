"""合同生命周期 + 电子签 webhook。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.schemas.contract_lifecycle_schemas import (
    ContractTransitionBody,
    EsignSignCompleteBody,
    EsignStartBody,
    EsignWebhookBody,
)

router = APIRouter(prefix="/api/contract-lifecycle", tags=["contract-lifecycle"])


def _require_admin_session(request: Request) -> JSONResponse | None:
    from app.application.session_account_meta import load_session_account_meta
    from app.fastapi_routes.domains.misc.helpers import _session_id_from_request

    sid = _session_id_from_request(request)
    if not sid:
        return JSONResponse({"ok": False, "message": "请先登录"}, status_code=401)
    meta = load_session_account_meta(sid) or {}
    if meta.get("account_kind") != "admin":
        return JSONResponse(
            {"ok": False, "message": "需要管理员账号登录后访问"},
            status_code=403,
        )
    return None


@router.get("/esign-channel")
def esign_channel(request: Request):
    """财务统计 / 电子签页：展示当前 ESIGN_PROVIDER 与是否需法大大。"""
    gate = _require_admin_session(request)
    if gate is not None:
        return gate
    from app.services.esign_adapter import esign_channel_status

    return JSONResponse(esign_channel_status())


@router.get("/status")
def contract_lifecycle_status(market_user_id: int, username: str = ""):
    from app.services.contract_lifecycle import get_contract_block
    from app.services.user_cs_pipeline import load_pipeline

    uid = int(market_user_id)
    doc = load_pipeline(uid, username=username)
    block = get_contract_block(doc)
    task = block.get("esign_task") if isinstance(block.get("esign_task"), dict) else {}
    fields = doc.get("contract_fields") if isinstance(doc.get("contract_fields"), dict) else {}
    sign_url = str(task.get("sign_url") or "").strip()
    return JSONResponse(
        {
            "success": True,
            "data": {
                "market_user_id": uid,
                "stage": doc.get("stage"),
                "username": doc.get("username"),
                "erp_customer_name": doc.get("erp_customer_name"),
                "contract_lifecycle": block,
                "sign_url": sign_url,
                "party_a_default": str(
                    fields.get("party_a_name") or doc.get("erp_customer_name") or ""
                ).strip(),
            },
        }
    )


@router.post("/transition")
def contract_transition(body: ContractTransitionBody):
    from app.services.contract_lifecycle import apply_contract_to_crm_meta, transition_contract
    from app.services.user_cs_pipeline import load_pipeline, save_pipeline

    uid = body.market_user_id
    status = body.status.strip()
    doc = load_pipeline(uid, username=body.username)
    doc = transition_contract(doc, status, source="api", note=body.note)
    doc = apply_contract_to_crm_meta(doc)
    doc = save_pipeline(doc)
    return JSONResponse({"success": True, "data": {"pipeline": doc}})


@router.post("/esign/start")
def esign_start(body: EsignStartBody):
    from app.services.contract_lifecycle import apply_contract_to_crm_meta, start_esign_flow
    from app.services.user_cs_pipeline import load_pipeline, save_pipeline

    uid = body.market_user_id
    doc = load_pipeline(uid, username=body.username)
    payment = doc.get("payment") if isinstance(doc.get("payment"), dict) else {}
    amount = payment.get("contract_amount_cents")
    doc = start_esign_flow(
        doc,
        party_a=body.party_a,
        party_b=body.party_b or str(doc.get("erp_customer_name") or ""),
        amount_cents=int(amount) if amount is not None else None,
    )
    doc = apply_contract_to_crm_meta(doc)
    doc = save_pipeline(doc)
    return JSONResponse({"success": True, "data": {"pipeline": doc}})


@router.get("/esign/sign/{task_id}")
def esign_sign_task_public(task_id: str, token: str = ""):
    """客户签署页拉取任务信息（无需登录，须 token）。"""
    from app.services.esign_adapter import esign_provider_name
    from app.services.stub_esign_store import (
        get_task,
        task_ttl_exceeded,
        verify_sign_token,
    )

    if esign_provider_name() != "stub":
        return JSONResponse(
            {"success": False, "error": "当前通道非自建电子签"},
            status_code=400,
        )
    if not verify_sign_token(task_id, token):
        return JSONResponse({"success": False, "error": "链接无效或已过期"}, status_code=403)
    task = get_task(task_id)
    if not task:
        return JSONResponse({"success": False, "error": "签署任务不存在"}, status_code=404)
    if task_ttl_exceeded(task):
        return JSONResponse({"success": False, "error": "签署链接已过期"}, status_code=410)
    return JSONResponse(
        {
            "success": True,
            "data": {
                "task_id": task.get("task_id"),
                "subject": task.get("subject"),
                "party_a": task.get("party_a"),
                "party_b": task.get("party_b"),
                "amount_cents": task.get("amount_cents"),
                "status": task.get("status"),
                "signed_at": task.get("signed_at"),
                "signer_name": task.get("signer_name"),
            },
        }
    )


@router.post("/esign/sign/{task_id}/complete")
def esign_sign_complete_public(task_id: str, body: EsignSignCompleteBody):
    """客户在自建签署页确认签署，自动推进合同状态。"""
    from app.services.contract_lifecycle import handle_esign_webhook
    from app.services.esign_adapter import esign_provider_name
    from app.services.stub_esign_store import (
        complete_task,
        get_task,
        task_ttl_exceeded,
        verify_sign_token,
    )

    if esign_provider_name() != "stub":
        return JSONResponse(
            {"success": False, "error": "当前通道非自建电子签"},
            status_code=400,
        )
    if not body.agree:
        return JSONResponse({"success": False, "error": "请先勾选同意条款"}, status_code=400)
    if not verify_sign_token(task_id, body.token):
        return JSONResponse({"success": False, "error": "链接无效或已过期"}, status_code=403)
    task = get_task(task_id)
    if not task:
        return JSONResponse({"success": False, "error": "签署任务不存在"}, status_code=404)
    if task_ttl_exceeded(task):
        return JSONResponse({"success": False, "error": "签署链接已过期"}, status_code=410)
    if str(task.get("status") or "") == "signed":
        return JSONResponse({"success": True, "data": {"already_signed": True}})

    signer = (body.signer_name or task.get("party_b") or "").strip()
    if not signer:
        return JSONResponse({"success": False, "error": "请填写签署人姓名"}, status_code=400)

    complete_task(task_id, signer_name=signer)
    result = handle_esign_webhook(
        {
            "signed": True,
            "market_user_id": task.get("market_user_id"),
            "task_id": task_id,
        }
    )
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)
    return JSONResponse({"success": True, "data": {"signed": True, "signer_name": signer}})


@router.post("/esign/webhook")
async def esign_webhook(request: Request):
    """Stub：JSON body；法大大：application/x-www-form-urlencoded + X-FASC-* 头。"""
    from app.services.contract_lifecycle import handle_esign_webhook

    fasc_app_id = (request.headers.get("X-FASC-App-Id") or "").strip()
    content_type = (request.headers.get("content-type") or "").lower()
    if fasc_app_id or "application/x-www-form-urlencoded" in content_type:
        return await _fadada_esign_webhook(request)

    try:
        raw = await request.json()
    except Exception:
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    body = EsignWebhookBody.model_validate(raw)
    return JSONResponse(handle_esign_webhook(body.model_dump()))


async def _fadada_esign_webhook(request: Request) -> PlainTextResponse | JSONResponse:
    from app.services.contract_lifecycle import handle_esign_webhook
    from app.services.esign_adapter import get_esign_adapter
    from app.services.fadada_fasc_client import (
        parse_fadada_callback_biz,
        verify_fadada_callback_signature,
    )

    form = await request.form()
    biz_content = str(form.get("bizContent") or "")
    headers = {k: v for k, v in request.headers.items()}
    if not verify_fadada_callback_signature(headers, biz_content):
        return PlainTextResponse('{"msg":"success"}', media_type="application/json")

    biz = parse_fadada_callback_biz(biz_content)
    event = (headers.get("X-FASC-Event") or headers.get("x-fasc-event") or "").strip()
    adapter = get_esign_adapter()
    parsed = adapter.parse_webhook(
        {
            "_fadada_callback": True,
            "event": event,
            "biz": biz,
        }
    )
    result = handle_esign_webhook(parsed)
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)
    return PlainTextResponse('{"msg":"success"}', media_type="application/json")
