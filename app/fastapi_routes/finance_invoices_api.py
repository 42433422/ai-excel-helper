"""自建发票管理 API：合同轨 CRM 账单 + Token 轨 MODstore 开票申请代理。"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/finance/invoices", tags=["finance-invoices"])


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


class CrmInvoiceIssueBody(BaseModel):
    market_user_id: Optional[int] = Field(default=None, ge=1)
    opportunity_id: Optional[int] = Field(default=None, ge=1)
    username: str = Field(default="", max_length=128)


class MarketInvoiceReviewBody(BaseModel):
    action: str = Field(..., pattern="^(issue|reject)$")
    pdf_url: str = Field(default="", max_length=2048)
    reject_reason: str = Field(default="", max_length=2000)


@router.get("/tax-channel")
def finance_tax_channel(request: Request):
    gate = _require_admin_session(request)
    if gate is not None:
        return gate
    raw = (os.environ.get("TAX_INVOICE_PROVIDER") or "stub").strip().lower()
    labels = {
        "stub": "自建 Stub（账单号 + 凭证归档，无需外部 ERP）",
        "baiwang": "百望云（可选税控通道，当前为占位实现）",
    }
    return {
        "ok": True,
        "provider": raw or "stub",
        "label": labels.get(raw, raw),
        "self_hosted": True,
        "baiwang_configured": raw in ("baiwang", "百望"),
        "external_erp": False,
    }


@router.get("/crm")
def finance_crm_invoices_list(
    request: Request,
    market_user_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    gate = _require_admin_session(request)
    if gate is not None:
        return gate
    try:
        from app.services.user_cs_crm_store import list_crm_invoices

        data = list_crm_invoices(
            market_user_id=market_user_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return {"ok": True, "finance_self_hosted": True, **data}
    except Exception as exc:
        logger.exception("crm invoices list failed")
        return JSONResponse({"ok": False, "message": str(exc)[:500]}, status_code=500)


@router.get("/crm/{invoice_id}")
def finance_crm_invoice_detail(request: Request, invoice_id: int):
    gate = _require_admin_session(request)
    if gate is not None:
        return gate
    try:
        from app.services.user_cs_crm_store import get_crm_invoice_by_id

        inv = get_crm_invoice_by_id(int(invoice_id))
        if not inv:
            return JSONResponse({"ok": False, "message": "发票不存在"}, status_code=404)
        return {"ok": True, "invoice": inv}
    except Exception as exc:
        logger.exception("crm invoice detail failed")
        return JSONResponse({"ok": False, "message": str(exc)[:500]}, status_code=500)


@router.post("/crm/issue")
def finance_crm_invoice_issue(request: Request, body: CrmInvoiceIssueBody):
    gate = _require_admin_session(request)
    if gate is not None:
        return gate
    try:
        from app.services.tax_invoice_provider import issue_crm_invoice_for_pipeline
        from app.services.user_cs_crm_store import get_opportunity_by_market_user
        from app.services.user_cs_pipeline import load_pipeline, save_pipeline

        uid = int(body.market_user_id or 0)
        opp_id = int(body.opportunity_id or 0)
        if uid <= 0 and opp_id <= 0:
            return JSONResponse(
                {"ok": False, "message": "请提供 market_user_id 或 opportunity_id"},
                status_code=400,
            )
        if uid <= 0 and opp_id > 0:
            from app.services.user_cs_crm_store import _connect, ensure_crm_schema

            ensure_crm_schema()
            with _connect() as conn:
                row = conn.execute(
                    "SELECT market_user_id FROM cs_crm_opportunities WHERE id = ?",
                    (opp_id,),
                ).fetchone()
            uid = int(row["market_user_id"]) if row else 0
        if uid <= 0:
            return JSONResponse(
                {"ok": False, "message": "无法解析 market_user_id"}, status_code=400
            )
        doc = load_pipeline(uid, username=body.username)
        if opp_id > 0:
            doc["crm_opportunity_id"] = opp_id
        elif not doc.get("crm_opportunity_id"):
            opp = get_opportunity_by_market_user(uid)
            if opp:
                doc["crm_opportunity_id"] = int(opp["id"])
        if int(doc.get("crm_opportunity_id") or 0) <= 0:
            return JSONResponse(
                {"ok": False, "message": "商机未入库，请先在内部客服同步 CRM"},
                status_code=400,
            )
        doc = issue_crm_invoice_for_pipeline(doc)
        doc = save_pipeline(doc, strict_crm=False)
        inv = doc.get("invoice") if isinstance(doc.get("invoice"), dict) else {}
        return {"ok": True, "pipeline": doc, "invoice": inv}
    except ValueError as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=400)
    except Exception as exc:
        logger.exception("crm invoice issue failed")
        return JSONResponse({"ok": False, "message": str(exc)[:500]}, status_code=500)


@router.post("/crm/{invoice_id}/archive")
def finance_crm_invoice_archive(request: Request, invoice_id: int):
    gate = _require_admin_session(request)
    if gate is not None:
        return gate
    try:
        from app.services.finance_unified_archive import archive_from_crm_invoice
        from app.services.user_cs_crm_store import get_crm_invoice_by_id

        inv = get_crm_invoice_by_id(int(invoice_id))
        if not inv:
            return JSONResponse({"ok": False, "message": "发票不存在"}, status_code=404)
        uid = int(inv.get("market_user_id") or 0)
        result = archive_from_crm_invoice(inv, market_user_id=uid)
        inv = get_crm_invoice_by_id(int(invoice_id))
        return {
            "ok": True,
            "archive": result,
            "invoice": inv,
        }
    except Exception as exc:
        logger.exception("crm invoice archive failed")
        return JSONResponse({"ok": False, "message": str(exc)[:500]}, status_code=500)


@router.get("/market")
async def finance_market_invoices_list(
    request: Request,
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    gate = _require_admin_session(request)
    if gate is not None:
        return gate
    from app.fastapi_routes.xcmax_admin import _market_admin_proxy

    q: list[str] = [f"page={int(page)}", f"page_size={int(page_size)}"]
    if status:
        q.append(f"status={status.strip()}")
    path = "/api/admin/invoices?" + "&".join(q)
    payload = await _market_admin_proxy(request, "GET", path)
    if isinstance(payload, JSONResponse):
        return payload
    return payload if isinstance(payload, dict) else {"ok": True, "data": payload}


@router.patch("/market/{invoice_id}")
async def finance_market_invoice_review(
    request: Request,
    invoice_id: int,
    body: MarketInvoiceReviewBody,
):
    gate = _require_admin_session(request)
    if gate is not None:
        return gate
    from app.fastapi_routes.xcmax_admin import _market_admin_proxy

    payload = await _market_admin_proxy(
        request,
        "PATCH",
        f"/api/admin/invoices/{int(invoice_id)}",
        json_body=body.model_dump(),
    )
    if isinstance(payload, JSONResponse):
        return payload
    return payload if isinstance(payload, dict) else {"ok": True, "data": payload}
