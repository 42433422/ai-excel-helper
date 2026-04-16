"""
XCAGI「审批流程规则」页使用的轻量 API（原前端直连路径，FastAPI 侧补齐）。

配置与待办列表持久化在 WORKSPACE_ROOT/424/_xcagi_ai_approval_state.json。
通过 / 拒绝为占位成功，不执行真实工作流。
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.shell.taiyangniao_attendance.paths import workspace_root

router = APIRouter(prefix="/ai", tags=["ai-approval"])

_lock = threading.Lock()
_STATE_NAME = "_xcagi_ai_approval_state.json"


def _state_path() -> Path:
    d = workspace_root() / "424"
    d.mkdir(parents=True, exist_ok=True)
    return d / _STATE_NAME


def _default_state() -> dict[str, Any]:
    return {"enabled": True, "rules": [], "pending_approvals": []}


def _load_state() -> dict[str, Any]:
    p = _state_path()
    if not p.is_file():
        return _default_state()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return _default_state()
        out = _default_state()
        out["enabled"] = bool(raw.get("enabled", True))
        out["rules"] = raw["rules"] if isinstance(raw.get("rules"), list) else []
        pa = raw.get("pending_approvals")
        out["pending_approvals"] = pa if isinstance(pa, list) else []
        return out
    except (OSError, ValueError, TypeError):
        return _default_state()


def _save_state(state: dict[str, Any]) -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


class ApprovalConfigBody(BaseModel):
    enabled: bool = True
    rules: list[Any] = Field(default_factory=list)


class PlanIdBody(BaseModel):
    plan_id: str | None = None


@router.get("/approval/pending")
async def approval_pending() -> dict[str, Any]:
    with _lock:
        st = _load_state()
    return {"success": True, "data": {"pending_approvals": st.get("pending_approvals", [])}}


@router.get("/config/approval")
async def approval_config_get() -> dict[str, Any]:
    with _lock:
        st = _load_state()
    return {"enabled": st.get("enabled", True), "rules": st.get("rules", [])}


@router.post("/config/approval")
async def approval_config_post(body: ApprovalConfigBody) -> dict[str, Any]:
    with _lock:
        st = _load_state()
        st["enabled"] = body.enabled
        st["rules"] = body.rules
        _save_state(st)
    return {"success": True, "message": "已保存"}


@router.post("/approval/approve")
async def approval_approve(body: PlanIdBody) -> dict[str, Any]:
    pid = (body.plan_id or "").strip()
    with _lock:
        st = _load_state()
        pending = [x for x in st.get("pending_approvals", []) if str(x.get("plan_id", "")) != pid]
        st["pending_approvals"] = pending
        _save_state(st)
    return {
        "success": True,
        "message": "已通过（占位：未执行工作流）",
        "data": {"workflow_executed": False},
    }


@router.post("/approval/reject")
async def approval_reject(body: PlanIdBody) -> dict[str, Any]:
    pid = (body.plan_id or "").strip()
    with _lock:
        st = _load_state()
        pending = [x for x in st.get("pending_approvals", []) if str(x.get("plan_id", "")) != pid]
        st["pending_approvals"] = pending
        _save_state(st)
    return {"success": True, "message": "已拒绝"}
