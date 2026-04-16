"""
销售合同生成 API
集成到统一 AI 架构
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query, Request, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.db_read_auth import verify_db_read_token_header
from backend.sales_contract_excel_generate import update_preview_products

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sales-contract", tags=["sales_contract"])


class SalesContractProduct(BaseModel):
    model_number: str
    name: str = ""
    spec: str = ""
    unit: str = ""
    quantity: str = "1"
    unit_price: str = "0"
    amount: str = "0"


class SalesContractGenerateRequest(BaseModel):
    customer_name: str
    customer_phone: str = ""
    contract_date: str = ""
    products: list[SalesContractProduct]
    return_buckets_expected: int = 0
    return_buckets_actual: int = 0
    template_id: str | None = Field(
        default=None,
        description="模板 slug（GET /api/document-templates?role=sales_contract_docx）；省略则用默认行",
    )


class SalesContractGenerateResponse(BaseModel):
    success: bool
    data: dict[str, Any] | None = None
    message: str = ""
    error: str = ""


@router.get("/template-preview")
async def sales_contract_template_preview(
    request: Request,
    template_id: str | None = Query(
        default=None,
        description="模板 slug（GET /api/document-templates?role=sales_contract_docx）；省略则用默认行",
    ),
) -> dict[str, Any]:
    """读取已登记销售合同 Word 首表表头与示例行；与价表 ``price-list-template-preview`` 对称，供模板库对齐。"""
    verify_db_read_token_header(request)
    from backend.price_list_docx_export import build_sales_contract_template_preview_json

    return build_sales_contract_template_preview_json(template_id)


@router.get("/templates")
async def list_sales_contract_templates() -> dict[str, Any]:
    """兼容旧前端：与 ``GET /api/document-templates?role=sales_contract_docx`` 同源（``id`` 字段即 slug）。"""
    from backend.document_template_service import ROLE_SALES_CONTRACT, list_templates

    rows = list_templates(ROLE_SALES_CONTRACT)
    out = [
        {
            "id": r["slug"],
            "label": r["display_name"],
            "path": r.get("storage_relpath"),
            "slug": r["slug"],
            "is_default": r.get("is_default"),
        }
        for r in rows
    ]
    default_row = next((r for r in rows if r.get("is_default")), rows[0] if rows else None)
    default_id = default_row["slug"] if default_row else None
    return {"success": True, "data": out, "default_id": default_id}


@router.post("/resolve-from-text")
async def sales_contract_resolve_from_text(request: Request, body: dict = Body(...)) -> dict[str, Any]:
    """
    将用户整句销售合同订货话术经 LLM 结构化抽取后，与主数据对齐，返回客户名与产品行（与 Planner / bridge 同源）。
    需配置 LLM API Key；未对齐到库中产品时 ``success`` 为 false。
    """
    verify_db_read_token_header(request)
    raw = str(body.get("text") or body.get("user_message") or "").strip()
    if not raw:
        return {"success": False, "message": "text 不能为空", "data": None}

    try:
        from backend.sales_contract_intent_bridge import (
            extract_sales_contract_draft,
            resolve_draft_to_tool_slots,
        )

        draft = extract_sales_contract_draft(raw)
        if not draft or not draft.lines:
            return {
                "success": False,
                "message": "未能从话术中抽取订货行（需配置 LLM API Key，或话术过短/无效）",
                "data": None,
            }
        slots = resolve_draft_to_tool_slots(draft, raw_user_message=raw)
        if not slots or not slots.get("products"):
            return {
                "success": False,
                "message": "草稿无法与主数据产品对齐，请检查型号/品名是否在库中",
                "data": None,
            }
        prods: list[dict[str, Any]] = []
        for p in slots["products"]:
            try:
                q = float(p.get("quantity") or 1)
            except (TypeError, ValueError):
                q = 1.0
            try:
                up = float(p.get("unit_price") or 0)
            except (TypeError, ValueError):
                up = 0.0
            amt = q * up
            amt_s = str(int(amt)) if amt == int(amt) else str(amt)
            prods.append(
                {
                    "model_number": str(p.get("model_number") or ""),
                    "name": str(p.get("name") or ""),
                    "spec": str(p.get("spec") or ""),
                    "unit": str(p.get("unit") or "桶"),
                    "quantity": str(p.get("quantity") or "1"),
                    "unit_price": str(p.get("unit_price") or "0"),
                    "amount": amt_s,
                }
            )
        return {
            "success": True,
            "data": {
                "customer_name": str(slots.get("customer_name") or "").strip(),
                "products": prods,
            },
            "message": "",
        }
    except Exception as e:
        logger.exception("resolve-from-text failed")
        return {"success": False, "message": str(e), "data": None}


@router.post("/generate", response_model=SalesContractGenerateResponse)
async def generate_sales_contract(request: SalesContractGenerateRequest):
    """
    生成销售合同（仅支持 Excel 模板 .xls/.xlsx/.xlsm）。

    成功时 ``data`` 含 ``filename`` / ``file_path``；另含 ``requested_template_id``（请求传入）、
    ``template_id``（实际使用的 slug）、``template_path_suffix``、``export_format``（固定 ``xlsx``），
    便于在浏览器 Network 中与下拉选的 ``template_id`` 对照。
    """
    from backend.sales_contract_generate_core import run_sales_contract_generation

    try:
        logger.info("产品数据：%s", request.products)
        out = run_sales_contract_generation(request)
        return SalesContractGenerateResponse(**out)
    except HTTPException:
        raise


@router.post("/preview-update")
async def update_sales_contract_preview(body: dict = Body(...)):
    """
    前端表格删除/修改行后调用。
    接收最新 products 列表，重新生成 Excel，返回更新后的预览数据和下载链接。
    """
    try:
        products = body.get("products", [])
        customer_name = body.get("customer_name", "客户")
        contract_date = body.get("contract_date", "")
        if isinstance(products, list):
            for p in products:
                if not isinstance(p, dict):
                    continue
                if p.get("specification") in (None, "") and p.get("spec") not in (None, ""):
                    p["specification"] = str(p.get("spec") or "").strip()

        from backend.sales_contract_generate_core import _get_output_dir
        out = update_preview_products(
            template_path=Path("424/document_templates/送货单.xls"),
            products=products,
            customer_name=customer_name,
            contract_date=contract_date,
            output_dir=_get_output_dir(),
        )
        return out
    except Exception as e:
        logger.exception("preview-update failed")
        return {"success": False, "message": str(e)}


@router.post("/generate-and-print", response_model=SalesContractGenerateResponse)
async def generate_and_print_sales_contract(request: SalesContractGenerateRequest):
    """
    生成并打印销售合同
    """
    generate_result = await generate_sales_contract(request)

    if not generate_result.success:
        return generate_result

    try:
        from backend.routers.print import print_document

        fp = (generate_result.data or {}).get("file_path")
        if not fp:
            generate_result.message = "销售合同已生成，但缺少文件路径无法打印"
            return generate_result

        print_result = await print_document({"file_path": fp, "printer_name": None})

        if print_result.get("success"):
            generate_result.message = "销售合同已生成并发送到打印机"
        else:
            generate_result.message = (
                f"销售合同已生成，但打印失败：{print_result.get('error', '')}"
            )
    except Exception as e:
        logger.warning("销售合同打印失败：%s", e)
        generate_result.message = "销售合同已生成，但打印失败"

    return generate_result


def _sales_contract_output_roots() -> list[Path]:
    """生成结果所在目录（与 ``sales_contract_generate_core._get_output_dir`` 一致）。"""
    roots: list[Path] = []
    ws = (os.environ.get("WORKSPACE_ROOT") or "").strip()
    if ws and os.path.isdir(ws):
        roots.append((Path(ws).expanduser() / "uploads" / "sales_contracts").resolve())
    roots.append((Path(__file__).resolve().parents[2] / "424" / "outputs" / "sales_contracts").resolve())
    return roots


def _resolve_sales_contract_download_path(raw: str) -> Path:
    """
    解析待下载文件：支持绝对路径；若不存在则仅在 ``sales_contracts`` 输出目录下按文件名查找，
    防止误传 ``/download/仅文件名`` 时落到进程当前目录的同名文件。
    """
    s = unquote((raw or "").strip().strip('"').strip("'"))
    if not s:
        raise HTTPException(status_code=400, detail="缺少文件路径")

    roots = _sales_contract_output_roots()

    def _is_under_allowed(p: Path) -> bool:
        try:
            rp = p.resolve()
        except OSError:
            return False
        if not rp.is_file():
            return False
        for root in roots:
            try:
                rp.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    p0 = Path(s).expanduser()
    try:
        p1 = p0.resolve()
    except OSError as e:
        raise HTTPException(status_code=400, detail=f"路径无效：{e}") from e

    if p1.is_file() and _is_under_allowed(p1):
        return p1

    name = p0.name
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="缺少有效文件名")

    for root in roots:
        cand = (root / name).resolve()
        if cand.is_file() and _is_under_allowed(cand):
            return cand

    raise HTTPException(status_code=404, detail="文件不存在或不在销售合同输出目录")


def _sales_contract_download_media_type(file_path: Path) -> str:
    suf = file_path.suffix.lower()
    if suf == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if suf in (".xlsx", ".xlsm"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if suf == ".xls":
        return "application/vnd.ms-excel"
    return "application/octet-stream"


@router.get("/download")
async def download_sales_contract(filepath: str):
    """
    下载销售合同文件。``filepath`` 为生成接口返回的绝对路径，或仅为 ``filename``（在输出目录内解析）。
    """
    try:
        if not filepath:
            raise HTTPException(status_code=400, detail="缺少文件路径")

        file_path = _resolve_sales_contract_download_path(filepath)
        filename = file_path.name

        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type=_sales_contract_download_media_type(file_path),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"下载失败：{e}")
        raise HTTPException(status_code=500, detail=f"下载失败：{str(e)}")
