"""审批中心 Mod（里程碑 E）— 全量门面路由，委托宿主 approval 实现。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, Header, Query, Request

logger = logging.getLogger(__name__)

HOST_PREFIXES = ["/api/approval"]


def register_fastapi_routes(app, mod_id: str) -> None:
    router = APIRouter(prefix=f"/api/mod/{mod_id}", tags=[f"approval-bridge-{mod_id}"])

    @router.get("/status")
    def status():
        from app.mod_sdk.approval_compat import list_approval_facade_registry

        return {"success": True, "data": {**list_approval_facade_registry(), "mod_id": mod_id, "phase": "E"}}

    @router.get("/registry")
    def registry():
        from app.mod_sdk.approval_compat import list_approval_facade_registry

        return {"success": True, "data": list_approval_facade_registry()}

    # ── 审批请求 ────────────────────────────────────────────────────
    @router.get("/requests")
    def mod_list_requests(
        approver_id: int | None = Query(default=None),
        applicant_id: int | None = Query(default=None),
        status: str | None = Query(default=None),
        business_type: str | None = Query(default=None),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50, ge=1, le=500),
    ):
        from app.fastapi_routes.approval import list_requests

        return list_requests(approver_id, applicant_id, status, business_type, page, page_size)

    @router.post("/requests/cleanup")
    def mod_cleanup_requests(
        body: dict | None = Body(default=None),
        x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    ):
        from app.fastapi_routes.approval import cleanup_requests

        return cleanup_requests(body or {}, x_user_id)

    @router.get("/requests/{request_id:int}")
    def mod_get_request(request_id: int):
        from app.fastapi_routes.approval import get_request_detail

        return get_request_detail(request_id)

    @router.post("/requests")
    def mod_submit_request(
        body: dict | None = Body(default=None),
        x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    ):
        from app.fastapi_routes.approval import submit_request

        return submit_request(body or {}, x_user_id)

    @router.post("/requests/{request_id:int}/approve")
    def mod_approve(
        request_id: int,
        body: dict | None = Body(default=None),
        x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    ):
        from app.fastapi_routes.approval import approve_request

        return approve_request(request_id, body or {}, x_user_id)

    @router.post("/requests/{request_id:int}/reject")
    def mod_reject(
        request_id: int,
        body: dict | None = Body(default=None),
        x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    ):
        from app.fastapi_routes.approval import reject_request

        return reject_request(request_id, body or {}, x_user_id)

    @router.post("/requests/{request_id:int}/withdraw")
    def mod_withdraw(
        request_id: int,
        body: dict | None = Body(default=None),
        x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    ):
        from app.fastapi_routes.approval import withdraw_request

        return withdraw_request(request_id, body or {}, x_user_id)

    @router.delete("/requests/{request_id:int}")
    def mod_delete_request(
        request_id: int,
        x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    ):
        from app.fastapi_routes.approval import delete_request

        return delete_request(request_id, x_user_id)

    # ── 审批流程 ────────────────────────────────────────────────────
    @router.get("/flows")
    def mod_list_flows(
        is_active: bool | None = Query(default=None),
        business_type: str | None = Query(default=None),
    ):
        from app.fastapi_routes.approval import list_flows

        return list_flows(is_active, business_type)

    @router.get("/flows/{flow_id:int}")
    def mod_get_flow(flow_id: int):
        from app.fastapi_routes.approval import get_flow_detail

        return get_flow_detail(flow_id)

    @router.post("/flows")
    def mod_create_flow(
        body: dict | None = Body(default=None),
        x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    ):
        from app.fastapi_routes.approval import create_flow

        return create_flow(body or {}, x_user_id)

    @router.put("/flows/{flow_id:int}")
    def mod_update_flow(
        flow_id: int,
        body: dict | None = Body(default=None),
        x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    ):
        from app.fastapi_routes.approval import update_flow

        return update_flow(flow_id, body or {}, x_user_id)

    @router.patch("/flows/{flow_id:int}/active")
    def mod_toggle_flow(
        flow_id: int,
        body: dict | None = Body(default=None),
        x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    ):
        from app.fastapi_routes.approval import toggle_flow_active

        return toggle_flow_active(flow_id, body or {}, x_user_id)

    @router.delete("/flows/{flow_id:int}")
    def mod_delete_flow(
        flow_id: int,
        x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    ):
        from app.fastapi_routes.approval import delete_flow

        return delete_flow(flow_id, x_user_id)

    @router.get("/users")
    def mod_approval_users():
        from app.fastapi_routes.approval import get_approval_users

        return get_approval_users()

    app.include_router(router)
    logger.info("xcagi-approval-bridge facade registered: %s", mod_id)


def mod_init():
    logger.info("xcagi-approval-bridge mod_init (approval facade E)")
