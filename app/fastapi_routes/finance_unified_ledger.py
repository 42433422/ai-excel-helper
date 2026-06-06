"""自建财务统一归档 API（独立路由，避免 finance.py 依赖 finance_schema 导入链）。"""

import logging
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FinanceLedgerRebuildBody(BaseModel):
    market_user_id: Optional[int] = Field(default=None, ge=1)


class FinanceLedgerListResponse(BaseModel):
    ok: bool = True
    items: list = Field(default_factory=list)
    finance_self_hosted: bool = True
    count: int = 0


router = APIRouter(prefix="/api/finance", tags=["finance-unified-ledger"])


@router.get("/unified-ledger")
def finance_unified_ledger(
    market_user_id: Optional[int] = Query(default=None),
    track: Optional[str] = Query(default=None, description="contract|token|manual"),
    limit: int = Query(default=200, ge=1, le=2000),
):
    """XCAGI 自建财务统一单据：CRM 账单 + MODstore 订单 + 归档凭证。"""
    try:
        from app.services.finance_unified_archive import list_ledger

        items = list_ledger(
            market_user_id=market_user_id,
            track=track,
            limit=limit,
        )
        return {
            "ok": True,
            "items": items,
            "finance_self_hosted": True,
            "count": len(items),
        }
    except Exception as exc:
        logger.exception("unified-ledger list failed")
        return JSONResponse(
            {"ok": False, "message": str(exc)[:500], "items": [], "count": 0},
            status_code=500,
        )


@router.get("/unified-ledger/summary")
def finance_unified_ledger_summary(
    market_user_id: Optional[int] = Query(default=None),
):
    """按轨道汇总笔数与金额（分）。"""
    try:
        from app.services.finance_unified_archive import summarize_ledger

        summary = summarize_ledger(market_user_id=market_user_id)
        return {
            "ok": True,
            "summary": summary,
            "finance_self_hosted": True,
        }
    except Exception as exc:
        logger.exception("unified-ledger summary failed")
        return JSONResponse(
            {"ok": False, "message": str(exc)[:500], "summary": None},
            status_code=500,
        )


@router.post("/unified-ledger/rebuild")
def finance_unified_ledger_rebuild(body: FinanceLedgerRebuildBody):
    """从 CRM 发票与 Token 订单幂等重建 financial_transactions 归档。"""
    try:
        from app.services.finance_unified_archive import rebuild_ledger_archive

        market_user_id = body.market_user_id
        result = rebuild_ledger_archive(market_user_id=market_user_id)
        return {"ok": True, **result}
    except Exception as exc:
        logger.exception("unified-ledger rebuild failed")
        return JSONResponse(
            {"ok": False, "message": str(exc)[:500]},
            status_code=500,
        )
