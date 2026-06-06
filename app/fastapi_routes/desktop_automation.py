"""REST API：/api/desktop/automation/*"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.desktop_automation.service import get_desktop_automation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/desktop/automation", tags=["desktop-automation"])


class RunWorkflowBody(BaseModel):
    app_id: str = Field(..., min_length=1, max_length=64)
    workflow: str = Field(..., min_length=1, max_length=64)
    params: dict[str, Any] = Field(default_factory=dict)
    driver: str = Field(default="", max_length=32)


class SendMessageBody(BaseModel):
    app_id: str = Field(default="wechat", max_length=64)
    contact_name: str = Field(..., min_length=1, max_length=256)
    message: str = Field(..., min_length=1, max_length=8000)
    workflow: str = Field(default="open_and_send", max_length=64)


class BootstrapBody(BaseModel):
    app_id: str = Field(..., min_length=1, max_length=64)
    use_vision_api: bool = False


class RegisterProfileBody(BaseModel):
    profile: dict[str, Any]


@router.get("/status")
def automation_status():
    svc = get_desktop_automation_service()
    from app.desktop_automation.drivers import MacDriver, MCPDriver, WindowsDriver

    return {
        "success": True,
        "data": {
            "profiles": len(svc.list_profiles()),
            "drivers": {
                "windows": WindowsDriver().is_available(),
                "mac": MacDriver().is_available(),
                "mcp_wechat": MCPDriver("wechat_cv").is_available(),
            },
        },
    }


@router.get("/profiles")
def list_profiles():
    svc = get_desktop_automation_service()
    return {"success": True, "data": {"profiles": svc.list_profiles()}}


@router.get("/profiles/{app_id}")
def get_profile(app_id: str):
    svc = get_desktop_automation_service()
    profile = svc.get_profile(app_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    return {"success": True, "data": profile}


@router.post("/profiles")
def register_profile(body: RegisterProfileBody):
    svc = get_desktop_automation_service()
    return {"success": True, "data": svc.register_profile(body.profile)}


@router.post("/workflow/run")
def run_workflow(body: RunWorkflowBody):
    svc = get_desktop_automation_service()
    result = svc.run_workflow(body.app_id, body.workflow, body.params, driver=body.driver)
    return {"success": result.get("success", False), "data": result}


@router.post("/send")
def send_message(body: SendMessageBody):
    svc = get_desktop_automation_service()
    result = svc.run_workflow(
        body.app_id,
        body.workflow,
        {"contact_name": body.contact_name, "message": body.message},
    )
    return {"success": result.get("success", False), "data": result}


@router.get("/find-element")
def find_element(app_id: str, element_id: str):
    svc = get_desktop_automation_service()
    result = svc.find_element(app_id, element_id)
    return {"success": result.get("success", False), "data": result}


@router.post("/bootstrap")
async def bootstrap_app(body: BootstrapBody):
    svc = get_desktop_automation_service()
    vision_call = None
    if body.use_vision_api:

        async def _vision(prompt: str, image_b64: str) -> str:
            try:
                from app.mod_sdk.mod_employee_llm import mod_employee_complete

                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                            },
                        ],
                    },
                ]
                return await mod_employee_complete(messages, max_tokens=2048, temperature=0.1)
            except Exception as exc:
                logger.warning("vision api bootstrap failed: %s", exc)
                return "{}"

        vision_call = _vision

    result = await svc.bootstrap_app(body.app_id, vision_call=vision_call)
    return {"success": result.get("success", False), "data": result}


@router.post("/yolo/export")
def export_yolo(app_id: str):
    svc = get_desktop_automation_service()
    return {"success": True, "data": svc.export_yolo(app_id)}
