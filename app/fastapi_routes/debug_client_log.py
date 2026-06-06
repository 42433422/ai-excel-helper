"""兼容旧版 ``POST /api/debug/client-log``（静态脚本 / 专业浮窗等仍主动上报）。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.post("/client-log")
def post_client_debug_log(body: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    try:
        from app.utils.logging_utils import ingest_client_debug_json

        return ingest_client_debug_json(body)
    except Exception as e:
        logger.exception("[debug] client-log 处理失败")
        return {"success": False, "message": str(e)}
