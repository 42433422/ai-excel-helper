"""
价格表生成 API
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/price-list", tags=["price_list"])


def _parse_quantity(value: str) -> int:
    """解析数量值"""
    import re
    match = re.search(r'(\d+)', str(value))
    if match:
        return int(match.group(1))
    return 0


def _parse_float(value: str | float | None, default: float = 0.0) -> float:
    """安全解析浮点数"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    import re
    match = re.search(r'[\d.]+', str(value))
    if match:
        try:
            return round(float(match.group()), 2)
        except ValueError:
            return default
    return default


class PriceListProduct(BaseModel):
    model_number: str
    name: str = ""
    spec: str = ""
    unit: str = ""
    unit_price: str = "0"


class PriceListGenerateRequest(BaseModel):
    customer_name: str
    products: list[PriceListProduct] = []
    printer_name: str = ""
    template_id: str | None = None


class PriceListGenerateResponse(BaseModel):
    success: bool
    data: dict[str, Any] | None = None
    message: str = ""
    error: str = ""


def _get_output_dir() -> Path:
    """获取输出目录"""
    output_dir = Path("e:/FHD/424/outputs/price_lists")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


from backend.product_db_read import load_products_price_table_rows


@router.post("/generate", response_model=PriceListGenerateResponse)
async def generate_price_list(request: PriceListGenerateRequest):
    """
    生成价格表

    使用模板生成 Word 价格表文档。
    """
    try:
        from backend.price_list_docx_export import (
            build_price_list_docx_bytes,
            resolve_price_list_docx_template,
        )

        logger.info(f"收到价格表生成请求：customer_name={request.customer_name}")

        template_path = resolve_price_list_docx_template(
            (request.template_id or "").strip() or None
        )
        if not template_path:
            raise HTTPException(
                status_code=404,
                detail="未找到价格表模板文件"
            )

        export_date = datetime.now().strftime("%Y-%m-%d")

        products_data = []
        for p in request.products:
            price = _parse_float(p.unit_price)
            products_data.append({
                "model_number": str(p.model_number or "").strip(),
                "name": str(p.name or "").strip(),
                "specification": str(p.spec or "").strip(),
                "unit": str(p.unit or "").strip() or "桶",
                "unit_price": str(price),
                "price": price,
            })

        if not products_data:
            products_data = load_products_price_table_rows(request.customer_name)

        if not products_data:
            raise HTTPException(
                status_code=404,
                detail=f"未找到客户「{request.customer_name}」的产品"
            )

        docx_bytes = build_price_list_docx_bytes(
            template_path,
            customer_name=request.customer_name,
            quote_date=export_date,
            products=products_data,
        )

        output_dir = _get_output_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"价格表_{request.customer_name}_{timestamp}.docx"
        output_path = output_dir / output_filename
        output_path.write_bytes(docx_bytes)

        logger.info(f"价格表生成成功：{output_path}")

        return PriceListGenerateResponse(
            success=True,
            data={
                "filename": output_filename,
                "file_path": str(output_path),
                "customer_name": request.customer_name,
                "product_count": len(products_data),
            },
            message=f"已生成客户「{request.customer_name}」的价格表，包含 {len(products_data)} 个产品"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"价格表生成失败：{e}")
        return PriceListGenerateResponse(
            success=False,
            error=str(e),
            message="价格表生成失败"
        )


@router.get("/download")
async def download_price_list(filepath: str):
    """
    下载价格表文件
    """
    try:
        if not filepath:
            raise HTTPException(status_code=400, detail="缺少文件路径")

        file_path = Path(filepath)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        filename = file_path.name

        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"下载失败：{e}")
        raise HTTPException(status_code=500, detail=f"下载失败：{str(e)}")