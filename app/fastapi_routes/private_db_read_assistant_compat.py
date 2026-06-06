"""Host compat API for private-db-read-assistant (wechat_local_db only)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

MOD_ID = "private-db-read-assistant"
WECHAT_SOURCE_ID = "wechat_local_db"
WECHAT_CAPABILITIES = ["contacts", "messages", "search", "context", "send"]


def _contact_to_private_db(contact: dict[str, Any]) -> dict[str, Any]:
    name = (
        contact.get("contact_name") or contact.get("remark") or contact.get("wechat_id") or ""
    ).strip()
    return {
        "id": contact.get("id"),
        "display_name": name or "-",
        "contact_name": contact.get("contact_name"),
        "remark": contact.get("remark"),
        "source_user_id": contact.get("wechat_id"),
        "contact_type": contact.get("contact_type", "contact"),
        "is_starred": bool(contact.get("is_starred")),
    }


def _map_context_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        text = ""
        for key in ("content", "message", "text", "raw_text", "body"):
            val = msg.get(key)
            if val is not None and str(val).strip():
                text = str(val).strip()
                break
        role = msg.get("role") or msg.get("sender") or "other"
        rows.append({"role": role, "text": text, "content": text})
    return rows


def build_private_db_assistant_router() -> APIRouter:
    router = APIRouter(prefix=f"/api/mod/{MOD_ID}", tags=[f"mod-{MOD_ID}"])

    @router.get("/status")
    def private_db_status():
        from app.services.wechat_decrypt_autoconfig import get_wechat_decrypt_status

        decrypt = get_wechat_decrypt_status()
        return {
            "success": True,
            "data": {
                "mod_id": MOD_ID,
                "selected_source": WECHAT_SOURCE_ID,
                "decrypt": decrypt,
            },
        }

    @router.get("/sources")
    def private_db_sources():
        from app.fastapi_routes.domains.wechat.compat_routes import (
            wechat_contacts_decrypt_status_compat,
        )

        decrypt = wechat_contacts_decrypt_status_compat()
        return {
            "success": True,
            "data": [
                {
                    "id": WECHAT_SOURCE_ID,
                    "label": "微信本地数据库适配器",
                    "status": "available",
                    "capabilities": WECHAT_CAPABILITIES,
                    "requires_authorization": True,
                    "contact_db_exists": bool(decrypt.get("contact_db_exists")),
                }
            ],
        }

    @router.post("/sources/select")
    def private_db_select_source(body: dict = Body(default_factory=dict)):
        source_id = str((body or {}).get("source_id") or "").strip()
        if source_id and source_id != WECHAT_SOURCE_ID:
            return JSONResponse(
                {"success": False, "message": f"数据源 {source_id} 尚在规划中"},
                status_code=400,
            )
        return {"success": True, "data": {"source_id": WECHAT_SOURCE_ID}}

    @router.post("/wechat/auto_configure")
    def private_db_wechat_auto_configure(body: dict = Body(default_factory=dict)):
        from app.services.wechat_decrypt_http import wechat_decrypt_auto_configure_response

        return wechat_decrypt_auto_configure_response(body)

    @router.post("/sources/refresh")
    def private_db_refresh_source(body: dict = Body(default_factory=dict)):
        data = body or {}
        source_id = str(data.get("source_id") or "").strip()
        refresh_type = str(data.get("refresh_type") or "contacts").strip().lower()

        if source_id != WECHAT_SOURCE_ID:
            return JSONResponse(
                {"success": False, "message": f"数据源 {source_id or '(空)'} 尚在规划中"},
                status_code=400,
            )

        if refresh_type in ("contacts", "all"):
            from app.application.facades.wechat_facade import refresh_wechat_contacts_from_decrypt

            payload, code = refresh_wechat_contacts_from_decrypt()
            return JSONResponse(payload, status_code=code)

        if refresh_type == "messages":
            try:
                from app.services.wechat_group_customer_bridge import sync_group_messages

                payload = sync_group_messages()
                code = 200 if payload.get("success") else 500
                return JSONResponse(payload, status_code=code)
            except Exception as exc:
                return JSONResponse(
                    {"success": False, "message": f"同步聊天记录失败：{exc}"},
                    status_code=500,
                )

        return JSONResponse(
            {"success": False, "message": f"不支持的 refresh_type: {refresh_type}"},
            status_code=400,
        )

    @router.get("/contacts/search")
    def private_db_search_contacts(
        source_id: str = Query(default=""),
        q: str = Query(default=""),
    ):
        if source_id != WECHAT_SOURCE_ID:
            return JSONResponse(
                {"success": False, "message": "仅支持 wechat_local_db"},
                status_code=400,
            )
        term = (q or "").strip()
        if not term:
            return {"success": True, "data": []}
        try:
            from app.application import get_wechat_contact_app_service

            service = get_wechat_contact_app_service()
            contacts = service.get_contacts(keyword=term, starred_only=False, limit=80)
            return {
                "success": True,
                "data": [_contact_to_private_db(c) for c in contacts],
            }
        except Exception as e:
            logger.exception("private_db search contacts: %s", e)
            return JSONResponse(
                {"success": False, "message": f"搜索失败：{e}"},
                status_code=500,
            )

    @router.get("/contacts/{contact_id}/context")
    def private_db_contact_context(
        contact_id: str,
        source_id: str = Query(default=""),
    ):
        if source_id != WECHAT_SOURCE_ID:
            return JSONResponse(
                {"success": False, "message": "仅支持 wechat_local_db"},
                status_code=400,
            )
        try:
            cid = int(contact_id)
        except ValueError:
            return JSONResponse(
                {"success": False, "message": "无效的联系人 ID"},
                status_code=400,
            )
        try:
            from app.application import get_wechat_contact_app_service

            service = get_wechat_contact_app_service()
            messages = service.get_contact_context(cid)
            return {"success": True, "data": _map_context_messages(messages)}
        except Exception as e:
            logger.exception("private_db contact context: %s", e)
            return JSONResponse(
                {"success": False, "message": f"读取失败：{e}"},
                status_code=500,
            )

    @router.post("/send")
    def private_db_send_message(body: dict = Body(default_factory=dict)):
        data = body or {}
        source_id = str(data.get("source_id") or "").strip()
        if source_id != WECHAT_SOURCE_ID:
            return JSONResponse(
                {"success": False, "message": f"数据源 {source_id or '(空)'} 尚在规划中"},
                status_code=400,
            )
        from app.fastapi_routes.domains.wechat.routes import wechat_contacts_send_message

        return wechat_contacts_send_message(
            body={
                "contact_name": data.get("contact_name"),
                "message": data.get("message"),
            }
        )

    return router


def register_private_db_read_assistant_routes(app) -> None:
    app.include_router(build_private_db_assistant_router())
    logger.info("Registered private_db_read_assistant_compat (/api/mod/%s/*)", MOD_ID)
