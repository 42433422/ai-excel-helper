"""
Control 路由：FastAPI ``router``（主进程）。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel, Field

from app.control.input_command_store import (
    ack_control_input,
    enqueue_control_input,
    peek_latest_control_input,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ControlInputBody(BaseModel):
    target: str = Field(default="main_input")
    text: str = ""
    action: str = "none"


@router.post("/input")
def fastapi_control_input(body: ControlInputBody = Body(default_factory=ControlInputBody)):
    ok, _mid, payload = enqueue_control_input(
        target=body.target,
        text=body.text,
        action=body.action,
    )
    if not ok:
        from fastapi.responses import JSONResponse

        return JSONResponse(payload, status_code=400)
    return payload


@router.get("/input/latest")
def fastapi_control_input_latest(target: str = Query(default="main_input")):
    return peek_latest_control_input(target)


@router.post("/input/{cmd_id}/ack")
def fastapi_control_input_ack(cmd_id: str, target: str = Query(default="main_input")):
    ok, payload = ack_control_input(target, cmd_id)
    if not ok:
        from fastapi.responses import JSONResponse

        return JSONResponse(payload, status_code=404)
    return payload


__all__ = ["router"]
