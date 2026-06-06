"""Migrated from legacy_wechat.py (v10)."""

from __future__ import annotations

import logging
import os
import sys

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["legacy-wechat"], deprecated=True)


def _send_wechat_via_automation(contact_name: str, message: str) -> dict:
    """优先 DesktopAutomationService，失败则回退 wechat_cv_send。"""
    from app.desktop_automation.service import get_desktop_automation_service
    from app.services.wechat_passive_group_monitor import assert_safe_outbound_group_reply

    safe = assert_safe_outbound_group_reply(message)
    if not safe:
        return {
            "success": False,
            "message": "消息内容未通过客服发送安全校验（疑似思考过程或任务复述），已拦截",
        }
    message = safe

    auto_result = get_desktop_automation_service().send_wechat_message(contact_name, message)
    if auto_result.get("success"):
        return {"success": True, "message": f"已发送给 {contact_name}", "result": auto_result}

    if not sys.platform.startswith("win"):
        return {
            "success": False,
            "message": auto_result.get("error") or auto_result.get("message") or "发送失败",
            "result": auto_result,
        }

    from app.utils.path_utils import get_resource_path

    sys_path = get_resource_path("wechat-decrypt")
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)

    from resources.wechat_cv.wechat_cv_send import search_and_send_by_cv

    result = search_and_send_by_cv(contact_name, message, delay=1.0, use_ocr=True)
    if result.get("status") == "success":
        return {"success": True, "message": f"已发送给 {contact_name}", "result": result}
    return {
        "success": False,
        "message": f"发送失败: {auto_result.get('error') or result.get('message', '未知错误')}",
        "result": {"automation": auto_result, "cv": result},
    }


def _secret_key() -> str:
    return os.environ.get("SECRET_KEY", "")


@router.get("/api/wechat/tasks")
def wechat_tasks(
    status: str = Query(default="pending"),
    contact_id: int | None = Query(default=None),
    limit: int = Query(default=20),
):
    try:
        from app.application import get_wechat_task_app_service

        service = get_wechat_task_app_service()
        tasks = service.get_tasks(contact_id=contact_id, status=status, limit=limit)
        return {"success": True, "data": tasks, "total": len(tasks)}
    except Exception as e:
        return JSONResponse({"success": False, "message": f"查询失败：{str(e)}"}, status_code=500)


def _wechat_message_timestamp_seconds(msg: dict) -> float:
    import datetime as _dt

    for key in ("timestamp", "msg_timestamp", "time", "created_at", "msg_time"):
        raw = msg.get(key)
        if raw is None:
            continue
        if isinstance(raw, (int, float)):
            v = float(raw)
            return v / 1000.0 if v > 1e12 else v
        text = str(raw).strip()
        if not text:
            continue
        try:
            iso = text.replace("Z", "+00:00")
            return _dt.datetime.fromisoformat(iso).timestamp()
        except Exception:
            continue
    return 0.0


def _wechat_message_text(msg: dict) -> str:
    for key in ("content", "message", "text", "raw_text", "body"):
        val = msg.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


@router.get("/api/wechat/starred-messages")
def wechat_starred_messages(
    limit: int = Query(default=10, ge=1, le=50),
    type: str = Query(default="all", description="all | group | contact"),
    market_user_id: int | None = Query(default=None),
    sync: bool = Query(default=False, description="为 true 时先同步群消息再返回"),
):
    """星标/绑定群聊最近一条上下文消息，供内部客服「客户微信摘要」。"""
    try:
        from app.services.wechat_group_customer_bridge import (
            build_starred_group_feed,
            sync_group_messages,
        )

        if type.strip().lower() == "group":
            if sync and market_user_id is not None:
                from app.services.wechat_group_customer_bridge import (
                    sync_bound_groups_from_live_wechat,
                )

                sync_bound_groups_from_live_wechat(
                    int(market_user_id), message_limit=80, mode="feed"
                )
            elif sync:
                sync_group_messages(force_refresh=True)
            page = build_starred_group_feed(limit=limit, market_user_id=market_user_id)
            return {"success": True, "data": page, "total": len(page), "filter": {"type": "group"}}

        from app.application import get_wechat_contact_app_service

        service = get_wechat_contact_app_service()
        contact_type = type if type not in ("all", "") else None
        contacts = service.get_contacts(
            starred_only=True,
            contact_type=contact_type,
            limit=80,
        )
        items: list[dict] = []
        for c in contacts:
            cid = c.get("id")
            if cid is None:
                continue
            messages = service.get_contact_context(int(cid))
            from app.services.wechat_group_customer_bridge import _latest_context_message

            last = _latest_context_message(messages)
            if not last:
                continue
            text = _wechat_message_text(last)
            ts = _wechat_message_timestamp_seconds(last)
            display_name = (c.get("contact_name") or "").strip() or "联系人"
            items.append(
                {
                    "id": f"{cid}-{ts}",
                    "contact_id": cid,
                    "contact_name": display_name,
                    "nickname": (c.get("remark") or "").strip() or display_name,
                    "content": text,
                    "message": text,
                    "timestamp": ts,
                    "created_at": ts,
                    "contact_type": c.get("contact_type") or "contact",
                    "is_group": (c.get("contact_type") or "") == "group",
                }
            )
        items.sort(key=lambda row: float(row.get("timestamp") or 0), reverse=True)
        page = items[:limit]
        return {"success": True, "data": page, "total": len(items)}
    except Exception as e:
        return JSONResponse({"success": False, "message": f"查询失败：{str(e)}"}, status_code=500)


@router.post("/api/wechat/groups/sync")
def wechat_groups_sync_messages(
    body: dict | None = Body(default=None),
    market_user_id: int | None = Query(default=None),
):
    """从解密库 message_0.db 同步群聊消息到 wechat_contact_context。"""
    data = body or {}
    uid = market_user_id if market_user_id is not None else data.get("market_user_id")
    try:
        from app.services.wechat_group_customer_bridge import sync_group_messages

        force_refresh = data.get("force_refresh")
        if force_refresh is None:
            force_refresh = True
        result = sync_group_messages(
            market_user_id=int(uid) if uid is not None else None,
            group_limit=int(data.get("group_limit") or 30),
            message_limit=int(data.get("message_limit") or 80),
            force_refresh=bool(force_refresh),
        )
        if (
            result.get("success")
            and int(result.get("synced") or 0) == 0
            and int(result.get("failed") or 0) > 0
        ):
            result = {
                **result,
                "success": False,
                "message": result.get("message") or "群消息同步失败，请检查微信目录、密钥与群绑定",
            }
        # 业务失败（未配置解密库等）仍返回 200 + success:false，避免前端 Network 标红
        return JSONResponse(result, status_code=200)
    except Exception as exc:
        return JSONResponse({"success": False, "message": str(exc)}, status_code=500)


@router.get("/api/wechat/groups")
def wechat_groups_list(
    keyword: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
):
    """列出已导入的微信群（供管理员绑定企业客户）。"""
    try:
        from app.services.wechat_group_customer_bridge import list_group_contacts

        rows = list_group_contacts(keyword=keyword or None, limit=limit)
        return {"success": True, "data": rows, "total": len(rows)}
    except Exception as exc:
        return JSONResponse({"success": False, "message": str(exc)}, status_code=500)


@router.get("/api/wechat/contacts")
def wechat_contacts_list_api(
    keyword: str | None = Query(default=None),
    type: str = Query(default="all"),
    starred: str = Query(default="false"),
    limit: int = Query(default=100),
):
    try:
        from app.mod_sdk.erp_domain_dispatch import try_invoke_erp_domain_handler

        mod_out = try_invoke_erp_domain_handler(
            "wechat",
            "contacts_list",
            keyword=keyword,
            type=type,
            starred=starred,
            limit=limit,
        )
        if mod_out is not None:
            return mod_out
    except Exception:
        import logging

        logging.getLogger(__name__).debug(
            "erp domain wechat.contacts_list dispatch skipped", exc_info=True
        )
    try:
        from app.application import get_wechat_contact_app_service

        service = get_wechat_contact_app_service()
        contacts = service.get_contacts(
            keyword=keyword,
            contact_type=type if type != "all" else None,
            starred_only=starred.lower() == "true",
            limit=limit,
        )
        return {"success": True, "data": contacts, "total": len(contacts)}
    except Exception as e:
        return JSONResponse({"success": False, "message": f"查询失败：{str(e)}"}, status_code=500)


@router.get("/api/wechat/contacts/{contact_id}")
def wechat_contact_get_api(contact_id: int):
    try:
        from app.application import get_wechat_contact_app_service

        service = get_wechat_contact_app_service()
        contact = service.get_contact_by_id(contact_id)
        if contact:
            return {"success": True, "data": contact}
        return JSONResponse({"success": False, "message": "联系人不存在"}, status_code=404)
    except Exception as e:
        return JSONResponse({"success": False, "message": f"查询失败：{str(e)}"}, status_code=500)


@router.delete("/api/wechat/contacts/{contact_id}")
def wechat_contact_delete_api(contact_id: int):
    try:
        from app.application import get_wechat_contact_app_service

        service = get_wechat_contact_app_service()
        result = service.delete_contact(contact_id)
        return JSONResponse(result, status_code=200 if result.get("success") else 400)
    except Exception as e:
        return JSONResponse({"success": False, "message": f"删除失败：{str(e)}"}, status_code=500)


@router.get("/api/wechat/contacts/{contact_id}/context")
def wechat_contact_context_api(contact_id: int, refresh: bool = False):
    try:
        from app.application import get_wechat_contact_app_service

        service = get_wechat_contact_app_service()
        if refresh:
            try:
                from app.services.wechat_decrypt_autoconfig import (
                    prepare_wechat_message_db_for_read,
                )

                prepare_wechat_message_db_for_read(force_decrypt=True, retry_key_scan=False)
            except Exception:
                logger.debug("context refresh: prepare_wechat_message_db skipped", exc_info=True)
            refresh_fn = getattr(service, "refresh_messages", None)
            if callable(refresh_fn):
                refresh_fn(int(contact_id), limit=80)
        messages = service.get_contact_context(contact_id)
        return {"success": True, "messages": messages, "count": len(messages)}
    except Exception as e:
        return JSONResponse({"success": False, "message": f"查询失败：{str(e)}"}, status_code=500)


@router.post("/api/wechat/contacts")
def wechat_contacts_post(body: dict = Body(default_factory=dict)):
    from app.application import get_wechat_contact_app_service

    data = body or {}
    contact_name = (data.get("contact_name") or "").strip()
    if not contact_name:
        return JSONResponse({"success": False, "message": "联系人名称不能为空"}, status_code=400)
    service = get_wechat_contact_app_service()
    result = service.add_contact(
        contact_name=contact_name,
        remark=(data.get("remark") or "").strip(),
        wechat_id=(data.get("wechat_id") or "").strip(),
        contact_type=data.get("contact_type", "contact"),
        is_starred=data.get("is_starred", True),
    )
    return JSONResponse(result, status_code=200 if result.get("success") else 400)


@router.put("/api/wechat/contacts/{contact_id}")
def wechat_contacts_put(contact_id: int, body: dict = Body(default_factory=dict)):
    from app.application import get_wechat_contact_app_service

    data = body or {}
    service = get_wechat_contact_app_service()
    result = service.update_contact(
        contact_id=contact_id,
        contact_name=(data.get("contact_name") or "").strip() or None,
        remark=(data.get("remark") or "").strip() or None,
        wechat_id=(data.get("wechat_id") or "").strip() or None,
        contact_type=data.get("contact_type"),
        is_starred=data.get("is_starred"),
    )
    return JSONResponse(result, status_code=200 if result.get("success") else 400)


@router.post("/api/wechat/contacts/{contact_id}/star")
def wechat_contacts_star(contact_id: int, body: dict = Body(default_factory=dict)):
    from app.application import get_wechat_contact_app_service

    data = body or {}
    starred = data.get("starred", True)
    service = get_wechat_contact_app_service()
    star_fn = getattr(service, "star_contact", None)
    if callable(star_fn):
        result = star_fn(contact_id, starred)
    else:
        result = service.update_contact(contact_id=contact_id, is_starred=starred)
    return JSONResponse(result, status_code=200 if result.get("success") else 400)


@router.post("/api/wechat/contacts/unstar-all")
def wechat_contacts_unstar_all():
    from app.application import get_wechat_contact_app_service

    return get_wechat_contact_app_service().unstar_all()


@router.get("/api/wechat/status")
def wechat_status():
    try:
        from app.utils.path_utils import get_resource_path

        wechat_cv_path = get_resource_path("wechat_cv")
        if os.path.isdir(wechat_cv_path) and wechat_cv_path not in sys.path:
            sys.path.insert(0, wechat_cv_path)
        from wechat_cv_send import _find_wechat_handle

        hwnd = _find_wechat_handle()
        is_logined = hwnd is not None
        return {
            "success": True,
            "logined": is_logined,
            "message": "微信已登录" if is_logined else "微信未登录",
        }
    except Exception as e:
        return {"success": False, "logined": False, "message": f"检测失败：{str(e)}"}


@router.get("/api/wechat/test")
def wechat_test():
    return {"success": True, "message": "微信服务运行正常"}


@router.post("/api/wechat/task/{task_id}/confirm")
def wechat_task_confirm(task_id: int):
    from app.application import get_wechat_task_app_service

    result = get_wechat_task_app_service().confirm_task(task_id)
    return JSONResponse(result, status_code=200 if result.get("success") else 400)


@router.post("/api/wechat/task/{task_id}/ignore")
def wechat_task_ignore(task_id: int):
    from app.application import get_wechat_task_app_service

    result = get_wechat_task_app_service().ignore_task(task_id)
    return JSONResponse(result, status_code=200 if result.get("success") else 400)


@router.post("/api/wechat/scan")
def wechat_scan(body: dict = Body(default_factory=dict)):
    data = body or {}
    try:
        from app.tasks.wechat_tasks import scan_wechat_messages

        task = scan_wechat_messages.delay(
            contact_id=data.get("contact_id"), limit=data.get("limit", 20)
        )
        return JSONResponse(
            {"success": True, "message": "扫描任务已触发", "task_id": task.id, "count": 0},
            status_code=202,
        )
    except Exception as e:
        return JSONResponse({"success": False, "message": f"扫描失败：{str(e)}"}, status_code=500)


@router.get("/api/wechat_contacts/ensure_contact_cache")
def wechat_contacts_ensure_cache():
    from app.application.facades.wechat_facade import refresh_wechat_contacts_from_decrypt

    payload, code = refresh_wechat_contacts_from_decrypt()
    return JSONResponse(payload, status_code=code)


@router.post("/api/wechat_contacts/ensure_contact_cache")
def wechat_contacts_ensure_contact_cache_post():
    from app.application.facades.wechat_facade import refresh_wechat_contacts_from_decrypt

    payload, code = refresh_wechat_contacts_from_decrypt()
    return JSONResponse(payload, status_code=code)


# POST /api/wechat_contacts/auto_configure 由 xcagi_compat_wechat 唯一注册（避免与 legacy_gaps 双挂载重复）


@router.get("/api/wechat_contacts/message_source_size")
def wechat_contacts_message_source_size():
    from app.application.facades.wechat_facade import wechat_message_source_size_payload

    payload, code = wechat_message_source_size_payload()
    return JSONResponse(payload, status_code=code)


@router.get("/api/wechat_contacts/{contact_id}")
def wechat_contacts_get_by_id(contact_id: int):
    try:
        from app.application import get_wechat_contact_app_service

        service = get_wechat_contact_app_service()
        contact = service.get_contact_by_id(contact_id)
        if contact:
            return {"success": True, "data": contact}
        return JSONResponse({"success": False, "message": "联系人不存在"}, status_code=404)
    except Exception as e:
        return JSONResponse({"success": False, "message": f"查询失败：{str(e)}"}, status_code=500)


@router.post("/api/wechat_contacts/send_message")
def wechat_contacts_send_message(body: dict = Body(default_factory=dict)):
    try:
        contact_name = (body.get("contact_name") or "").strip()
        message = (body.get("message") or "").strip()
        if not contact_name:
            return JSONResponse(
                {"success": False, "message": "联系人名称不能为空"}, status_code=400
            )
        if not message:
            return JSONResponse({"success": False, "message": "消息内容不能为空"}, status_code=400)

        out = _send_wechat_via_automation(contact_name, message)
        if out.get("success"):
            return out
        return JSONResponse(out, status_code=500)
    except Exception as e:
        logger.exception("wechat_contacts send_message: %s", e)
        return JSONResponse({"success": False, "message": f"发送失败：{str(e)}"}, status_code=500)


@router.post("/api/wechat_contacts/{contact_id}/send_message")
def wechat_contacts_send_message_to_id(contact_id: int, body: dict = Body(default_factory=dict)):
    try:
        message = (body.get("message") or "").strip()
        if not message:
            return JSONResponse({"success": False, "message": "消息内容不能为空"}, status_code=400)

        from app.application import get_wechat_contact_app_service

        service = get_wechat_contact_app_service()
        contact = service.get_contact_by_id(contact_id)
        if not contact:
            return JSONResponse(
                {"success": False, "message": f"联系人不存在: {contact_id}"}, status_code=404
            )

        contact_name = (
            contact.get("contact_name")
            or contact.get("remark")
            or contact.get("wechat_id")
            or f"ID {contact_id}"
        )

        out = _send_wechat_via_automation(contact_name, message)
        if out.get("success"):
            return out
        return JSONResponse(out, status_code=500)
    except Exception as e:
        logger.exception("wechat_contacts send to id: %s", e)
        return JSONResponse({"success": False, "message": f"发送失败：{str(e)}"}, status_code=500)
