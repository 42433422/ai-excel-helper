"""客户端状态 API（原版模式开关等），自归档 state 蓝图迁移。"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/state", tags=["client-state"])

# 与归档 state.py 一致：``.archive/.client_mods_state.json``（仓库根下 .archive）
STATE_FILE = Path(__file__).resolve().parents[2] / ".archive" / ".client_mods_state.json"


def read_client_mods_off_state() -> bool:
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return bool(data.get("client_mods_off", False))
    except Exception as e:
        logger.warning("[State API] 读取状态文件失败: %s", e)
    return False


def write_client_mods_off_state(value: bool) -> None:
    try:
        data = {
            "client_mods_off": value,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("[State API] 已写入 client_mods_off=%s", value)
    except Exception as e:
        logger.error("[State API] 写入状态文件失败: %s", e)


@router.get("/client-mods-off")
def get_client_mods_off():
    return JSONResponse(
        {
            "success": True,
            "data": {"client_mods_off": read_client_mods_off_state()},
        }
    )


@router.post("/client-mods-off")
def set_client_mods_off(body: dict[str, Any] = Body(default_factory=dict)):
    value = bool(body.get("client_mods_off", False))
    write_client_mods_off_state(value)
    return JSONResponse(
        {
            "success": True,
            "data": {"client_mods_off": value},
        }
    )
