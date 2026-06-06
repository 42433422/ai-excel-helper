"""销售合同 API（模板预览 / LLM 解析）— 注册至 FastAPI 主应用。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/sales-contract", tags=["sales-contract"])


class ResolveFromTextBody(BaseModel):
    text: str = Field(..., min_length=1)


@router.get("/templates")
def list_templates():
    from app.infrastructure.documents.template_registry import list_templates

    return JSONResponse({"success": True, "data": list_templates(role="sales_contract_docx")})


@router.get("/template-preview")
def template_preview(slug: str | None = None):
    from app.infrastructure.documents.price_list_export import (
        build_sales_contract_template_preview_json,
    )

    return JSONResponse(
        {"success": True, "data": build_sales_contract_template_preview_json(slug=slug)}
    )


@router.post("/resolve-from-text")
def resolve_from_text(body: ResolveFromTextBody):
    text = body.text.strip()
    # 轻量规则抽取；完整 LLM 路径可在后续接入
    products: list[dict[str, Any]] = []
    if "产品" in text or "SKU" in text:
        products.append({"name": "定制软件服务", "quantity": 1, "unit_price": 0})
    return JSONResponse(
        {
            "success": True,
            "data": {
                "party_a": "",
                "party_b": "",
                "total_amount_number": "",
                "products": products,
                "raw_text": text[:4000],
            },
        }
    )
