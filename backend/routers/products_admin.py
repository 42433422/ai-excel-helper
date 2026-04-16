"""
受令牌保护的产品批量写入（购买单位 + 多行报价）。

路径前缀 ``/api/admin/`` 不在公开 API 白名单内：若配置了 ``FHD_API_KEYS``，须同时携带合法 API Key。
写入本身另需请求头 ``X-FHD-Db-Write-Token`` 与环境变量 ``FHD_DB_WRITE_TOKEN`` 一致。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request

from backend.db_write_auth import verify_db_write_token_header
from backend.products_bulk_import import run_bulk_import

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/products", tags=["admin-products"])


@router.post("/bulk-import")
@router.post("/bulk-import/")
async def products_bulk_import(request: Request, body: dict[str, Any] = Body(default_factory=dict)) -> dict:
    verify_db_write_token_header(request)
    try:
        result = run_bulk_import(body)
    except Exception as e:
        logger.exception("products bulk-import failed")
        raise HTTPException(status_code=500, detail=f"导入失败: {e}") from e
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message") or result.get("error") or "导入被拒绝",
        )
    return {"success": True, "data": result}
