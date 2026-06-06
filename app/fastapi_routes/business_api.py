"""FHD 业务能力 HTTP 出口：通过神经域 emit / NeuroBus publish 触发既有流水线。

供 MODstore 员工或其它内网客户端调用。若设置环境变量 ``FHD_BUSINESS_API_KEY``，
则须在请求头携带 ``X-FHD-Business-Key``；未设置时仅依赖现有 LAN 门禁（生产务必配置密钥）。"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/business", tags=["business-bridge"])


def _expected_business_key() -> str:
    return (os.environ.get("FHD_BUSINESS_API_KEY") or "").strip()


def require_fhd_business_key(
    x_fhd_business_key: Annotated[str | None, Header(alias="X-FHD-Business-Key")] = None,
) -> None:
    exp = _expected_business_key()
    if not exp:
        return
    got = (x_fhd_business_key or "").strip()
    if got != exp:
        raise HTTPException(status_code=401, detail="invalid X-FHD-Business-Key")


BusinessKeyDep = Annotated[None, Depends(require_fhd_business_key)]


class PrintLabelBody(BaseModel):
    model_config = ConfigDict(extra="allow")

    job_id: str | None = None
    document_name: str = "document"
    printer_id: str = "default"
    copies: int = 1


@router.post("/print/label")
async def business_print_label(body: PrintLabelBody, _: BusinessKeyDep) -> dict[str, Any]:
    from app.neuro_bus.domains.print_domain import get_print_domain

    job_id = (body.job_id or "").strip() or str(uuid.uuid4())
    dom = get_print_domain()
    ok = dom.emit_job_submitted(
        job_id=job_id,
        document_name=body.document_name,
        printer_id=body.printer_id,
        copies=max(1, int(body.copies or 1)),
    )
    return {"ok": bool(ok), "job_id": job_id, "event": "print.job.submitted"}


class InventoryUpdateBody(BaseModel):
    model_config = ConfigDict(extra="allow")

    product_id: str
    warehouse_id: str = "default"
    delta: int = 0
    reason: str = "api_business"
    new_quantity: int = 0


@router.post("/inventory/update")
async def business_inventory_update(body: InventoryUpdateBody, _: BusinessKeyDep) -> dict[str, Any]:
    from app.neuro_bus.domains.inventory_domain import get_inventory_domain

    dom = get_inventory_domain()
    ok = dom.emit_stock_changed(
        product_id=body.product_id.strip(),
        warehouse_id=body.warehouse_id.strip(),
        delta=int(body.delta),
        reason=body.reason,
        new_quantity=int(body.new_quantity),
    )
    return {"ok": bool(ok), "event": "inventory.changed"}


class OcrRecognizeBody(BaseModel):
    model_config = ConfigDict(extra="allow")

    request_id: str | None = None
    image_url: str
    ocr_type: str = "general"
    user_id: str = "system"


@router.post("/ocr/recognize")
async def business_ocr_recognize(body: OcrRecognizeBody, _: BusinessKeyDep) -> dict[str, Any]:
    from app.neuro_bus.domains.ocr_domain import get_ocr_domain

    rid = (body.request_id or "").strip() or str(uuid.uuid4())
    dom = get_ocr_domain()
    ok = dom.emit_ocr_requested(
        request_id=rid,
        image_url=body.image_url.strip(),
        ocr_type=(body.ocr_type or "general").strip(),
        user_id=body.user_id.strip() or "system",
    )
    return {"ok": bool(ok), "request_id": rid, "event": "ocr.requested"}


class ShipmentCreateBody(BaseModel):
    model_config = ConfigDict(extra="allow")

    unit_name: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    contact_person: str = ""
    contact_phone: str = ""


@router.post("/shipment/create")
async def business_shipment_create(body: ShipmentCreateBody, _: BusinessKeyDep) -> dict[str, Any]:
    from app.neuro_bus.application_neuro_bridge import publish_neuro_event

    payload = {
        "unit_name": body.unit_name.strip(),
        "items": body.items,
        "contact_person": body.contact_person.strip(),
        "contact_phone": body.contact_phone.strip(),
    }
    ok = publish_neuro_event("shipment.created", payload, "shipment")
    if not ok:
        logger.info("business shipment.create: neuro publish skipped or failed (stack off?)")
    return {"ok": bool(ok), "published": ok, "event": "shipment.created"}


@router.get("/health")
async def business_health(_: BusinessKeyDep) -> dict[str, Any]:
    return {"ok": True, "business_api": "up", "key_required": bool(_expected_business_key())}
