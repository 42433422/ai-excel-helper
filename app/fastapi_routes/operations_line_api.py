"""运营线健康度 API（供全景页 / MODstore admin 拉取）。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/operations-line", tags=["operations-line"])


@router.get("/health")
def operations_health():
    from app.services.operations_line_bridge import compute_operations_health

    return JSONResponse({"success": True, "data": compute_operations_health()})


@router.post("/contracts/scan-expiry")
def operations_scan_contract_expiry(days_ahead: int = 30, dry_run: bool = True):
    from app.services.contract_expiry_scheduler import run_contract_expiry_scan

    return JSONResponse(
        {
            "success": True,
            "data": run_contract_expiry_scan(days_ahead=days_ahead, dry_run=dry_run),
        }
    )


@router.get("/signoff/status")
def operations_signoff_status():
    from app.services.user_cs_delivery_signoff import signoff_backend_info

    return JSONResponse({"success": True, "data": signoff_backend_info()})


@router.get("/reconciliation/status")
def operations_reconciliation_status():
    from app.services.reconciliation_scheduler import get_reconciliation_status

    return JSONResponse({"success": True, "data": get_reconciliation_status()})


@router.post("/reconciliation/run")
def operations_reconciliation_run(dry_run: bool = False):
    from app.services.reconciliation_scheduler import (
        run_reconciliation_full_cycle,
        run_reconciliation_preview_cycle,
    )

    data = run_reconciliation_preview_cycle() if dry_run else run_reconciliation_full_cycle()
    return JSONResponse({"success": bool(data.get("ok")), "data": data})
