"""服务间：FHD 模型支付订单对账区间快照（MODstore reconciliation 合并用）。"""

from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/internal/payment", tags=["payment-internal"])


def _require_internal_api_key(request: Request) -> None:
    expected = (
        os.environ.get("XCAGI_MARKET_INTERNAL_API_KEY")
        or os.environ.get("XCAGI_CS_INTAKE_LINK_SECRET")
        or os.environ.get("FHD_INTERNAL_API_KEY")
        or ""
    ).strip()
    if not expected:
        raise HTTPException(status_code=503, detail="internal api not configured")
    got = (request.headers.get("x-internal-api-key") or "").strip()
    if not got or not secrets.compare_digest(got, expected):
        raise HTTPException(status_code=403, detail="invalid internal api key")


@router.get("/reconciliation-period")
def api_fhd_reconciliation_period(
    request: Request,
    period_start: str = Query(..., description="ISO 8601"),
    period_end: str = Query(..., description="ISO 8601"),
):
    _require_internal_api_key(request)
    from app.services.fhd_payment_reconciliation import (
        _parse_dt,
        compute_fhd_period_snapshot,
    )

    start = _parse_dt(period_start)
    end = _parse_dt(period_end)
    if not start or not end:
        raise HTTPException(400, detail="invalid period_start or period_end")
    if end <= start:
        raise HTTPException(400, detail="period_end must be after period_start")
    snap = compute_fhd_period_snapshot(start, end)
    return JSONResponse(
        {
            "ok": True,
            "period_start": period_start,
            "period_end": period_end,
            "fhd_host_snapshot": snap,
        }
    )
